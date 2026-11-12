# ==============================================================================
# TEST PERFORMANCE SYNC
# ==============================================================================
# Compare production Sync against test-only polling and event-driven delivery.
# Measure storage throughput, notification latency, and idle CPU utilization.
# ==============================================================================

import argparse
import json
import os
import statistics
import subprocess
import sys
import tempfile
import threading
import time

from collections import defaultdict
from queue       import Empty, Queue, SimpleQueue
from types       import SimpleNamespace

import o


class TestPerformanceSync(o.Tester):

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Keep the original Sync locking but poll instead of waking its worker
	# at each commit; production Sync remains unchanged.
	# ----------------------------------------------------------------------
	@classmethod
	def _poll_mode(cls, sync, interval):
		condition       = sync._condition
		original_notify = condition.notify
		original_wait   = condition.wait
		original_close  = sync.close

		condition.notify = lambda n=1: None
		condition.wait   = lambda timeout=None: original_wait(
			min(timeout, interval) if timeout is not None else interval
		)

		# Restore wake-up semantics before closing the original worker.
		# ------------------------------------------------------------------
		def close():
			condition.notify = original_notify
			original_close()
			condition.wait = original_wait

		sync.close = close

	# Run a test-only queue consumer that never locks the writing thread.
	# Polling preserves cheap storage; event mode trades write-side signalling
	# for faster delivery under sparse traffic.
	# ----------------------------------------------------------------------
	@classmethod
	def _queue_run(cls, sync, interval, event_mode, hybrid):
		last_active = time.monotonic()

		while not sync._stop.is_set():
			# Sleep until a producer signals when no transaction is pending.
			# Recheck after declaring the worker asleep to avoid lost wakeups.
			# --------------------------------------------------------------
			if (
				hybrid and time.monotonic() - last_active >= 0.02
				and sync._completed.empty() and not sync._pending
			):
				sync._wake.clear()
				sync._sleeping = True

				if sync._completed.empty() and not sync._pending:
					sync._wake.wait()

				sync._sleeping = False
				sync._wake.clear()
			else:
				sync._wake.wait(interval)

			if event_mode and sync._wake.is_set():
				sync._wake.clear()
				time.sleep(0.001)

			batches = []

			for index in range(sync._completed.qsize()):
				try:
					batches.append(sync._completed.get_nowait())
				except Empty:
					break

			# Unconfirmed transactions retain a 1-second fallback. A
			# generation check rejects stale snapshots after ID reuse.
			# ----------------------------------------------------------
			now = time.monotonic()

			for txn, state in tuple(sync._pending.items()):
				if now >= state[0] and sync._pending.get(txn) is state:
					batches.append(tuple(state[1]))
					state[0] = now + 1.0

			if batches:
				last_active = time.monotonic()
				ids = set()

				for batch in batches:
					ids.update(batch)

				sync._update(frozenset({0}) if 0 in ids else frozenset(ids))

		# Drain confirmed commits before shutdown.
		# ------------------------------------------------------------------
		batches = []

		for index in range(sync._completed.qsize()):
			try:
				batches.append(sync._completed.get_nowait())
			except Empty:
				break

		if batches:
			ids = set()

			for batch in batches:
				ids.update(batch)

			sync._update(frozenset({0}) if 0 in ids else frozenset(ids))

	# Prototype: producer-owned pending IDs, lock-free SimpleQueue handoff,
	# and periodic draining or a coalesced Event wake-up.
	# Thread-safety beyond CPython's GIL needs a separate correctness review.
	# ----------------------------------------------------------------------
	@classmethod
	def _queue_mode(cls, sync, interval, event_mode, hybrid=False):
		sync._pending   = {}
		sync._completed = SimpleQueue()
		sync._stop      = threading.Event()
		sync._wake      = threading.Event()
		sync._closed    = False
		sync._sleeping  = False

		def on_change(txn, id):
			state = sync._pending.get(txn)

			if state is None:
				state = [time.monotonic() + 1.0, []]
				sync._pending[txn] = state

			state[1].append(id)

			if hybrid and sync._sleeping:
				sync._wake.set()

		def on_changed(txn):
			state = sync._pending.pop(txn, None)

			if state is not None:
				sync._completed.put(state[1])

				if event_mode or (hybrid and sync._sleeping):
					sync._wake.set()

		def on_aborted(txn):
			sync._pending.pop(txn, None)

		def close():
			sync._stop.set()
			sync._wake.set()
			sync._queue_worker.join()
			sync._subscribers.clear()
			sync._closed = True

		sync.on_change  = on_change
		sync.on_changed = on_changed
		sync.on_aborted = on_aborted
		sync.close      = close

		sync._queue_worker = threading.Thread(
			target = cls._queue_run,
			args   = (sync, interval, event_mode, hybrid),
			name   = 'o-sync-benchmark',
			daemon = True,
		)
		sync._queue_worker.start()

	# Keep each pending transaction owned by the worker. Producers publish
	# the transaction record once and later hand off committed ID lists.
	# The writer and worker do not concurrently access the transaction map.
	# ----------------------------------------------------------------------
	@classmethod
	def _handoff_run(cls, sync, interval):
		pending     = []
		last_active = time.monotonic()

		while not sync._stop.is_set():
			# A dormant worker wakes only when a new transaction arrives.
			# ----------------------------------------------------------
			if (
				time.monotonic() - last_active >= 0.02
				and not pending and sync._registered.empty()
				and sync._completed.empty()
			):
				sync._wake.clear()
				sync._sleeping = True

				if not pending and sync._registered.empty() and sync._completed.empty():
					sync._wake.wait()

				sync._sleeping = False
				sync._wake.clear()
			else:
				sync._wake.wait(interval)

			for index in range(sync._registered.qsize()):
				try:
					state = sync._registered.get_nowait()

					if state[2]:
						pending.append(state)
				except Empty:
					break

			batches = []

			for index in range(sync._completed.qsize()):
				try:
					batches.append(sync._completed.get_nowait())
				except Empty:
					break

			now    = time.monotonic()
			active = []

			for state in pending:
				if state[2]:
					if now >= state[0]:
						batches.append(tuple(state[1]))
						state[0] = now + 1.0

					active.append(state)

			pending = active

			if batches:
				last_active = now
				ids = set()

				for batch in batches:
					ids.update(batch)

				sync._update(frozenset({0}) if 0 in ids else frozenset(ids))

		batches = []

		for index in range(sync._completed.qsize()):
			try:
				batches.append(sync._completed.get_nowait())
			except Empty:
				break

		if batches:
			ids = set()

			for batch in batches:
				ids.update(batch)

			sync._update(frozenset({0}) if 0 in ids else frozenset(ids))

	# Publish an open transaction once, then hand its list to the worker
	# on commit; all transaction-map mutations stay on the producer side.
	# ----------------------------------------------------------------------
	@classmethod
	def _handoff_mode(cls, sync, interval):
		sync._pending    = {}
		sync._registered = SimpleQueue()
		sync._completed  = SimpleQueue()
		sync._stop       = threading.Event()
		sync._wake       = threading.Event()
		sync._sleeping   = False
		sync._closed     = False

		def on_change(txn, id):
			state = sync._pending.get(txn)

			if state is None:
				state = [time.monotonic() + 1.0, [], True]
				sync._pending[txn] = state
				sync._registered.put(state)

			state[1].append(id)

			if sync._sleeping:
				sync._wake.set()

		def on_changed(txn):
			state = sync._pending.pop(txn, None)

			if state is not None:
				state[2] = False
				sync._completed.put(state[1])

				if sync._sleeping:
					sync._wake.set()

		def on_aborted(txn):
			state = sync._pending.pop(txn, None)

			if state is not None:
				state[2] = False

		def close():
			sync._stop.set()
			sync._wake.set()
			sync._queue_worker.join()
			sync._subscribers.clear()
			sync._closed = True

		sync.on_change  = on_change
		sync.on_changed = on_changed
		sync.on_aborted = on_aborted
		sync.close      = close

		sync._queue_worker = threading.Thread(
			target = cls._handoff_run,
			args   = (sync, interval),
			name   = 'o-sync-handoff-benchmark',
			daemon = True,
		)
		sync._queue_worker.start()

	# Establish a fresh model for each mode after O startup has completed.
	# A no-op stub measures original storage without delivery bookkeeping.
	# ----------------------------------------------------------------------
	@classmethod
	def _select_mode(cls, memory, sync, mode):
		sync.close()

		if mode == 'stub':
			memory.sync = SimpleNamespace(
				on_change  = lambda txn, id: None,
				on_changed = lambda txn: None,
				on_aborted = lambda txn: None,
			)
		else:
			type(sync).initialize(sync, fallback_delay=1.0)

			if mode == 'poll1':
				cls._poll_mode(sync, 0.001)
			elif mode == 'poll5':
				cls._poll_mode(sync, 0.005)
			elif mode == 'queue1':
				cls._queue_mode(sync, 0.001, False)
			elif mode == 'queue5':
				cls._queue_mode(sync, 0.005, False)
			elif mode == 'event1':
				cls._queue_mode(sync, 0.001, True)
			elif mode == 'hybrid':
				cls._queue_mode(sync, 0.001, False, True)
			elif mode == 'handoff':
				cls._handoff_mode(sync, 0.001)

	# Measure microseconds per write, sparse delivery latency distribution,
	# or worker CPU spent during a one-second idle interval.
	# ----------------------------------------------------------------------
	@classmethod
	def _measure(cls, scenario, mode, size):
		with tempfile.TemporaryDirectory(prefix='o_perf_sync_') as directory:
			type(o).__app__ = SimpleNamespace(__lib_path__=directory)
			o.start()

			memory = o.services.Memory
			sync   = o.services.Sync
			cls._select_mode(memory, sync, mode)

			try:
				if scenario == 'single':
					started = time.perf_counter_ns()

					for index in range(size):
						memory.set('sync/perf/single', index, 12345)

					result = (time.perf_counter_ns() - started) / (size * 1000)

				elif scenario == 'batch':
					started = time.perf_counter_ns()

					with memory.write():
						for index in range(size):
							memory.set('sync/perf/batch', index, 12345)

					result = (time.perf_counter_ns() - started) / (size * 1000)

				elif scenario == 'latency':
					observed = Queue()

					if mode != 'stub':
						sync.subscribe(lambda ids: observed.put(time.perf_counter_ns()))

					samples = []

					for index in range(size):
						txn = -(index + 1)
						memory.sync.on_change(txn, index + 1)
						started = time.perf_counter_ns()
						memory.sync.on_changed(txn)

						if mode != 'stub':
							finished = observed.get(timeout=3)
							samples.append(max(0, finished - started) / 1000)

					result = samples

				elif scenario == 'idle':
					if mode != 'stub':
						# Prime the worker, then allow the initial event to drain.
						memory.sync.on_change(-1, 1)
						memory.sync.on_changed(-1)
						time.sleep(0.05)

					started = time.process_time_ns()
					time.sleep(1.0)
					result = (time.process_time_ns() - started) / 1000000

			finally:
				if mode != 'stub':
					sync.close()

				memory.env.close()

		return result


	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Provide isolated results to the parent process for each strategy.
	# ----------------------------------------------------------------------
	@classmethod
	def measure(cls, scenario, mode, size):
		result = cls._measure(scenario, mode, size)
		return result


# Keep each sample in a separate process to isolate LMDB and service state.
# ------------------------------------------------------------------------------
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--size', type=int, default=10000)
	parser.add_argument('--rounds', type=int, default=5)
	parser.add_argument('--_json', action='store_true', help=argparse.SUPPRESS)
	parser.add_argument('--scenario', choices=('single', 'batch', 'latency', 'idle'))
	parser.add_argument('--mode', choices=('stub', 'current', 'poll1', 'poll5', 'queue1', 'queue5', 'event1', 'hybrid', 'handoff'))
	args = parser.parse_args()

	modes = ('stub', 'current', 'poll1', 'poll5', 'queue1', 'queue5', 'event1', 'hybrid', 'handoff')

	if args._json:
		result = TestPerformanceSync.measure(args.scenario, args.mode, args.size)
		print(json.dumps(result))
	else:
		runner = os.path.abspath(__file__)

		for scenario in ('single', 'batch', 'latency', 'idle'):
			count   = args.size if scenario in ('single', 'batch') else (80 if scenario == 'latency' else 1)
			rounds = args.rounds if scenario in ('single', 'batch') else (2 if scenario == 'latency' else 1)
			print(f'{scenario}: {rounds} rounds x {count} iterations', flush=True)

			for mode in modes:
				results = []

				for round_id in range(rounds):
					completed = subprocess.run(
						[
							sys.executable, runner,
							'--size', str(count),
							'--scenario', scenario,
							'--mode', mode,
							'--_json',
						],
						capture_output = True,
						text           = True,
					)

					if completed.returncode:
						raise RuntimeError(
							f'{scenario}/{mode}: ' + completed.stdout + completed.stderr
						)

					results.append(json.loads(completed.stdout.strip().splitlines()[-1]))

				if scenario == 'latency':
					latencies = sorted(value for sample in results for value in sample)
					if latencies:
						p50 = latencies[int(0.50 * (len(latencies) - 1))]
						p95 = latencies[int(0.95 * (len(latencies) - 1))]
						p99 = latencies[int(0.99 * (len(latencies) - 1))]
						print(f'{mode:9} latency p50={p50:8.1f} p95={p95:8.1f} p99={p99:8.1f} us', flush=True)
					else:
						print(f'{mode:9} latency n/a', flush=True)
				else:
					unit = 'ms CPU' if scenario == 'idle' else 'us/change'
					print(f'{mode:9} {statistics.median(results):8.3f} [{min(results):8.3f}..{max(results):8.3f}] {unit}', flush=True)
