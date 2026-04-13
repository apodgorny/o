import o


class TestObject(o.Test):

	@classmethod
	def test_default_and_kwargs_construction(cls):
		x = o.Object()
		y = o.Object(a=1, b=2)

		assert x.__cast_out__() == {}
		assert x.__dict__.get('_attributes', {}) == {}

		assert y.a == 1
		assert y.b == 2
		assert y.__cast_out__() == {'a': 1, 'b': 2}
		assert set(y.__dict__['_attributes'].keys()) == {'a', 'b'}

	@classmethod
	def test_get_set_and_unset_low_level_methods(cls):
		x = o.Object({'a': 1})

		type_id, item_id = x.__get__('a')

		next_value = o.Int(2)
		x.__set__('a', next_value.__type_id__, next_value.__id__, next_value)

		assert x.a == 2
		assert x.__cast_out__() == {'a': 2}
		assert x.__get__('a') == (next_value.__type_id__, next_value.__id__)

		x.__unset__('a')

		assert x.__cast_out__() == {}
		assert 'a' not in x.__dict__['_attributes']

	@classmethod
	def test_delattr_removes_field(cls):
		x = o.Object({'name': 'alex', 'age': 33})

		del x.age

		assert x.__cast_out__() == {'name': 'alex'}

		try:
			x.age
			assert False
		except AttributeError:
			pass

	@classmethod
	def test_children_yield_declared_fields(cls):
		class UserChildren(o.Object):
			name: str
			age: int

		x = UserChildren(name='alex', age=33)

		assert list(x.__children__()) == [
			('name', 'alex'),
			('age', 33),
		]

	@classmethod
	def test_reopen_builds_full_graph_and_cast_out(cls):
		class UserRead(o.Object):
			age: int
			name: str

		x = UserRead(age=33, name='alex')
		y = UserRead.__load__(x.__id__)

		assert y.age == 33
		assert y.name == 'alex'
		assert y.__cast_out__() == {'age': 33, 'name': 'alex'}
		assert set(y.__dict__['_attributes'].keys()) == {'age', 'name'}

	@classmethod
	def test_internal_attributes_are_not_serialized(cls):
		x = o.Object({'a': 1})
		x._internal = 'x'

		x.__write__()

		_, attributes, _, _, _, _, _ = o.services.Store.read(x.__id__)
		assert attributes == x.__dict__['_attributes']
		assert '_internal' not in attributes

	@classmethod
	def test_internal_state_stays_consistent_after_mutations(cls):
		x = o.Object({'a': 1, 'b': 2})

		x.a = 10
		x.c = 'x'
		del x.b

		assert x.__cast_out__() == {'a': 10, 'c': 'x'}
		assert set(x.__dict__['_attributes'].keys()) == {'a', 'c'}

		x.__clear__()

		assert x.__cast_out__() == {}
		assert x.__dict__['_attributes'] == {}

	@classmethod
	def test_invalid_field_names_raise(cls):
		x = o.Object()

		for bad in ('a b', 'a-b', '1abc'):
			try:
				setattr(x, bad, 1)
				assert False
			except ValueError:
				pass

		try:
			setattr(x, 'x' * 33, 1)
			assert False
		except ValueError:
			pass

	@classmethod
	def test_delete_removes_storage_and_children(cls):
		x = o.Object({'age': 10})
		object_id = x.__id__
		child_id = x.__dict__['_attributes']['age']

		x.__delete__()

		assert x.__dict__['_attributes'] == {}

		try:
			o.services.Store.read(object_id)
			assert False
		except FileNotFoundError:
			pass

		try:
			o.services.Store.read(child_id)
			assert False
		except FileNotFoundError:
			pass


if __name__ == '__main__':
	TestObject.run()
