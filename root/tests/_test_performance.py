import time
from tqdm import tqdm

import o


class TestPerformance(o.Tester):

	# Trigger list getitem
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_list_getitem(cls, n):
		x = o.List([1, 2, 3, 4, 5])

		for i in tqdm(range(n), desc='list_getitem'):
			k = i % 5
			x[k]

	# Trigger list setitem
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_list_setitem(cls, n):
		x = o.List([1, 2, 3, 4, 5])

		for i in tqdm(range(n), desc='list_setitem'):
			k    = i % 5
			x[k] = i

	# Trigger dict getitem
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_dict_getitem(cls, n):
		x    = o.Dict({'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5})
		keys = ['a', 'b', 'c', 'd', 'e']

		for i in tqdm(range(n), desc='dict_getitem'):
			k = keys[i % 5]
			x[k]

	# Trigger dict setitem
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_dict_setitem(cls, n):
		x    = o.Dict({'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5})
		keys = ['a', 'b', 'c', 'd', 'e']

		for i in tqdm(range(n), desc='dict_setitem'):
			k    = keys[i % 5]
			x[k] = i

		# Trigger object attr get
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_object_attr_get(cls, n, root_cls):
		APerfAttr = root_cls.extend('APerfAttrGet', x=int, y=int)
		x         = APerfAttr(x=1, y=2)

		for i in tqdm(range(n), desc='object_attr_get'):
			x.x
			x.y

	# Trigger object attr set
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_object_attr_set(cls, n, root_cls):
		APerfAttr = root_cls.extend('APerfAttrSet', x=int, y=int)
		x         = APerfAttr(x=1, y=2)

		for i in tqdm(range(n), desc='object_attr_set'):
			x.x = i
			x.y = i + 1

	# Trigger object creation
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_object_create(cls, n, root_cls):
		APerfCreate = root_cls.extend('APerfCreate', x=int, y=int)

		for i in tqdm(range(n), desc='object_create'):
			APerfCreate(x=i, y=i + 1)


	# # Trigger object getattr and setattr
	# # ----------------------------------------------------------------------
	# @classmethod
	# def trigger_object_attr(cls, n, root_cls):
	# 	APerfAttr = root_cls.extend('APerfAttr', x=int, y=int)
	# 	x         = APerfAttr(x=1, y=2)

	# 	for i in tqdm(range(n), desc='object_attr'):
	# 		x.x
	# 		x.y
	# 		x.x = i
	# 		x.y = i + 1

	# Trigger define
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_define(cls, n, root_cls):
		for i in tqdm(range(n), desc='define'):
			type_name = f'APerfDefine{i}'
			attempt   = 0

			while hasattr(root_cls, type_name):
				attempt  += 1
				type_name = f'APerfDefine{i}_{attempt}'

			root_cls.extend(type_name, x=int, y=int)

	# Performance test
	# ----------------------------------------------------------------------
	@classmethod
	def test_performance(cls):
		size = 5000
		n_attr   = size
		n_list   = size
		n_dict   = size
		n_define = size
		run_id   = time.time_ns()
		root_name = f'APerfRun{run_id}'
		PerfRoot  = o.T.extend(root_name)

		o.Timer.reset()

		with o.services.Memory.write():
			cls.trigger_list_getitem(n_list)
			cls.trigger_list_setitem(n_list)
			cls.trigger_dict_getitem(n_dict)
			cls.trigger_dict_setitem(n_dict)
			cls.trigger_object_attr_get(n_attr, PerfRoot)
			cls.trigger_object_attr_set(n_attr, PerfRoot)
			cls.trigger_object_create(n_attr, PerfRoot)
			cls.trigger_define(n_define, PerfRoot)

		# cls.trigger_list_getitem(n_list)
		# cls.trigger_list_setitem(n_list)
		# cls.trigger_dict_getitem(n_dict)
		# cls.trigger_dict_setitem(n_dict)
		# cls.trigger_object_attr_get(n_attr, PerfRoot)
		# cls.trigger_object_attr_set(n_attr, PerfRoot)
		# cls.trigger_object_create(n_attr, PerfRoot)
		# cls.trigger_define(n_define, PerfRoot)

		print()
		print(f'n_list   = {n_list}')
		print(f'n_dict   = {n_dict}')
		print(f'n_attr   = {n_attr}')
		print(f'n_define = {n_define}')
		print()

		o.Timer.report()


if __name__ == '__main__':
	TestPerformance.test_performance()
