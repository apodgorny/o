# ==============================================================================
# TRACKER PERFORMANCE TEST
# ==============================================================================
# Compare identical O workloads with tracking disabled or read-only.
# Reuse the regular benchmark operations, with isolated storage per run.
# ==============================================================================

import argparse
import json
import os
import statistics
import subprocess
import sys
import tempfile

from contextlib import nullcontext
from types import SimpleNamespace

import o

from _test_performance import TestPerformance


class TestPerformanceTracker(o.Tester):

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Run the unchanged benchmark operations inside one tracking mode.
	# ----------------------------------------------------------------------
	@classmethod
	def measure(cls, size, workload, mode, profile_case=None, profile_top=20):
		reads = []
		scope = nullcontext()

		if mode == 'r':
			scope = o.services.Tracker.track_reads(reads)

		with scope:
			results = TestPerformance.test_performance(
				size,
				workload,
				quiet        = profile_case is None,
				profile_case = profile_case,
				profile_top  = profile_top,
			)

		return results


# Compare runs in alternating order without sharing an LMDB or process.
# ------------------------------------------------------------------------------
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--size', type=int, default=10000)
	parser.add_argument('--rounds', type=int, default=5)
	parser.add_argument('--workload', choices=['legacy', 'expanded'], default='legacy')
	parser.add_argument('--mode', choices=['all', 'none', 'r'], default='all')
	parser.add_argument('--tree-mode', choices=['graph', 'tree'], default='graph')
	parser.add_argument('--profile', action='store_true')
	parser.add_argument('--instrumented', action='store_true')
	parser.add_argument('--profile-case', choices=[
		'list_getitem', 'list_setitem', 'dict_getitem', 'dict_setitem',
		'object_attr_get_set', 'object_attr_get', 'object_attr_set',
		'object_create', 'define', 'all',
	], default='dict_setitem')
	parser.add_argument('--profile-top', type=int, default=20)
	parser.add_argument('--_mode', choices=['none', 'r'], help=argparse.SUPPRESS)
	parser.add_argument('--_json', action='store_true', help=argparse.SUPPRESS)
	parser.add_argument('--_profile_only', action='store_true', help=argparse.SUPPRESS)
	args = parser.parse_args()

	if args.size <= 0 or args.rounds <= 0 or args.profile_top <= 0:
		parser.error('--size, --rounds and --profile-top must be positive')

	if args.instrumented and not (args.profile or args._profile_only):
		parser.error('--instrumented requires --profile')

	if args.profile and args.workload == 'legacy':
		if args.profile_case in ('object_attr_get', 'object_attr_set', 'object_create'):
			parser.error('selected --profile-case requires --workload expanded')

	if args.profile and args.workload == 'expanded' and args.profile_case == 'object_attr_get_set':
		parser.error('object_attr_get_set requires --workload legacy')

	if args._json or args._profile_only:
		if args._mode is None:
			parser.error('internal tracking mode is required')

		with tempfile.TemporaryDirectory(prefix=f'o_perf_tracker_{args._mode}_') as directory:
			type(o).__app__ = SimpleNamespace(__lib_path__=directory)
			o.start(tree_mode=args.tree_mode == 'tree')
			o.Timer.enabled = args.instrumented and args._profile_only

			try:
				results = TestPerformanceTracker.measure(
					args.size,
					args.workload,
					args._mode,
					profile_case = args.profile_case if args._profile_only else None,
					profile_top  = args.profile_top,
				)

				if args._json:
					print(json.dumps(results))
			finally:
				o.services.Memory.env.close()
	else:
		modes        = ['none', 'r'] if args.mode == 'all' else [args.mode]
		measurements = {mode: {} for mode in modes}
		runner       = os.path.abspath(__file__)

		print(f'{args.rounds} rounds × {args.size} iterations; independent LMDB per run.', flush=True)
		print(f'Ontology: {args.tree_mode}; tracker modes: {", ".join(modes)}', flush=True)

		for round_index in range(args.rounds):
			order = modes if round_index % 2 == 0 else list(reversed(modes))

			for mode in order:
				print(f'Round {round_index + 1}/{args.rounds}: {mode}', flush=True)
				command = [
					sys.executable, runner,
					'--size', str(args.size),
					'--workload', args.workload,
					'--tree-mode', args.tree_mode,
					'--_mode', mode,
					'--_json',
				]
				completed = subprocess.run(command, capture_output=True, text=True)

				if completed.returncode:
					raise RuntimeError(f'Benchmark {mode} failed:\n{completed.stderr}')

				values = json.loads(completed.stdout)

				for operation, microseconds in values.items():
					measurements[mode].setdefault(operation, []).append(microseconds)

		print()
		print('Microseconds per iteration: median [min..max]. Lower is faster.')
		header = 'Operation'.ljust(22) + ''.join(f'{mode:>29}' for mode in modes)
		print(header)
		print('-' * len(header))

		for operation in measurements[modes[0]]:
			line = f'{operation:22}'

			for mode in modes:
				values = measurements[mode][operation]
				median = statistics.median(values)
				line += f' {median:8.3f} [{min(values):7.3f}..{max(values):7.3f}]'

			if 'none' in modes:
				baseline = statistics.median(measurements['none'][operation])

				for mode in modes:
					if mode != 'none':
						observed = statistics.median(measurements[mode][operation])
						line += f'  {mode}/none {100 * (observed / baseline - 1):+6.1f}%'

			print(line)

		if args.profile:
			print()
			print('Independent cProfile runs (excluded from timing medians).', flush=True)

			for mode in modes:
				print(f'Profiling {mode}: {args.profile_case}', flush=True)
				command = [
					sys.executable, runner,
					'--size', str(args.size),
					'--workload', args.workload,
					'--tree-mode', args.tree_mode,
					'--_mode', mode,
					'--profile-case', args.profile_case,
					'--profile-top', str(args.profile_top),
					'--_profile_only',
				]

				if args.instrumented:
					command.append('--instrumented')

				subprocess.run(command, check=True)