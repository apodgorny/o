import o


class TestDefinition(o.Test):

	# ----------------------------------------------------------------------
	@classmethod
	def test_define_atomic(cls):
		Age = o.T.define('Age', int)
		x   = Age(10)

		assert issubclass(Age, o.One)
		assert Age.__annotation__ == o.Annotation(int)
		assert x.__cast_out__() == 10

	# ----------------------------------------------------------------------
	@classmethod
	def test_define_list(cls):
		Names = o.T.define('Names', list[str])
		x     = Names(['a', 'b'])

		assert issubclass(Names, o.List)
		assert Names.__annotation__ == o.Annotation(list[str])
		assert x.__cast_out__() == ['a', 'b']

	# ----------------------------------------------------------------------
	@classmethod
	def test_define_dict(cls):
		Scores = o.T.define('Scores', dict[str, int])
		x      = Scores({'a': 1, 'b': 2})

		assert issubclass(Scores, o.Dict)
		assert Scores.__annotation__ == o.Annotation(dict[str, int])
		assert x.__cast_out__() == {'a': 1, 'b': 2}

	# ----------------------------------------------------------------------
	@classmethod
	def test_define_object(cls):
		User = o.T.define('User', name=str, age=int)
		x    = User({'name': 'alex', 'age': 10})

		assert issubclass(User, o.Object)
		assert 'name' in User.__fields__
		assert 'age' in User.__fields__
		assert x.name == 'alex'
		assert x.age == 10
		assert x.__cast_out__() == {'name': 'alex', 'age': 10}

	# ----------------------------------------------------------------------
	@classmethod
	def test_define_object_with_field(cls):
		User = o.T.define(
			'UserWithField',
			name = o.F(
				name        = 'name',
				type        = str,
				description = None,
				default     = o.undefined,
			),
			age = int,
		)
		x = User({'name': 'alex', 'age': 10})

		assert issubclass(User, o.Object)
		assert x.name == 'alex'
		assert x.age == 10

	# ----------------------------------------------------------------------
	@classmethod
	def test_define_rejects_both_annotation_and_fields(cls):
		try:
			o.T.define('Bad', int, x=int)
			assert False
		except ValueError as e:
			assert 'Either named fields or annotation can/must be provided' in str(e)

	# ----------------------------------------------------------------------
	@classmethod
	def test_define_rejects_neither_annotation_nor_fields(cls):
		try:
			o.T.define('Bad')
			assert False
		except ValueError as e:
			assert 'Either named fields or annotation can/must be provided' in str(e)

	# ----------------------------------------------------------------------
	@classmethod
	def test_define_untyped_dict(cls):
		JustDict = o.T.define('JustDict', dict)
		x       = JustDict({'a': 1})

		assert issubclass(JustDict, o.Dict)
		assert JustDict.__annotation__ == o.Annotation(dict)
		assert x.__cast_out__() == {'a': 1}

	# ----------------------------------------------------------------------
	@classmethod
	def test_define_rejects_untyped_object_field_mix_is_not_allowed(cls):
		try:
			o.T.define('BadMix', list[int], age=int)
			assert False
		except ValueError as e:
			assert 'Either named fields or annotation can/must be provided' in str(e)

	# ----------------------------------------------------------------------
	@classmethod
	def test_defined_type_registered(cls):
		Token = o.T.define('Token', str)

		assert hasattr(Token, '__type_id__')
		assert Token.__type_id__ in o.__types_by_id__
		assert o.__types_by_id__[Token.__type_id__] is Token
		assert Token.__o_module__ == 'o.T.Token'


if __name__ == '__main__':
	TestDefinition.run()
