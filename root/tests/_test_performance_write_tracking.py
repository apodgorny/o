# ==============================================================================
# TRANSACTIONAL WRITE TRACKING PERFORMANCE
# ==============================================================================
# Compare identical persistent writes on master and two-call IPL code.
# Each timing run starts with fresh storage; use median microseconds per operation.
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


class TestPerformanceWriteTracking(o.Tester):

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Time individual commits, one grouped commit, raw writes, and zone removal.
	# ----------------------------------------------------------------------
	@classmethod
	def measure(cls, size):
		memory = o.services.Memory
		zone   = memory.zone('o.T.WriteBench._1.')
		result = {}

		# One new commit per write; captures the per-commit notification cost.
		# ----------------------------------------------------------------------
		started = time.perf_counter_ns()

		for index in range(size):
			zone.set('single', index)

		result['zone_set_single'] = (time.perf_counter_ns() - started) / (1000 * size)

		# Many updates to one owner share a single notification pair.
		# ----------------------------------------------------------------------
		started = time.perf_counter_ns()

		with memory.write():
			for index in range(size):
				zone.set('batch', index)

		result['zone_set_batch'] = (time.perf_counter_ns() - started) / (1000 * size)

		# Low-level writes must derive identity from storage keys.
		# ----------------------------------------------------------------------
		started = time.perf_counter_ns()

		for index in range(size):
			memory.set('o.T.WriteBench._2.value', index)

		result['memory_set_single'] = (time.perf_counter_ns() - started) / (1000 * size)

		# A cached zone read must not pay any IPL notification cost.
		# ----------------------------------------------------------------------
		started = time.perf_counter_ns()

		for index in range(size):
			zone.get('batch')

		result['zone_cached_get'] = (time.perf_counter_ns() - started) / (1000 * size)

		# Clearing many keys from one instance zone is one transaction.
		# ----------------------------------------------------------------------
		with memory.write():
			for index in range(size):
				zone.set(f'field_{index}', index)

		started = time.perf_counter_ns()
		zone.clear()
		result['zone_clear'] = (time.perf_counter_ns() - started) / (1000 * size)

		return result


# Repeated measurements use independent stores and alternating run order.
# ------------------------------------------------------------------------------
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--size', type=int, default=2000)
	parser.add_argument('--rounds', type=int, default=5)
	parser.add_argument('--ipl', choices=['none', 'stub'], default='none')
	parser.add_argument('--_json', action='store_true', help=argparse.SUPPRESS)
	args = parser.parse_args()

	if args.size <= 0 or args.rounds <= 0:
		parser.error('--size and --rounds must be positive')

	if args._json:
		with tempfile.TemporaryDirectory(prefix='o_write_perf_') as directory:
			type(o).__app__ = SimpleNamespace(__lib_path__=directory)
			o.start()

			if args.ipl == 'stub':
				o.services.Memory.ipl = SimpleNamespace(
					pre_invalidate = lambda ids: None,
					invalidate     = lambda ids: None,
				)

			try:
				results = TestPerformanceWriteTracking.measure(args.size)
				print(json.dumps(results))
			finally:
				o.services.Memory.env.close()
	else:
		measurements = {}
		runner       = os.path.abspath(__file__)

		print(f'{args.rounds} rounds × {args.size} operations; IPL: {args.ipl}.', flush=True)

		for index in range(args.rounds):
			completed = subprocess.run(
				[sys.executable, runner, '--size', str(args.size), '--ipl', args.ipl, '--_json'],
				capture_output = True,
				text           = True,
			)

			if completed.returncode:
				raise RuntimeError(completed.stdout + completed.stderr)

			for operation, microseconds in json.loads(completed.stdout).items():
				measurements.setdefault(operation, []).append(microseconds)

		print('Microseconds per operation: median [min..max]. Lower is faster.')
		print(f'{"Operation":24}  {"Median":>9}  {"Min":>9}  {"Max":>9}')

		for operation, samples in measurements.items():
			print(
				f'{operation:24}  {statistics.median(samples):9.3f}  '
				f'{min(samples):9.3f}  {max(samples):9.3f}'
			)
