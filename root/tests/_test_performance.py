# ==============================================================================
# ONTOLOGY PERFORMANCE TEST
# ==============================================================================
# Measure complete workloads on an isolated store, with optional method timers.
# ==============================================================================

import argparse
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

	# Time whole iterations without counting fixture construction.
	# ----------------------------------------------------------------------
	@classmethod
	def test_performance(cls, size=5000, workload='legacy'):
		root  = o.T.extend('APerfRun')
		cases = [
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

		print(f'Python {sys.version.split()[0]}, {platform.platform()}, {workload}, n={size}')
		print('Time per iteration (fixture construction excluded).')

		for name, run, args in cases:
			print(f'Running {name}...', flush=True)
			seconds = run(*args)
			print(f'{name:22} {seconds:9.3f}s   {seconds * 1e6 / size:10.3f} us/iter')

		if o.Timer.enabled:
			print('Inclusive method times (nested calls overlap):')
			o.Timer.report()


# Run the same workload on a fresh database on each invocation.
# ----------------------------------------------------------------------
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--size', type=int, default=5000)
	parser.add_argument('--workload', choices=['legacy', 'expanded'], default='legacy')
	parser.add_argument('--instrumented', action='store_true')
	args = parser.parse_args()

	if args.size <= 0:
		parser.error('--size must be positive')

	with tempfile.TemporaryDirectory(prefix='o_perf_') as root:
		o.start(os.path.join(root, 'ontology'))
		o.Timer.enabled = args.instrumented

		try:
			TestPerformance.test_performance(args.size, args.workload)
		finally:
			o.services.Memory.env.close()

