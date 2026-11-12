# ==============================================================================
# TEST PERFORMANCE SYNC
# ==============================================================================
# Isolate per-ID bookkeeping, transaction confirmation, and worker wakeups.
# Compare production Sync, a worker-disabled diagnostic, and a no-op stub.
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

	# Measure one scenario in a fresh ontology, excluding service startup,
	# shutdown, and subscriber registration from the timed interval.
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
			first_txn = -1000000

			# Startup writes may already have launched the worker. Reset Sync
			# before each diagnostic to isolate its actual delivery policy.
			# --------------------------------------------------------------
			sync.close()

			if mode == 'stub':
				memory.sync = SimpleNamespace(
					on_change  = lambda txn, id: None,
					on_changed = lambda txn: None,
					on_aborted = lambda txn: None,
				)
			else:
				type(sync).initialize(sync, fallback_delay=5.0)

				if mode == 'no_worker':
					# Diagnostic only: accumulate notifications without starting
					# their consumer. This is NOT a valid production configuration.
					# ----------------------------------------------------------
					sync._start_worker = lambda: None
				elif mode == 'listening':
					sync.subscribe(lambda ids: None)

			try:
				if scenario == 'notify':
					# Repeated changes to one open transaction: steady-state
					# hot-path bookkeeping without scheduling new deadlines.
					# ------------------------------------------------------
					started = time.perf_counter_ns()

					for index in range(size):
						memory.sync.on_change(first_txn, owner_id)

					elapsed = time.perf_counter_ns() - started
					memory.sync.on_changed(first_txn)

				elif scenario == 'first':
					# First changed ID in each distinct transaction: deadline,
					# bookkeeping, and initial worker notification.
					# ------------------------------------------------------
					started = time.perf_counter_ns()

					for index in range(size):
						memory.sync.on_change(first_txn - index, owner_id)

					elapsed = time.perf_counter_ns() - started

					for index in range(size):
						memory.sync.on_aborted(first_txn - index)

				elif scenario == 'confirm':
					# Prepare candidate IDs before timing confirmation. This
					# isolates on_changed, queue insertion, and worker wakeups.
					# ------------------------------------------------------
					if mode != 'stub':
						for index in range(size):
							txn = first_txn - index
							sync.changes[txn]    = [owner_id]
							sync._scheduled[txn] = index

					started = time.perf_counter_ns()

					for index in range(size):
						memory.sync.on_changed(first_txn - index)

					elapsed = time.perf_counter_ns() - started

				elif scenario == 'pair':
					# Entire per-transaction Sync notification without LMDB.
					# ------------------------------------------------------
					started = time.perf_counter_ns()

					for index in range(size):
						txn = first_txn - index
						memory.sync.on_change(txn, owner_id)
						memory.sync.on_changed(txn)

					elapsed = time.perf_counter_ns() - started

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
				if mode != 'stub':
					sync.close()

				memory.env.close()

		result = elapsed / (size * 1000)
		return result


# Run paired modes in independent processes and alternate their order.
# Microbenchmarks isolate overhead; no_worker intentionally bypasses delivery.
# ------------------------------------------------------------------------------
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--size', type=int, default=10000)
	parser.add_argument('--rounds', type=int, default=5)
	parser.add_argument('--scenario', choices=('notify', 'first', 'confirm', 'pair', 'batch', 'single'))
	parser.add_argument('--mode', choices=('stub', 'no_worker', 'sync', 'listening'))
	parser.add_argument('--_json', action='store_true', help=argparse.SUPPRESS)
	args = parser.parse_args()

	if args.size <= 0 or args.rounds <= 0:
		parser.error('--size and --rounds must be positive')

	if args._json:
		result = TestPerformanceSync.measure(args.scenario, args.mode, args.size)
		print(json.dumps(result))
	else:
		runner = os.path.abspath(__file__)
		modes  = ('stub', 'no_worker', 'sync', 'listening')
		print(f'{args.rounds} rounds x {args.size} operations, isolated LMDB for each sample.', flush=True)
		print('Microseconds per operation: median [min..max]; lower is faster.', flush=True)
		print('no_worker disables delivery ONLY to isolate worker cost.', flush=True)
		print(f'{"Scenario":12} ' + ' '.join(f'{mode:>25}' for mode in modes), flush=True)
		print('-' * 116, flush=True)

		for scenario in ('notify', 'first', 'confirm', 'pair', 'batch', 'single'):
			samples = {mode: [] for mode in modes}

			for round_id in range(args.rounds):
				order = modes if round_id % 2 == 0 else tuple(reversed(modes))

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
						raise RuntimeError(
							f'{scenario}/{mode}: ' + completed.stdout + completed.stderr
						)

					samples[mode].append(json.loads(completed.stdout.strip().splitlines()[-1]))

			values = []

			for mode in modes:
				data = samples[mode]
				values.append(
					f'{statistics.median(data):8.3f} '
					f'[{min(data):7.3f}..{max(data):7.3f}]'
				)

			print(f'{scenario:12} ' + ' '.join(values), flush=True)
