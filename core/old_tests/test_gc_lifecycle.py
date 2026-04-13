import gc

import o


class TestGcLifecycle(o.Test):

	@classmethod
	def test_str_wrapper_gc_deletes_storage(cls):
		s = o.Str('abc')
		id_ = s.__id__

		del s
		gc.collect()

		try:
			o.Str.instantiate(id_)
			assert False
		except KeyError:
			pass

	@classmethod
	def test_dict_wrapper_gc_deletes_storage_and_key_record(cls):
		d = o.Dict({'a': 1})
		dict_id = d.__id__
		key_id = d.__refs__['a'][0].__id__

		del d
		gc.collect()

		try:
			o.Dict.instantiate(dict_id)
			assert False
		except KeyError:
			pass

		try:
			o.Key.instantiate(key_id).__cast_out__()
			assert False
		except (ValueError, OSError):
			pass

	@classmethod
	def test_object_wrapper_gc_deletes_storage_and_child_record(cls):
		x = o.Object({'age': 10})
		object_id = x.__id__
		child_id = x.__dict__['_attributes']['age']

		del x
		gc.collect()

		try:
			o.Object.__load__(object_id)
			assert False
		except FileNotFoundError:
			pass

		try:
			o.services.Store.read(child_id)
			assert False
		except FileNotFoundError:
			pass

	@classmethod
	def test_runtime_one_definition_file_removed_after_last_gc(cls):
		Age = o.T.define('TestGcLifecycleAgeSingle', int)
		type_id = Age.__type_id__
		x = Age(10)

		assert o.services.Definition.get_count(type_id) == 1

		del x
		gc.collect()

		try:
			o.services.Definition.get_count(type_id)
			assert False
		except FileNotFoundError:
			pass

	@classmethod
	def test_runtime_many_definition_file_removed_after_last_gc(cls):
		User = o.T.define('TestGcLifecycleUserSingle', name=str, age=int)
		type_id = User.__type_id__
		x = User(name='alex', age=10)

		assert o.services.Definition.get_count(type_id) == 1

		del x
		gc.collect()

		try:
			o.services.Definition.get_count(type_id)
			assert False
		except FileNotFoundError:
			pass


if __name__ == '__main__':
	TestGcLifecycle.run()
