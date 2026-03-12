import os


import o


class TestDict(o.Test):

	@classmethod
	def test_basic_set_get(cls):
		o.Str('asdf')
		o.Int(10)
		d = o.Dict()
		d['a'] = 1
		assert d['a'] == 1

	@classmethod
	def test_overwrite(cls):
		d = o.Dict()
		d['a'] = 1
		d['a'] = 2
		assert d['a'] == 2

	@classmethod
	def test_delete_existing(cls):
		d = o.Dict()
		d['a'] = 1
		del d['a']

		try:
			d['a']
			assert False
		except KeyError:
			pass

	@classmethod
	def test_delete_missing_keyerror(cls):
		d = o.Dict()

		try:
			del d['missing']
			assert False
		except KeyError:
			pass

	@classmethod
	def test_get_missing_keyerror(cls):
		d = o.Dict()

		try:
			d['missing']
			assert False
		except KeyError:
			pass

	# ----------------------------------------------------------------------
	# CONTAINER PROTOCOL (Object.__len__/__iter__/__contains__)
	# ----------------------------------------------------------------------

	@classmethod
	def test_contains_len_iter(cls):
		d = o.Dict()
		d['a'] = 1
		d['b'] = 2

		assert ('a' in d) == True
		assert ('c' in d) == False

		assert len(d) == 2

		keys = list(iter(d))
		assert ('a' in keys) == True
		assert ('b' in keys) == True
		assert ('c' in keys) == False

	# ----------------------------------------------------------------------
	# CAST / UNCAST VALUES
	# ----------------------------------------------------------------------

	@classmethod
	def test_cast_atomic_values(cls):
		d = o.Dict()
		d['i'] = 10
		d['s'] = 'x'
		d['b'] = True
		d['f'] = 1.5

		assert d['i'] == 10
		assert d['s'] == 'x'
		assert d['b'] == True
		assert d['f'] == 1.5

	@classmethod
	def test_non_homogenous_values_are_supported(cls):
		d = o.Dict()
		d['i'] = 10
		d['s'] = 'x'
		d['l'] = [1, 2]
		d['d'] = {'k': 1}

		assert d['i'] == 10
		assert d['s'] == 'x'
		assert isinstance(d['l'], o.List)
		assert isinstance(d['d'], o.Dict)
		assert d['l'] == [1, 2]
		assert d['d'] == {'k': 1}

	@classmethod
	def test_value_as_object_roundtrip(cls):
		d = o.Dict()

		x = o.Int(7)
		d['x'] = x

		y = d['x']

		assert int(y) == 7

	# ----------------------------------------------------------------------
	# PERSISTENCE / REOPEN
	# ----------------------------------------------------------------------

	@classmethod
	def test_persistence_reopen_by_id(cls):
		d1 = o.Dict()
		d1['a'] = 1
		d1['b'] = 2

		d2 = o.Dict.instantiate(d1.__id__)

		assert d2['a'] == 1
		assert d2['b'] == 2

	@classmethod
	def test_commit_persistence(cls):
		d1 = o.Dict()
		d1['a'] = 1

		o.services.Many.commit()

		d2 = o.Dict.instantiate(d1.__id__)
		assert d2['a'] == 1

	# ----------------------------------------------------------------------
	# ISOLATION
	# ----------------------------------------------------------------------

	@classmethod
	def test_isolation_between_dicts(cls):
		d1 = o.Dict()
		d2 = o.Dict()

		d1['a'] = 1
		d2['a'] = 2

		assert d1['a'] == 1
		assert d2['a'] == 2

	# ----------------------------------------------------------------------
	# KEY BEHAVIOR
	# - Dict keys may be any hashable value.
	# - Composite unhashable keys must fail.
	# ----------------------------------------------------------------------

	@classmethod
	def test_key_length_policy_is_consistent(cls):
		d = o.Dict()

		key = 'x' * 200
		d[key] = 1

		assert d[key] == 1

	@classmethod
	def test_tuple_key_not_supported(cls):
		d = o.Dict()
		key = ('a', 'b')

		try:
			d[key] = 'ok'
			assert False
		except TypeError as e:
			assert 'Unsupported cast type `tuple`' in str(e)

	@classmethod
	def test_hashable_object_key_roundtrip(cls):
		class ObjKey(o.Str):
			pass

		d = o.Dict()
		key = ObjKey('x')

		d[key] = 7
		assert d[key] == 7

	# ----------------------------------------------------------------------
	# MANY REINDEX AFTER DELETE
	# ----------------------------------------------------------------------

	@classmethod
	def test_reindex_after_delete(cls):
		d = o.Dict()

		d['a'] = 1
		d['b'] = 2
		d['c'] = 3

		del d['b']

		assert d['a'] == 1
		assert d['c'] == 3

		try:
			d['b']
			assert False
		except KeyError:
			pass

		d['b'] = 22
		assert d['b'] == 22

	@classmethod
	def test_bind_snapshot_requires_reload(cls):
		d1 = o.Dict()
		d2 = o.Dict.instantiate(d1.__id__)

		d1['a'] = 1
		d2.__read__()
		assert d2['a'] == 1

		d2['b'] = 2
		d1.__read__()
		assert d1['b'] == 2

	@classmethod
	def test_iter_preserves_insertion_order(cls):
		d = o.Dict()
		d['a'] = 1
		d['c'] = 3
		d['b'] = 2

		assert list(iter(d)) == ['a', 'c', 'b']

	@classmethod
	def test_overwrite_does_not_change_len(cls):
		d = o.Dict()
		d['a'] = 1
		d['a'] = 2

		assert len(d) == 1

	@classmethod
	def test_value_reference_is_live_object(cls):
		d = o.Dict()
		x = o.Int(7)
		d['x'] = x

		x.__write__(9)
		assert d['x'] == 9

	@classmethod
	def test_unsupported_value_type_raises(cls):
		d = o.Dict()

		try:
			d['x'] = object()
			assert False
		except TypeError:
			pass

	@classmethod
	def test_non_hashable_key_raises(cls):
		d = o.Dict()

		try:
			d[[]] = 1
			assert False
		except TypeError:
			pass

	@classmethod
	def test_clear_empties_all_indexes(cls):
		d = o.Dict()
		d['a'] = 1
		d['b'] = 2

		d.__clear__()

		assert len(d) == 0
		assert list(iter(d)) == []
		assert ('a' in d) == False

	@classmethod
	def test_delete_dict_removes_storage(cls):
		d = o.Dict()
		d['a'] = 1
		id_ = d.__id__

		d.__delete__()

		try:
			o.Dict.instantiate(id_)['a']
			assert False
		except Exception:
			pass

	@classmethod
	def test_python_composite_values_are_supported(cls):

		d = o.Dict({
			'a': [1, 2],
			'b': {'x': 10}
		})

		v0 = d['a']
		v1 = d['b']

		assert isinstance(v0, o.List)
		assert isinstance(v1, o.Dict)

		assert v0 == [1, 2]
		assert v1 == {'x': 10}

	@classmethod
	def test_wrapped_composite_values_roundtrip(cls):

		d = o.Dict({
			'a': o.List([1, 2]),
			'b': o.Dict({'x': 10}),
		})

		list_obj = d['a']
		dict_obj = d['b']

		# Composite всегда возвращаются как wrapper
		assert isinstance(list_obj, o.List)
		assert isinstance(dict_obj, o.Dict)

		assert list_obj == [1, 2]
		assert dict_obj == {'x': 10}

	@classmethod
	def test_key_cleanup_after_delete_entry(cls):
		d = o.Dict()
		d['a'] = 1

		ref = d.__index__['a']
		key_t, key_i = ref

		del d['a']

		try:
			o.__types_by_id__[key_t].instantiate(key_i).__cast_out__()
			assert False
		except (KeyError, ValueError):
			pass

	@classmethod
	def test_atomic_int_key_roundtrip(cls):
		d = o.Dict()
		d[1] = 'one'
		assert d[1] == 'one'

	@classmethod
	def test_atomic_bool_key_roundtrip(cls):
		d = o.Dict()
		d[True] = 'yes'
		d[False] = 'no'

		assert d[True] == 'yes'
		assert d[False] == 'no'

	@classmethod
	def test_atomic_float_key_roundtrip(cls):
		d = o.Dict()
		d[1.5] = 'x'
		assert d[1.5] == 'x'

	@classmethod
	def test_composite_python_key_list_prohibited(cls):
		d = o.Dict()

		try:
			d[[1, 2]] = 3
			assert False
		except TypeError:
			pass

	@classmethod
	def test_composite_python_key_dict_prohibited(cls):
		d = o.Dict()

		try:
			d[{'k': 1}] = 3
			assert False
		except TypeError:
			pass

	@classmethod
	def test_composite_o_key_list_prohibited(cls):
		d = o.Dict()

		try:
			d[o.List([1, 2])] = 3
			assert False
		except TypeError:
			pass

	@classmethod
	def test_composite_o_key_dict_prohibited(cls):
		d = o.Dict()

		try:
			d[o.Dict({'k': 1})] = 3
			assert False
		except TypeError:
			pass


if __name__ == '__main__':
	TestDict.run()
	print('\nAll tests passed')
