# ==============================================================================
# TEST PERFORMANCE SYNC
# ==============================================================================
# Measure local Sync overhead per mutation: notification-only, one LMDB
# transaction for many writes, and one transaction per write.
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


class TestPerformanceSync(o.Tester):

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Measure one scenario in a fresh ontology, without timing initialization,
	# service shutdown, or subscriber callbacks.
	# ----------------------------------------------------------------------
	@classmethod
	def measure(cls, scenario, mode, size):
		with tempfile.TemporaryDirectory(prefix='o_perf_sync_') as directory:
			type(o).__app__ = SimpleNamespace(__lib_path__=directory)
			o.start()

			memory   = o.services.Memory
			sync     = o.services.Sync
			owner_id = 12345
			elapsed  = None

			if mode == 'stub':
				sync.close()
				memory.sync = SimpleNamespace(
					on_change  = lambda txn, id: None,
					on_changed = lambda txn: None,
					on_aborted = lambda txn: None,
				)

			try:
				if scenario == 'notify':
					# Isolate the cost of on_change without LMDB operations.
					# ------------------------------------------------------
					started = time.perf_counter_ns()

					for index in range(size):
						memory.sync.on_change(-1, owner_id)

					elapsed = time.perf_counter_ns() - started
					memory.sync.on_changed(-1)

				elif scenario == 'batch':
					# Change one key repeatedly within a single LMDB commit.
					# ------------------------------------------------------
					started = time.perf_counter_ns()

					with memory.write():
						for index in range(size):
							memory.set('sync/perf/batch', index, owner_id)

					elapsed = time.perf_counter_ns() - started

				elif scenario == 'single':
					# Each mutation opens and commits a separate transaction.
					# ------------------------------------------------------
					started = time.perf_counter_ns()

					for index in range(size):
						memory.set('sync/perf/single', index, owner_id)

					elapsed = time.perf_counter_ns() - started

			finally:
				if mode == 'sync':
					sync.close()

				memory.env.close()

		result = elapsed / (size * 1000)
		return result


# Run paired modes in independent processes to avoid shared LMDB and worker
# state; alternate their order to reduce drift across successive samples.
# ------------------------------------------------------------------------------
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--size', type=int, default=10000)
	parser.add_argument('--rounds', type=int, default=5)
	parser.add_argument('--scenario', choices=('notify', 'batch', 'single'))
	parser.add_argument('--mode', choices=('stub', 'sync'))
	parser.add_argument('--_json', action='store_true', help=argparse.SUPPRESS)
	args = parser.parse_args()

	if args.size <= 0 or args.rounds <= 0:
		parser.error('--size and --rounds must be positive')

	if args._json:
		result = TestPerformanceSync.measure(args.scenario, args.mode, args.size)
		print(json.dumps(result))
	else:
		runner = os.path.abspath(__file__)
		print(f'{args.rounds} rounds x {args.size} changes; isolated LMDB per sample.', flush=True)
		print('Microseconds per change: median [min..max]; lower is faster.', flush=True)
		print(f'{"Scenario":16} {"stub":>25} {"Sync":>25} {"delta":>16}', flush=True)
		print('-' * 86, flush=True)

		for scenario in ('notify', 'batch', 'single'):
			samples = {'stub': [], 'sync': []}

			for round_id in range(args.rounds):
				order = ('stub', 'sync') if round_id % 2 == 0 else ('sync', 'stub')

				for mode in order:
					completed = subprocess.run(
						[
							sys.executable, runner,
							'--size', str(args.size),
							'--scenario', scenario,
							'--mode', mode,
							'--_json',
						],
						capture_output = True,
						text           = True,
					)

					if completed.returncode:
						raise RuntimeError(completed.stdout + completed.stderr)

					samples[mode].append(json.loads(completed.stdout.strip().splitlines()[-1]))

			stub = samples['stub']
			sync = samples['sync']

			stub_median = statistics.median(stub)
			sync_median = statistics.median(sync)
			difference  = sync_median - stub_median
			percentage  = difference / stub_median * 100

			print(
				f'{scenario:16} '
				f'{stub_median:8.3f} [{min(stub):7.3f}..{max(stub):7.3f}] '
				f'{sync_median:8.3f} [{min(sync):7.3f}..{max(sync):7.3f}] '
				f'{difference:+7.3f} ({percentage:+5.1f}%)',
				flush = True,
			)
