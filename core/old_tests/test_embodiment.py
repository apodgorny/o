import o


class TestEmbodiment(o.Test):

	# ----------------------------------------------------------------------
	@classmethod
	def test_atomic_int(cls):
		x = o.T(1)

		assert isinstance(x, o.Int)
		assert x.__cast_out__() == 1

	# ----------------------------------------------------------------------
	@classmethod
	def test_atomic_str(cls):
		x = o.T('x')

		assert isinstance(x, o.Str)
		assert x.__cast_out__() == 'x'

	# ----------------------------------------------------------------------
	@classmethod
	def test_atomic_none(cls):
		x = o.T(None)

		assert isinstance(x, o.Null)
		assert x.__cast_out__() is None

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_basic(cls):
		x = o.T([1, 'x', None])

		assert isinstance(x, o.List)
		assert x.__cast_out__() == [1, 'x', None]

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_basic(cls):
		x = o.T({'a': 1, 'b': 'x'})

		assert isinstance(x, o.Dict)
		assert x.__cast_out__() == {'a': 1, 'b': 'x'}

	# ----------------------------------------------------------------------
	@classmethod
	def test_nested_basic(cls):
		x = o.T([
			{
				'a' : [1, None, 'x'],
				'b' : {'c': 2},
			}
		])

		assert isinstance(x, o.List)
		assert x.__cast_out__() == [
			{
				'a' : [1, None, 'x'],
				'b' : {'c': 2},
			}
		]

	# ----------------------------------------------------------------------
	@classmethod
	def test_passthrough(cls):
		x = o.Str('abc')
		y = o.T(x)
		assert y is x

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_children_embodied(cls):
		x = o.T([1, 'x', None])

		assert isinstance(x.__refs__[0], o.Int)
		assert isinstance(x.__refs__[1], o.Str)
		assert isinstance(x.__refs__[2], o.Null)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_children_embodied(cls):
		x = o.T({'a': 1})

		key_obj, value_obj = x.__refs__['a']

		assert isinstance(key_obj, o.Str)
		assert isinstance(value_obj, o.Int)

	# ----------------------------------------------------------------------
	@classmethod
	def test_tuple_not_supported(cls):
		try:
			o.T((1, 2))
			assert False
		except TypeError as e:
			assert 'Cannot cast' in str(e)

	# ----------------------------------------------------------------------
	@classmethod
	def test_object_not_supported(cls):
		class X:
			pass

		try:
			o.T(X())
			assert False
		except TypeError as e:
			assert 'Cannot cast' in str(e)

		# ----------------------------------------------------------------------
	@classmethod
	def test_t_subclass_empty(cls):

		class A1(o.T):
			x: int
			y: int

		x = A1()

		assert isinstance(x, A1)

	# ----------------------------------------------------------------------
	@classmethod
	def test_t_subclass_kwargs(cls):

		class A2(o.T):
			x: int
			y: int

		x = A2(x=1, y=2)

		assert isinstance(x, A2)
		assert x.x == 1
		assert x.y == 2

	# ----------------------------------------------------------------------
	@classmethod
	def test_t_subclass_partial_kwargs(cls):

		class A3(o.T):
			x: int
			y: int

		x = A3(x=1)

		assert isinstance(x, A3)
		assert x.x == 1

	# ----------------------------------------------------------------------
	@classmethod
	def test_t_subclass_setattr_after_empty(cls):

		class A4(o.T):
			x: int
			y: int

		x   = A4()
		x.x = 1
		x.y = 2

		assert isinstance(x, A4)
		assert x.x == 1
		assert x.y == 2

	# ----------------------------------------------------------------------
	@classmethod
	def test_t_nested_subclass_kwargs(cls):

		class B1(o.T):
			z: int

		class A5(o.T):
			b: B1

		x = A5(b=B1(z=3))

		assert isinstance(x, A5)
		assert isinstance(x.b, B1)
		assert x.b.z == 3


if __name__ == '__main__':
	TestEmbodiment.run()
