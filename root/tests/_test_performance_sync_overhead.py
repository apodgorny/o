# ==============================================================================
# SYNC PRODUCER OVERHEAD DIAGNOSTIC
# ==============================================================================
# Isolate per-commit queue insertion, worker contention, subscriber overhead.
# Production Sync is never modified.
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

from types import SimpleNamespace

import o


OWNER_ID = 1 << 60
BLOCK_ID = OWNER_ID + 1
DRAIN_ID = OWNER_ID + 2


class TestPerformanceSyncOverhead(o.Tester):

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Wait for all previously queued publications to reach the worker.
	# ----------------------------------------------------------------------
	@classmethod
	def _drain(cls, sync):
		done     = threading.Event()
		callback = sync.subscribe({DRAIN_ID}, lambda ids: done.set())

		try:
			sync.publish_change([DRAIN_ID])
			assert done.wait(10), 'Sync worker did not drain'
		finally:
			sync.unsubscribe(callback)

	# Each sample runs in a fresh process with an independent LMDB store.
	# ----------------------------------------------------------------------
	@classmethod
	def _measure(cls, mode, size):
		with tempfile.TemporaryDirectory(prefix='o_sync_overhead_') as directory:
			type(o).__app__ = SimpleNamespace(__lib_path__=directory)
			o.start(multiprocess=False)

			memory   = o.services.Memory
			sync     = o.services.Sync
			release  = threading.Event()
			entered  = threading.Event()
			callback = None
			result   = {}

			try:
				cls._drain(sync)

				if mode == 'stub':
					memory.sync = SimpleNamespace(publish_change=lambda ids, local=True: None)

				elif mode == 'paused':
					# Suspend the worker inside a test subscriber, leaving
					# the real producer queue available for write operations.
					# ----------------------------------------------------------
					def block(ids):
						entered.set()
						assert release.wait(20), 'Paused worker timeout'

					callback = sync.subscribe({BLOCK_ID}, block)
					sync.publish_change([BLOCK_ID])
					assert entered.wait(5), 'Worker did not pause'

				elif mode == 'subscriber':
					callback = sync.subscribe({OWNER_ID}, lambda ids: None)

				# Separate LMDB commit for each mutation.
				# --------------------------------------------------------------
				started = time.perf_counter_ns()

				for index in range(size):
					memory.set('sync/perf/overhead', index, OWNER_ID)

				result['write_single'] = (time.perf_counter_ns() - started) / (1000 * size)

				if mode not in ('stub', 'paused'):
					cls._drain(sync)

				# Isolate publish_change from any LMDB activity.
				# --------------------------------------------------------------
				publish = memory.sync.publish_change
				ids     = [OWNER_ID]
				started = time.perf_counter_ns()

				for index in range(size):
					publish(ids, local=True)

				result['publish_only'] = (time.perf_counter_ns() - started) / (1000 * size)

			finally:
				if mode == 'paused':
					release.set()

				if callback is not None:
					sync.unsubscribe(callback)

				if mode != 'stub':
					cls._drain(sync)

				memory.env.close()

		return result

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	@classmethod
	def measure(cls, mode, size):
		return cls._measure(mode, size)


# Alternate subprocess modes to limit thermal and ordering bias.
# ------------------------------------------------------------------------------
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--size', type=int, default=10000)
	parser.add_argument('--rounds', type=int, default=5)
	parser.add_argument('--mode', choices=('all', 'stub', 'paused', 'worker', 'subscriber'), default='all')
	parser.add_argument('--_json', action='store_true', help=argparse.SUPPRESS)
	args = parser.parse_args()

	if args.size <= 0 or args.rounds <= 0:
		parser.error('size and rounds must be positive')

	if args._json:
		print(json.dumps(TestPerformanceSyncOverhead.measure(args.mode, args.size)))
	else:
		modes   = ('stub', 'paused', 'worker', 'subscriber') if args.mode == 'all' else (args.mode,)
		runner  = os.path.abspath(__file__)
		samples = {mode: {} for mode in modes}

		print(f'{args.rounds} rounds x {args.size} iterations; multiprocess=False.', flush=True)

		for round_index in range(args.rounds):
			order = modes if round_index % 2 == 0 else tuple(reversed(modes))

			for mode in order:
				print(f'Round {round_index + 1}/{args.rounds}: {mode}', flush=True)
				completed = subprocess.run(
					[sys.executable, runner, '--_json', '--mode', mode, '--size', str(args.size)],
					capture_output = True,
					text           = True,
				)

				if completed.returncode:
					raise RuntimeError(f'{mode}: ' + completed.stdout + completed.stderr)

				for name, microseconds in json.loads(completed.stdout.strip().splitlines()[-1]).items():
					samples[mode].setdefault(name, []).append(microseconds)

		print()
		print('Microseconds per operation: median [min..max]. Lower is faster.')
		print(f'{"Mode":12} {"Write + commit":>27} {"Publish only":>27}')
		print('-' * 69)

		for mode in modes:
			columns = []

			for name in ('write_single', 'publish_only'):
				values = samples[mode][name]
				columns.append(
					f'{statistics.median(values):8.3f} [{min(values):8.3f}..{max(values):8.3f}]'
				)

			print(f'{mode:12} {columns[0]:>27} {columns[1]:>27}')

		print()
		print('stub: no Sync publication')
		print('paused: real queue, worker blocked during timing')
		print('worker: real Sync, no application subscribers')
		print('subscriber: real Sync, one no-op subscriber')
		print('Differences include thread scheduling/GIL, not just method execution.')
