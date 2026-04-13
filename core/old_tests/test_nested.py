import o


class TestNested(o.Test):

	@classmethod
	def test_list_contains_nested_dict_and_list(cls):
		l = o.List([
			1,
			{'a': [2, 3.0, None]},
			[True, {'x': 'y'}],
		])

		assert l[0] == 1

		d0 = l[1]
		l0 = l[2]

		assert isinstance(d0, o.Dict)
		assert isinstance(l0, o.List)

		assert isinstance(d0['a'], o.List)
		assert d0['a'][0] == 2
		assert d0['a'][1] == 3.0
		assert d0['a'][2] is None

		assert l0[0] == True
		assert isinstance(l0[1], o.Dict)
		assert l0[1]['x'] == 'y'

	@classmethod
	def test_dict_contains_nested_list_and_dict(cls):
		d = o.Dict({
			'numbers': [1, 2.0, '3'],
			'obj': {'k': 10},
		})

		assert isinstance(d['numbers'], o.List)
		assert isinstance(d['obj'], o.Dict)

		assert d['numbers'][0] == 1
		assert d['numbers'][1] == 2.0
		assert d['numbers'][2] == '3'
		assert d['obj']['k'] == 10

	@classmethod
	def test_deep_nesting_roundtrip(cls):
		d1 = o.Dict({'k': [1, {'x': [2, 3]}]})
		id_ = d1.__id__
		d2 = o.Dict.instantiate(id_)

		assert isinstance(d2['k'], o.List)
		assert d2['k'][0] == 1
		assert isinstance(d2['k'][1], o.Dict)
		assert isinstance(d2['k'][1]['x'], o.List)
		assert d2['k'][1]['x'][0] == 2
		assert d2['k'][1]['x'][1] == 3

	@classmethod
	def test_multiple_bind_consistency(cls):
		d1 = o.Dict({'a': [1, 2]})
		id_ = d1.__id__

		d2 = o.Dict.instantiate(id_)
		d3 = o.Dict.instantiate(id_)

		assert isinstance(d2['a'], o.List)
		assert isinstance(d3['a'], o.List)
		assert d2['a'][0] == 1
		assert d3['a'][1] == 2

	@classmethod
	def test_type_identity_stable_for_wrappers(cls):
		i = o.Int(99)
		l = o.List([i])

		item_obj = l.__refs__[0]

		assert i.__class__.__type_id__ == o.Int.__type_id__
		assert item_obj.__class__.__type_id__ == o.Int.__type_id__
