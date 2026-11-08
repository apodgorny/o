# ==============================================================================
# ONTOLOGY PERFORMANCE TEST
# ==============================================================================
# Measure complete workloads on an isolated store, with optional method timers.
# ==============================================================================

import argparse
import cProfile
import io
import json
import os
import platform
import pstats
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time

import o


BEFORE_TREE_REF = '6b2d40532081342575259b194a4d4509c5f3436b'


class TestPerformance(o.Tester):

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Read existing list elements without timing fixture construction.
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_list_getitem(cls, n):
		x       = o.List([1, 2, 3, 4, 5])
		started = time.perf_counter_ns()

		for i in range(n):
			x[i % 5]

		return (time.perf_counter_ns() - started) / 1e9

	# Replace existing list elements with fresh integer values.
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_list_setitem(cls, n):
		x       = o.List([1, 2, 3, 4, 5])
		started = time.perf_counter_ns()

		for i in range(n):
			x[i % 5] = i

		return (time.perf_counter_ns() - started) / 1e9

	# Read existing dictionary values without timing fixture construction.
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_dict_getitem(cls, n):
		x       = o.Dict({'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5})
		keys    = ['a', 'b', 'c', 'd', 'e']
		started = time.perf_counter_ns()

		for i in range(n):
			x[keys[i % 5]]

		return (time.perf_counter_ns() - started) / 1e9

	# Replace dictionary values, preserving the original five keys.
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_dict_setitem(cls, n):
		x       = o.Dict({'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5})
		keys    = ['a', 'b', 'c', 'd', 'e']
		started = time.perf_counter_ns()

		for i in range(n):
			x[keys[i % 5]] = i

		return (time.perf_counter_ns() - started) / 1e9

	# Read two previously materialized object attributes per iteration.
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_object_attr_get(cls, n, root_cls):
		APerfAttr = root_cls.extend('APerfAttrGet', x=int, y=int)
		x         = APerfAttr(x=1, y=2)
		started   = time.perf_counter_ns()

		for i in range(n):
			x.x
			x.y

		return (time.perf_counter_ns() - started) / 1e9

	# Write two object attributes per iteration.
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_object_attr_set(cls, n, root_cls):
		APerfAttr = root_cls.extend('APerfAttrSet', x=int, y=int)
		x         = APerfAttr(x=1, y=2)
		started   = time.perf_counter_ns()

		for i in range(n):
			x.x = i
			x.y = i + 1

		return (time.perf_counter_ns() - started) / 1e9

	# Preserve BEFORE's interleaved two-read, two-write attribute workload.
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_object_attr(cls, n, root_cls):
		APerfAttr = root_cls.extend('APerfAttr', x=int, y=int)
		x         = APerfAttr(x=1, y=2)
		started   = time.perf_counter_ns()

		for i in range(n):
			x.x
			x.y
			x.x = i
			x.y = i + 1

		return (time.perf_counter_ns() - started) / 1e9

	# Create instances with two initialized fields.
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_object_create(cls, n, root_cls):
		APerfCreate = root_cls.extend('APerfCreate', x=int, y=int)
		started     = time.perf_counter_ns()

		for i in range(n):
			APerfCreate(x=i, y=i + 1)

		return (time.perf_counter_ns() - started) / 1e9

	# Define distinct classes, including checks for pre-existing names.
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_define(cls, n, root_cls):
		started = time.perf_counter_ns()

		for i in range(n):
			type_name = f'APerfDefine{i}'
			attempt   = 0

			while hasattr(root_cls, type_name):
				attempt  += 1
				type_name = f'APerfDefine{i}_{attempt}'

			root_cls.extend(type_name, x=int, y=int)

		return (time.perf_counter_ns() - started) / 1e9


	# Time each workload with fresh fixtures, optionally profiling one case.
	# ----------------------------------------------------------------------
	@classmethod
	def test_performance(cls, size=10000, workload='legacy', quiet=False, profile_case=None, profile_top=20):
		root    = o.T.extend('APerfRun')
		results = {}
		cases   = [
			('list_getitem', cls.trigger_list_getitem, (size,)),
			('list_setitem', cls.trigger_list_setitem, (size,)),
			('dict_getitem', cls.trigger_dict_getitem, (size,)),
			('dict_setitem', cls.trigger_dict_setitem, (size,)),
		]

		if workload == 'legacy':
			cases.append(('object_attr_get_set', cls.trigger_object_attr, (size, root)))
		else:
			cases.extend([
				('object_attr_get', cls.trigger_object_attr_get, (size, root)),
				('object_attr_set', cls.trigger_object_attr_set, (size, root)),
				('object_create', cls.trigger_object_create, (size, root)),
			])

		cases.append(('define', cls.trigger_define, (size, root)))
		o.Timer.reset()

		if not quiet:
			mode = getattr(o, 'TREE_MODE', 'before')
			print(f'Python {sys.version.split()[0]}, {platform.platform()}, tree_mode={mode}, {workload}, n={size}')
			print('Time per iteration (fixture construction excluded).')

		for name, run, parameters in cases:
			if profile_case is None or profile_case in (name, 'all'):
				if not quiet:
					print(f'Running {name}...', flush=True)

				profiler = cProfile.Profile() if profile_case is not None else None

				if profiler is not None:
					profiler.enable()

				seconds = run(*parameters)

				if profiler is not None:
					profiler.disable()

				results[name] = seconds * 1e6 / size

				if not quiet:
					print(f'{name:22} {seconds:9.3f}s   {results[name]:10.3f} us/iter')

				if profiler is not None:
					output = io.StringIO()
					pstats.Stats(profiler, stream=output).sort_stats('cumtime').print_stats(profile_top)
					print('cProfile (timings above include profiler overhead; do not compare with unprofiled runs):')
					print(output.getvalue())

		if o.Timer.enabled and not quiet:
			print('Inclusive method times (nested calls overlap):')
			o.Timer.report()

		return results


# Repeat each mode in isolated processes, alternating order across rounds.
# ------------------------------------------------------------------------------
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--size', type=int, default=10000)
	parser.add_argument('--rounds', type=int, default=5)
	parser.add_argument('--workload', choices=['legacy', 'expanded'], default='legacy')
	parser.add_argument('--instrumented', action='store_true')
	parser.add_argument('--mode', choices=['both', 'tree', 'graph', 'before'], default='both')
	parser.add_argument('--baseline', action='store_true', help='Compare with the pre-tree commit using a temporary git archive')
	parser.add_argument('--profile', action='store_true', help='Run cProfile separately after the timing rounds')
	parser.add_argument('--profile-case', choices=[
		'list_getitem', 'list_setitem', 'dict_getitem', 'dict_setitem',
		'object_attr_get_set', 'object_attr_get', 'object_attr_set',
		'object_create', 'define', 'all',
	], default='dict_setitem')
	parser.add_argument('--profile-top', type=int, default=20)
	parser.add_argument('--_json', action='store_true', help=argparse.SUPPRESS)
	parser.add_argument('--_profile_only', action='store_true', help=argparse.SUPPRESS)
	args = parser.parse_args()

	if args.size <= 0 or args.rounds <= 0 or args.profile_top <= 0:
		parser.error('--size, --rounds and --profile-top must be positive')

	if args.baseline and args.mode != 'both':
		parser.error('--baseline requires --mode both')

	if args.mode == 'before' and not (args._json or args._profile_only):
		parser.error('--mode before is reserved for the isolated baseline runner')

	if args._json or args._profile_only:
		with tempfile.TemporaryDirectory(prefix=f'o_perf_{args.mode}_') as directory:
			if args.mode == 'before':
				o.start(os.path.join(directory, 'ontology'))
			else:
				o.start(os.path.join(directory, 'ontology'), tree_mode=args.mode == 'tree')

			o.Timer.enabled = args.instrumented

			try:
				results = TestPerformance.test_performance(
					args.size,
					args.workload,
					quiet        = args._json,
					profile_case = args.profile_case if args._profile_only else None,
					profile_top  = args.profile_top,
				)

				if args._json:
					print(json.dumps(results))
			finally:
				o.services.Memory.env.close()
	else:
		with tempfile.TemporaryDirectory(prefix='o_perf_compare_') as directory:
			runners = {
				'tree'  : os.path.abspath(__file__),
				'graph' : os.path.abspath(__file__),
			}
			modes = ['tree', 'graph'] if args.mode == 'both' else [args.mode]

			if args.baseline:
				repository = subprocess.check_output(
					['git', '-C', os.path.dirname(__file__), 'rev-parse', '--show-toplevel'],
					text = True,
				).strip()
				archive = subprocess.run(
					['git', '-C', repository, 'archive', '--format=tar', BEFORE_TREE_REF],
					check          = True,
					capture_output = True,
				).stdout
				baseline = os.path.join(directory, 'before')
				os.mkdir(baseline)

				with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as bundle:
					bundle.extractall(baseline, filter='data')

				runners['before'] = os.path.join(baseline, '_benchmark_runner.py')
				shutil.copyfile(__file__, runners['before'])
				modes.insert(0, 'before')

			measurements = {mode: {} for mode in modes}
			print(f'{args.rounds} rounds × {args.size} iterations; independent LMDB per run.', flush=True)

			for round_index in range(args.rounds):
				order = modes if round_index % 2 == 0 else list(reversed(modes))

				for mode in order:
					print(f'Round {round_index + 1}/{args.rounds}: {mode}', flush=True)
					command = [
						sys.executable, runners[mode],
						'--size', str(args.size),
						'--workload', args.workload,
						'--mode', mode,
						'--_json',
					]
					environment = dict(os.environ)

					if mode == 'before':
						environment['PYTHONPATH'] = baseline + os.pathsep + environment.get('PYTHONPATH', '')

					if args.instrumented:
						command.append('--instrumented')

					completed = subprocess.run(
						command,
						check          = True,
						capture_output = True,
						text           = True,
						env            = environment,
					)
					values = json.loads(completed.stdout)

					for operation, microseconds in values.items():
						measurements[mode].setdefault(operation, []).append(microseconds)

			print()
			print('Microseconds per iteration: median [min..max]. Lower is faster.')
			header = f'{"Operation":22}' + ''.join(f'{mode:>27}' for mode in modes)
			print(header)
			print('-' * len(header))

			for operation in measurements[modes[0]]:
				line = f'{operation:22}'

				for mode in modes:
					values = measurements[mode][operation]
					median = statistics.median(values)
					line += f' {median:8.3f} [{min(values):7.3f}..{max(values):7.3f}]'

				if 'tree' in modes and 'graph' in modes:
					on  = statistics.median(measurements['tree'][operation])
					off = statistics.median(measurements['graph'][operation])
					line += f'  ON/OFF {100 * (on / off - 1):+6.1f}%'

				print(line)

			if args.profile:
				print()
				print('Independent cProfile runs (not used for benchmark medians).', flush=True)

				for mode in modes:
					print(f'Profiling {mode}: {args.profile_case}', flush=True)
					command = [
						sys.executable, runners[mode],
						'--size', str(args.size),
						'--workload', args.workload,
						'--mode', mode,
						'--profile-case', args.profile_case,
						'--profile-top', str(args.profile_top),
						'--_profile_only',
					]
					environment = dict(os.environ)

					if mode == 'before':
						environment['PYTHONPATH'] = baseline + os.pathsep + environment.get('PYTHONPATH', '')

					subprocess.run(command, check=True, env=environment)
