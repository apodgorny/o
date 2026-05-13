import os

import o


class TestDict(o.Tester):
	RUNTIME_PREFIX = 'o_dict_'

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_without_value_implies_empty_dict(cls):
		state = cls._patch_runtime()

		try:
			root_name  = os.path.basename(state['root'])
			EmptyDict  = o.T.extend(f'EmptyDict_{root_name}', dict)
			x          = EmptyDict()

			assert isinstance(x, EmptyDict)
			assert len(x) == 0
			assert dict(x.items()) == {}
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_basic_surface(cls):
		state = cls._patch_runtime()

		try:
			root_name        = os.path.basename(state['root'])
			DictBasicSurface = o.T.extend(f'DictBasicSurface_{root_name}', dict)
			x                = DictBasicSurface({'a': 1, 'b': 2})
			items            = o.services.Memory.get(f'{x.__proto__}.__items__')

			assert x.__zone__.prefix == f'{x.__proto__}.'
			assert x.__zone__.get('__items__') == items
			assert isinstance(items, bytes)
			assert len(items) == len(x) * 16
			assert x['a'] == 1
			assert x['b'] == 2
			assert 'a' in x
			assert 'c' not in x
			assert len(x) == 2
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_setitem_update_and_delitem(cls):
		state = cls._patch_runtime()

		try:
			root_name                   = os.path.basename(state['root'])
			DictSetitemUpdateAndDelitem = o.T.extend(f'DictSetitemUpdateAndDelitem_{root_name}', dict)
			x                           = DictSetitemUpdateAndDelitem({'a': 1})

			x['a'] = 3
			x.update({'b': 2, 'c': 4})
			del x['b']

			assert dict(x.items()) == {'a': 3, 'c': 4}
			assert len(x) == 2
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_non_atomic_value_surface(cls):
		state = cls._patch_runtime()

		try:
			root_name              = os.path.basename(state['root'])
			Child                  = o.T.extend(f'DictChild_{root_name}', name=str)
			DictNonAtomicValueSurf = o.T.extend(f'DictNonAtomicValueSurf_{root_name}', dict)
			x                      = DictNonAtomicValueSurf({'user': Child(name='alex')})
			items                  = dict(x.items())

			assert isinstance(x['user'], Child)
			assert x['user'].name == 'alex'
			assert isinstance(items['user'], Child)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_rejects_undeclared_object_attrs(cls):
		state = cls._patch_runtime()

		try:
			root_name               = os.path.basename(state['root'])
			DictSupportsObjectAttrs = o.T.extend(f'DictSupportsObjectAttrs_{root_name}', dict)
			x                       = DictSupportsObjectAttrs({'a': 1})

			try:
				x.title = 'scores'
				assert False
			except AttributeError as e:
				assert 'Field `title` is not defined' in str(e)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_get_reconstructs_dict_instance_on_cache_miss(cls):
		state = cls._patch_runtime()

		try:
			root_name                   = os.path.basename(state['root'])
			ReconstructsDictOnCacheMiss = o.T.extend(f'ReconstructsDictOnCacheMiss_{root_name}', dict)
			x                           = ReconstructsDictOnCacheMiss({'a': 1, 'b': 2})
			id    = x.id
			proto = x.__proto__

			del o.__entities__[id]

			reopened = o.get(id)

			assert isinstance(reopened, ReconstructsDictOnCacheMiss)
			assert reopened.id == id
			assert reopened.__proto__ == proto
			assert dict(reopened.items()) == {'a': 1, 'b': 2}
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_get_reconstructs_old_dict_items_storage(cls):
		state = cls._patch_runtime()

		try:
			root_name                        = os.path.basename(state['root'])
			ReconstructsOldDictItemsStorage = o.T.extend(f'ReconstructsOldDictItemsStorage_{root_name}', dict)
			x                                = ReconstructsOldDictItemsStorage({'a': 1, 'b': 2})
			id                               = x.id
			old_items                        = dict(x.__items__)

			x.__zone__.set('__items__', old_items)

			del o.__entities__[id]

			reopened = o.get(id)

			assert isinstance(reopened, ReconstructsOldDictItemsStorage)
			assert reopened.__items__ == old_items
			assert dict(reopened.items()) == {'a': 1, 'b': 2}
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_get_resolves_dict_n_proto_to_entity(cls):
		state = cls._patch_runtime()

		try:
			root_name                = os.path.basename(state['root'])
			Child                    = o.T.extend(f'DictNProtoChild_{root_name}', name=str)
			DictNProtoResolvesEntity = o.T.extend(f'DictNProtoResolvesEntity_{root_name}', dict)
			alex                     = Child(name='alex')
			bob                      = Child(name='bob')
			x                        = DictNProtoResolvesEntity({'a': alex, 'b': bob})
			key_id                   = x._item_key_id('b')
			child                    = o.get(x.__items__[key_id])
			resolved                 = o.get(f'{x.__proto__}[\'b\']')

			assert resolved is child
			assert isinstance(resolved, Child)
			assert resolved.name == 'bob'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dependants_yield_key_n_proto_and_child(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Child     = o.T.extend(f'DictDependantsChild_{root_name}', name=str)
			ChildDict = o.T.extend(f'DictDependants_{root_name}', dict)
			alex      = Child(name='alex')
			bob       = Child(name='bob')
			x         = ChildDict({'a': alex, 'b': bob})
			items     = list(x.__dependants__())

			assert items[0][0] == 'a'
			assert items[0][1] == f'{x.__proto__}[\'a\']'
			assert items[0][2] is alex
			assert items[1][0] == 'b'
			assert items[1][1] == f'{x.__proto__}[\'b\']'
			assert items[1][2] is bob
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestDict.run()
