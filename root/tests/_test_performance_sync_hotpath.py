# ==============================================================================
# TEST PERFORMANCE SYNC HOTPATH
# ==============================================================================
# Isolate producer-side Sync costs without modifying the production service.
# Candidate variants preserve committed delivery; diagnostics may omit fallback.
# ==============================================================================

import argparse
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time

from types import SimpleNamespace

import o


class TestPerformanceSyncHotpath(o.Tester):

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Prototype a single registration queue: commit changes record state.
	# The worker observes state transitions without a second producer enqueue.
	# ----------------------------------------------------------------------
	@classmethod
	def _single_queue_mode(cls, sync):
		def on_change(txn, id):
			if sync._closed:
				raise RuntimeError('Sync is closed')

			record = sync.changes.get(txn)

			if record is None:
				record = [time.monotonic() + sync.fallback_delay, [id], 1]
				sync.changes[txn] = record
				sync._registered.put(record)

				if sync._sleeping:
					sync._wake.set()
			else:
				record[1].append(id)

		def on_changed(txn):
			if sync._closed:
				raise RuntimeError('Sync is closed')

			record = sync.changes.pop(txn, None)

			if record is not None:
				record[2] = 2

		def on_aborted(txn):
			record = sync.changes.pop(txn, None)

			if record is not None:
				record[2] = 0

		def run():
			pending       = []
			last_activity = time.monotonic()

			while not sync._closed:
				if (
					time.monotonic() - last_activity >= sync.idle_delay
					and not pending and sync._registered.empty()
				):
					sync._wake.clear()
					sync._sleeping = True

					if not pending and sync._registered.empty():
						sync._wake.wait()

					sync._sleeping = False
				else:
					sync._wake.wait(sync.batch_delay)

				sync._wake.clear()
				pending.extend(sync._drain(sync._registered))
				batches = []
				active  = []
				now     = time.monotonic()

				for record in pending:
					state = record[2]

					if state == 2:
						batches.append(record[1])
					elif state == 1:
						if now >= record[0]:
							batches.append(tuple(record[1]))
							record[0] = now + sync.fallback_delay

						active.append(record)

				pending = active

				if batches:
					last_activity = now
					sync._deliver(batches)

			# A committed record must survive immediate close.
			# --------------------------------------------------------------
			batches = []

			for record in pending + sync._drain(sync._registered):
				if record[2] == 2:
					batches.append(record[1])

			if batches:
				sync._deliver(batches)

		sync.on_change  = on_change
		sync.on_changed = on_changed
		sync.on_aborted = on_aborted
		sync._run       = run

	# Install a test-only producer variation on the real Sync singleton.
	# ----------------------------------------------------------------------
	@classmethod
	def _configure(cls, memory, sync, mode):
		sync.close()

		if mode == 'stub':
			memory.sync = SimpleNamespace(
				on_change  = lambda txn, id: None,
				on_changed = lambda txn: None,
				on_aborted = lambda txn: None,
			)
		else:
			if mode == 'single_queue':
				cls._single_queue_mode(sync)

			type(sync).initialize(sync)

			if mode in ('no_register', 'worker_deadline'):
				# Remove first-change queue insertion as a diagnostic, or
				# move deadline calculation to the consumer as a candidate.
				# ----------------------------------------------------------
				def on_change(txn, id):
					if sync._closed:
						raise RuntimeError('Sync is closed')

					record = sync.changes.get(txn)

					if record is None:
						record = [0.0, [id], True]
						sync.changes[txn] = record

						if mode == 'worker_deadline':
							sync._registered.put(record)

						if sync._sleeping:
							sync._wake.set()
					else:
						record[1].append(id)

				sync.on_change = on_change

				if mode == 'worker_deadline':
					original_drain = sync._drain

					def drain(queue):
						records = original_drain(queue)

						if queue is sync._registered:
							for record in records:
								record[0] = time.monotonic() + sync.fallback_delay

						return records

					sync._drain = drain

			elif mode == 'unchecked':
				# Assess the cost of the closed-state check alone. This
				# diagnostic must NOT be shipped as production behavior.
				# ----------------------------------------------------------
				def on_change(txn, id):
					record = sync.changes.get(txn)

					if record is None:
						record = [time.monotonic() + sync.fallback_delay, [id], True]
						sync.changes[txn] = record
						sync._registered.put(record)

						if sync._sleeping:
							sync._wake.set()
					else:
						record[1].append(id)

				def on_changed(txn):
					record = sync.changes.pop(txn, None)

					if record is not None:
						record[2] = False
						sync._ready.put(record[1])

				sync.on_change  = on_change
				sync.on_changed = on_changed

	# Measure one producer stage or an entire LMDB write with fresh storage.
	# ----------------------------------------------------------------------
	@classmethod
	def _measure(cls, mode, scenario, size):
		with tempfile.TemporaryDirectory(prefix='o_sync_hotpath_') as directory:
			type(o).__app__ = SimpleNamespace(__lib_path__=directory)
			o.start()

			memory = o.services.Memory
			sync   = o.services.Sync
			cls._configure(memory, sync, mode)

			try:
				if scenario == 'single':
					started = time.perf_counter_ns()

					for index in range(size):
						memory.set('sync/perf/hotpath', index, 12345)

					elapsed = time.perf_counter_ns() - started

				elif scenario == 'batch':
					started = time.perf_counter_ns()

					with memory.write():
						for index in range(size):
							memory.set('sync/perf/hotpath', index, 12345)

					elapsed = time.perf_counter_ns() - started

				elif scenario == 'change':
					started = time.perf_counter_ns()

					for index in range(size):
						memory.sync.on_change(-1, 12345)

					elapsed = time.perf_counter_ns() - started
					memory.sync.on_aborted(-1)

				elif scenario == 'validate':
					from queue import Empty, Queue

					events = Queue()
					sync.subscribe(events.put)
					sync.fallback_delay = 0.03

					sync.on_change(-9, 11)
					assert events.get(timeout=2) == frozenset({11})
					sync.on_change(-9, 12)
					sync.on_changed(-9)
					assert events.get(timeout=2) == frozenset({11, 12})

					sync.on_change(-8, 21)
					sync.on_aborted(-8)
					time.sleep(0.06)

					try:
						unexpected = events.get_nowait()
					except Empty:
						unexpected = None

					assert unexpected is None
					assert sync.changes == {}
					elapsed = 0

				elif scenario == 'latency':
					from queue import Queue

					events = Queue()
					sync.subscribe(lambda ids: events.put(time.perf_counter_ns()))
					samples = []

					for index in range(80):
						txn = -index - 1
						memory.sync.on_change(txn, index + 1)
						started = time.perf_counter_ns()
						memory.sync.on_changed(txn)
						finished = events.get(timeout=2)
						samples.append((finished - started) / 1000)

					elapsed = statistics.median(samples) * 1000 * size

				elif scenario == 'pair':
					started = time.perf_counter_ns()

					for index in range(size):
						txn = -index - 1
						memory.sync.on_change(txn, 12345)
						memory.sync.on_changed(txn)

					elapsed = time.perf_counter_ns() - started

			finally:
				if mode != 'stub':
					sync.close()

				memory.env.close()

		return elapsed / (1000 * size)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Execute one independent timing sample in the child process.
	# ----------------------------------------------------------------------
	@classmethod
	def measure(cls, mode, scenario, size):
		result = cls._measure(mode, scenario, size)
		return result


# Run paired modes with alternating order to reduce thermal/runtime bias.
# ------------------------------------------------------------------------------
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--size', type=int, default=10000)
	parser.add_argument('--rounds', type=int, default=7)
	parser.add_argument('--_mode', help=argparse.SUPPRESS)
	parser.add_argument('--_scenario', help=argparse.SUPPRESS)
	parser.add_argument('--_json', action='store_true', help=argparse.SUPPRESS)
	args = parser.parse_args()

	modes     = ('stub', 'current', 'no_register', 'worker_deadline', 'unchecked', 'single_queue')
	scenarios = ('change', 'pair', 'batch', 'single')

	if args._json:
		result = TestPerformanceSyncHotpath.measure(args._mode, args._scenario, args.size)
		print(json.dumps(result))
	else:
		runner = os.path.abspath(__file__)
		print('Microseconds per operation; 7 rounds by default; lower is faster.', flush=True)
		print('no_register loses open-transaction fallback; unchecked omits closure checks.', flush=True)

		for scenario in scenarios:
			samples = {mode: [] for mode in modes}
			print(f'{scenario}: {args.size} iterations', flush=True)

			for round_id in range(args.rounds):
				order = modes if round_id % 2 == 0 else tuple(reversed(modes))

				for mode in order:
					completed = subprocess.run(
						[
							sys.executable, runner, '--size', str(args.size),
							'--_mode', mode, '--_scenario', scenario, '--_json',
						],
						capture_output = True,
						text           = True,
					)

					if completed.returncode:
						raise RuntimeError(completed.stdout + completed.stderr)

					samples[mode].append(json.loads(completed.stdout.strip().splitlines()[-1]))

			for mode in modes:
				values = samples[mode]
				print(
					f'{mode:17} {statistics.median(values):8.3f} '
					f'[{min(values):8.3f}..{max(values):8.3f}]',
					flush = True,
				)

		# Validate speculative fallback and commit delivery before recommending.
		# ----------------------------------------------------------------------
		for mode in ('current', 'single_queue'):
			completed = subprocess.run(
				[
					sys.executable, runner, '--size', '1',
					'--_mode', mode, '--_scenario', 'validate', '--_json',
				],
				capture_output = True,
				text           = True,
			)

			if completed.returncode:
				raise RuntimeError(completed.stdout + completed.stderr)

			print(f'{mode} validation passed', flush=True)

		# Measure sparse delivery separately from write throughput.
		# ----------------------------------------------------------------------
		for mode in ('current', 'single_queue'):
			completed = subprocess.run(
				[
					sys.executable, runner, '--size', '1',
					'--_mode', mode, '--_scenario', 'latency', '--_json',
				],
				capture_output = True,
				text           = True,
			)

			if completed.returncode:
				raise RuntimeError(completed.stdout + completed.stderr)

			print(f'{mode} latency p50: {float(completed.stdout.strip().splitlines()[-1]):.1f} us', flush=True)
