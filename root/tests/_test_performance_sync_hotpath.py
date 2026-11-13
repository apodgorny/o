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

	modes     = ('stub', 'current', 'no_register', 'worker_deadline', 'unchecked')
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
