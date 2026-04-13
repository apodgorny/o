import o


class TestRuntimeTypesInContainers(o.Test):

	# ----------------------------------------------------------------------
	@classmethod
	def test_runtime_one_in_list_roundtrip(cls):
		Age = o.T.define('TestRuntimeAgeInList', int)

		x = o.List([Age(10), Age(20)])

		assert x[0] == 10
		assert x[1] == 20
		assert isinstance(x.__refs__[0], Age)
		assert isinstance(x.__refs__[1], Age)

		y = o.List.instantiate(x.__id__)

		assert y[0] == 10
		assert y[1] == 20
		assert isinstance(y.__refs__[0], Age)
		assert isinstance(y.__refs__[1], Age)

	# ----------------------------------------------------------------------
	@classmethod
	def test_runtime_one_in_dict_roundtrip(cls):
		Age = o.T.define('TestRuntimeAgeInDict', int)

		x = o.Dict({'a': Age(10), 'b': Age(20)})

		assert x['a'] == 10
		assert x['b'] == 20
		assert isinstance(x.__refs__['a'][1], Age)
		assert isinstance(x.__refs__['b'][1], Age)

		y = o.Dict.instantiate(x.__id__)

		assert y['a'] == 10
		assert y['b'] == 20
		assert isinstance(y.__refs__['a'][1], Age)
		assert isinstance(y.__refs__['b'][1], Age)

	# ----------------------------------------------------------------------
	@classmethod
	def test_runtime_one_in_object_roundtrip(cls):
		Age  = o.T.define('TestRuntimeAgeInObject', int)
		User = o.T.define('TestRuntimeUserWithAge', age=Age, name=str)

		x = User({'age': Age(33), 'name': 'alex'})

		assert x.age == 33
		assert x.name == 'alex'
		age_id = x.__dict__['_attributes']['age']
		age_module, _, _, _, _, _, _ = o.services.Store.read(age_id)
		assert age_module == Age.__o_module__

		y = User.__load__(x.__id__)

		assert y.age == 33
		assert y.name == 'alex'
		assert y.__cast_out__() == {'age': 33, 'name': 'alex'}
		assert set(y.__dict__['_attributes'].keys()) == {'age', 'name'}

	# ----------------------------------------------------------------------
	@classmethod
	def test_runtime_list_type_roundtrip(cls):
		Names = o.T.define('TestRuntimeNames', list[str])

		x = Names(['a', 'b'])

		assert x.__cast_out__() == ['a', 'b']

		y = Names.instantiate(x.__id__)

		assert y.__cast_out__() == ['a', 'b']

	# ----------------------------------------------------------------------
	@classmethod
	def test_runtime_dict_type_roundtrip(cls):
		Scores = o.T.define('TestRuntimeScores', dict[str, int])

		x = Scores({'a': 1, 'b': 2})

		assert x.__cast_out__() == {'a': 1, 'b': 2}

		y = Scores.instantiate(x.__id__)

		assert y.__cast_out__() == {'a': 1, 'b': 2}

	# ----------------------------------------------------------------------
	@classmethod
	def test_runtime_object_in_list_roundtrip(cls):
		User = o.T.define('TestRuntimeUserInList', name=str, age=int)

		x = o.List([
			User({'name': 'a', 'age': 1}),
			User({'name': 'b', 'age': 2}),
		])

		assert x[0] == {'name': 'a', 'age': 1}
		assert x[1] == {'name': 'b', 'age': 2}
		assert isinstance(x.__refs__[0], User)
		assert isinstance(x.__refs__[1], User)

		y = o.List.instantiate(x.__id__)

		assert y[0] == {'name': 'a', 'age': 1}
		assert y[1] == {'name': 'b', 'age': 2}
		assert isinstance(y.__refs__[0], User)
		assert isinstance(y.__refs__[1], User)


if __name__ == '__main__':
	TestRuntimeTypesInContainers.run()
