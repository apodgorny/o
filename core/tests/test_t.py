import o


class TestT(o.Test):

	@classmethod
	def test_requires_root_value(cls):
		try:
			o.T()
			assert False
		except TypeError:
			pass

	@classmethod
	def test_passthrough_for_existing_o_instance(cls):
		x = o.Int(10)
		y = o.T(x)

		assert y is x
		assert int(y) == 10

	@classmethod
	def test_dispatch_atomic_values(cls):
		assert isinstance(o.T(1), o.Int)
		assert isinstance(o.T(1.5), o.Float)
		assert isinstance(o.T(True), o.Bool)
		assert isinstance(o.T('x'), o.Str)
		assert isinstance(o.T(None), o.Null)

	@classmethod
	def test_dispatch_list_and_dict(cls):
		l = o.T([1, 'a', True])
		d = o.T({'a': 1})

		assert isinstance(l, o.List)
		assert isinstance(d, o.Dict)

		assert l[0] == 1
		assert l[1] == 'a'
		assert l[2] == True
		assert d['a'] == 1

	@classmethod
	def test_nested_heterogenous_embodiment(cls):
		root = o.T([
			1,
			'v',
			{'k': [2, 3.0, None]},
			[True, {'x': 10}],
		])

		assert isinstance(root, o.List)
		assert root[0] == 1
		assert root[1] == 'v'

		d0 = root[2]
		l0 = root[3]

		assert isinstance(d0, o.Dict)
		assert isinstance(l0, o.List)

		assert isinstance(d0['k'], o.List)
		assert d0['k'][0] == 2
		assert d0['k'][1] == 3.0
		assert d0['k'][2] is None

		assert l0[0] == True
		assert isinstance(l0[1], o.Dict)
		assert l0[1]['x'] == 10

	@classmethod
	def test_subclass_uses_normal_construction_path(cls):
		class CustomT(o.T):
			pass

		obj = CustomT(123)

		assert isinstance(obj, CustomT)
		assert obj.__id__ is None

	@classmethod
	def test_unsupported_root_type_raises(cls):
		class X:
			pass

		try:
			o.T(X())
			assert False
		except TypeError:
			pass


if __name__ == '__main__':
	TestT.run()
	print('\nAll tests passed')
