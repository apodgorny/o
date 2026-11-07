# ==============================================================================
# ONTOLOGY PERFORMANCE TEST
# ==============================================================================
# Measure complete workloads on an isolated store, with optional method timers.
# ==============================================================================

import argparse
import json
import os
import platform
import sys
import tempfile
import time

import o


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

	# Report complete elapsed workloads, independent of nested method totals.
	# ----------------------------------------------------------------------
	@classmethod
	def test_performance(cls, size=5000, workload='legacy'):
		root_cls  = o.T.extend('APerfRun')
		scenarios = [
			('list_getitem', size, cls.trigger_list_getitem, (size,)),
			('list_setitem', size, cls.trigger_list_setitem, (size,)),
			('dict_getitem', size, cls.trigger_dict_getitem, (size,)),
			('dict_setitem', size, cls.trigger_dict_setitem, (size,)),
		]

		if workload == 'legacy':
			scenarios.append(('object_attr_get_set', size, cls.trigger_object_attr, (size, root_cls)))
		else:
			scenarios.extend([
				('object_attr_get', size, cls.trigger_object_attr_get, (size, root_cls)),
				('object_attr_set', size, cls.trigger_object_attr_set, (size, root_cls)),
				('object_create', size, cls.trigger_object_create, (size, root_cls)),
			])

		scenarios.append(('define', size, cls.trigger_define, (size, root_cls)))
		o.Timer.reset()

		results = []
		mode    = 'instrumented' if o.Timer.enabled else 'wall-clock, timers disabled'

		print(f'Python:   {sys.version.split()[0]}')
		print(f'Platform: {platform.platform()}')
		print(f'Workload: {workload} ({size} iterations per scenario)')
		print(f'Timing:   {mode}, fixture creation excluded')
		if workload == 'legacy':
			print('object_attr_get_set: 2 reads + 2 writes per iteration')
		else:
			print('object_attr_get / object_attr_set: 2 accesses per iteration')

		print('All measurements include Python loop overhead.')
		print()

		for name, iterations, run, args in scenarios:
			print(f'Running {name}...', flush=True)
			seconds = run(*args)
			per_iter = seconds * 1e6 / iterations
			rate     = iterations / seconds
			results.append({
				'name'             : name,
				'iterations'       : iterations,
				'seconds'          : seconds,
				'us_per_iteration' : per_iter,
				'iterations_per_s' : rate,
			})
			print(f'{name:22} {iterations:>8,} iter  {seconds:>9.3f}s  {per_iter:>10,.3f} us/iter  {rate:>12,.1f} iter/s')

		if o.Timer.enabled:
			print()
			print('Inclusive method timings: nested durations overlap and must not be summed.')
			o.Timer.report()

		return results


# Run the same workload on a fresh database on each invocation.
# ----------------------------------------------------------------------
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--size', type=int, default=5000)
	parser.add_argument('--workload', choices=['legacy', 'expanded'], default='legacy')
	parser.add_argument('--instrumented', action='store_true')
	parser.add_argument('--output', default=None)
	args = parser.parse_args()

	if args.size <= 0:
		parser.error('--size must be positive')

	with tempfile.TemporaryDirectory(prefix='o_perf_') as root:
		o.start(os.path.join(root, 'ontology'))
		o.Timer.enabled = args.instrumented

		try:
			results = TestPerformance.test_performance(args.size, args.workload)
		finally:
			o.services.Memory.env.close()

	if args.output is not None:
		data = {
			'python'       : sys.version.split()[0],
			'platform'     : platform.platform(),
			'workload'     : args.workload,
			'size'         : args.size,
			'instrumented' : args.instrumented,
			'results'      : results,
		}

		with open(args.output, 'w') as file:
			json.dump(data, file, indent=2)

		print(f'Results written to {args.output}')
