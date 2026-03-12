import o


class TestReuseDeleteSymmetry(o.Test):

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_same_type_overwrite_reuses_child(cls):
		x = o.List([1])

		before = x.__refs__[0].__id__
		x[0] = 2
		after = x.__refs__[0].__id__

		assert before == after
		assert x[0] == 2

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_different_type_overwrite_replaces_child(cls):
		x = o.List([1])

		before_type = x.__refs__[0].__class__
		before_id   = x.__refs__[0].__id__

		x[0] = 'a'

		after_type = x.__refs__[0].__class__
		after_id   = x.__refs__[0].__id__

		assert before_type is not after_type
		assert before_id != after_id
		assert x[0] == 'a'

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_same_type_overwrite_reuses_child(cls):
		x = o.Dict({'a': 1})

		before = x.__refs__['a'][1].__id__
		x['a'] = 2
		after = x.__refs__['a'][1].__id__

		assert before == after
		assert x['a'] == 2

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_different_type_overwrite_replaces_child(cls):
		x = o.Dict({'a': 1})

		before_type = x.__refs__['a'][1].__class__
		before_id   = x.__refs__['a'][1].__id__

		x['a'] = 'b'

		after_type = x.__refs__['a'][1].__class__
		after_id   = x.__refs__['a'][1].__id__

		assert before_type is not after_type
		assert before_id != after_id
		assert x['a'] == 'b'

	# ----------------------------------------------------------------------
	@classmethod
	def test_object_same_type_overwrite_reuses_child(cls):
		class User1(o.Object):
			age: int

		x = User1({'age': 10})

		before = x.__refs__['age'][1].__id__
		x.age = 20
		after = x.__refs__['age'][1].__id__

		assert before == after
		assert x.age == 20

	# ----------------------------------------------------------------------
	@classmethod
	def test_object_different_type_overwrite_replaces_child(cls):
		class User2(o.Object):
			value: int

		x = User2({'value': 10})

		before_type = x.__refs__['value'][1].__class__
		before_id   = x.__refs__['value'][1].__id__

		x.value = 'abc'

		after_type = x.__refs__['value'][1].__class__
		after_id   = x.__refs__['value'][1].__id__

		assert before_type is not after_type
		assert before_id != after_id
		assert x.value == 'abc'

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_delete_reindexes_refs(cls):
		x = o.List([1, 2, 3])

		second_id = x.__refs__[1].__id__
		del x[0]

		assert len(x) == 2
		assert x[0] == 2
		assert x.__refs__[0].__id__ == second_id

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_delete_removes_key_ref_and_value(cls):
		x = o.Dict({'a': 1, 'b': 2})

		assert 'a' in x.__index__
		assert 'a' in x.__refs__

		del x['a']

		assert 'a' not in x.__index__
		assert 'a' not in x.__refs__
		assert x['b'] == 2

	# ----------------------------------------------------------------------
	@classmethod
	def test_object_delete_removes_accessor_ref_and_value(cls):
		class User3(o.Object):
			name: str
			age: int

		x = User3({'name': 'alex', 'age': 10})

		assert 'age' in x.__index__
		assert 'age' in x.__refs__

		del x.age

		assert 'age' not in x.__index__
		assert 'age' not in x.__refs__
		assert x.name == 'alex'

	# ----------------------------------------------------------------------
	@classmethod
	def test_nested_list_clear_symmetry(cls):
		x = o.List([
			{'a': [1, 2]},
			{'b': [3, 4]},
		])

		x.__clear__()

		assert len(x.__items__) == 0
		assert len(x.__refs__) == 0
		assert x.__cast_out__() == []

	# ----------------------------------------------------------------------
	@classmethod
	def test_nested_dict_clear_symmetry(cls):
		x = o.Dict({
			'a': [1, 2],
			'b': {'x': 3},
		})

		x.__clear__()

		assert len(x.__items__) == 0
		assert len(x.__index__) == 0
		assert len(x.__ref_index__) == 0
		assert len(x.__refs__) == 0
		assert x.__cast_out__() == {}

	# ----------------------------------------------------------------------
	@classmethod
	def test_nested_object_clear_symmetry(cls):
		class User4(o.Object):
			name: str
			data: dict

		x = User4({
			'name': 'alex',
			'data': {'scores': [1, 2, 3]},
		})

		x.__clear__()

		assert len(x.__items__) == 0
		assert len(x.__index__) == 0
		assert len(x.__refs__) == 0
		assert x.__cast_out__() == {}


if __name__ == '__main__':
	TestReuseDeleteSymmetry.run()
