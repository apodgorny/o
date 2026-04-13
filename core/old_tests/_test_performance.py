import hashlib

import o


class TestPerformance(o.Test):

	# Trigger list getitem
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_list_getitem(cls, n):
		x = o.List([1, 2, 3, 4, 5])

		for i in range(n):
			k = i % 5
			x[k]

	# Trigger list setitem
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_list_setitem(cls, n):
		x = o.List([1, 2, 3, 4, 5])

		for i in range(n):
			k    = i % 5
			x[k] = i

	# Trigger dict getitem
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_dict_getitem(cls, n):
		x = o.Dict({'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5})
		keys = ['a', 'b', 'c', 'd', 'e']

		for i in range(n):
			k = keys[i % 5]
			x[k]

	# Trigger dict setitem
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_dict_setitem(cls, n):
		x = o.Dict({'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5})
		keys = ['a', 'b', 'c', 'd', 'e']

		for i in range(n):
			k    = keys[i % 5]
			x[k] = i

	# Trigger object getattr and setattr
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_object_attr(cls, n):

		class APerfAttr(o.T):
			x: int
			y: int

		x = APerfAttr(x=1, y=2)

		for i in range(n):
			x.x
			x.y
			x.x = i
			x.y = i + 1

	# Trigger define
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_define(cls, n):
		defined = 0
		i       = 0

		while defined < n:
			type_name = f'APerfDefine{i}'
			o_module  = f'o.{type_name}'
			type_id   = int.from_bytes(hashlib.sha256(o_module.encode()).digest()[:2], 'little', signed=False)

			# Skip hash-occupied ids to avoid false "already exists" collisions.
			if type_id in o.__types_by_id__:
				i += 1
				continue

			type(
				type_name,
				(o.T,),
				{'__annotations__': {'x': int, 'y': int}},
			)
			defined += 1
			i += 1

	# Performance test
	# ----------------------------------------------------------------------
	@classmethod
	def test_performance(cls):
		n_attr    = 100_000
		n_list    = 100_000
		n_dict    = 100_000
		n_define  = 10_000

		o.Timer.reset()

		cls.trigger_list_getitem(n_list)
		cls.trigger_list_setitem(n_list)
		cls.trigger_dict_getitem(n_dict)
		cls.trigger_dict_setitem(n_dict)
		cls.trigger_object_attr(n_attr)
		cls.trigger_define(n_define)

		print()
		print(f'n_list   = {n_list}')
		print(f'n_dict   = {n_dict}')
		print(f'n_attr   = {n_attr}')
		print(f'n_define = {n_define}')
		print()
