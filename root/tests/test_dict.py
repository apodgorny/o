import os
import shutil
import tempfile

import o

UNDEFINED = o.Undefined


class TestDict(o.Tester):

	# ----------------------------------------------------------------------
	@classmethod
	def _patch_registry(cls):
		services = o.services
		registry = type('RegistryState', (), {})()
		state    = {
			'services'      : services,
			'had_registry'  : 'Registry' in services.__dict__,
			'registry'      : services.__dict__.get('Registry'),
			'paths'         : {},
		}

		def add(id, path):
			state['paths'][id] = path

		def remove(id):
			if id in state['paths']:
				del state['paths'][id]

		def get(id):
			return state['paths'].get(id, UNDEFINED)

		registry.add    = add
		registry.remove = remove
		registry.get    = get

		services.Registry = registry

		return state

	# ----------------------------------------------------------------------
	@classmethod
	def _restore_registry(cls, state):
		services = state['services']

		if state['had_registry']:
			services.Registry = state['registry']
		else:
			del services.Registry

	# ----------------------------------------------------------------------
	@classmethod
	def _patch_runtime(cls):
		temp_root      = os.path.join(o.__path__, '__tmp__')
		registry_state = cls._patch_registry()

		os.makedirs(temp_root, exist_ok=True)

		root = tempfile.mkdtemp(prefix='o_dict_', dir=temp_root)

		state = {
			'root'          : root,
			'temp_root'     : temp_root,
			'registry'      : registry_state,
			'data_dir'      : o.DATA_DIR,
			'entities'      : dict(o.__entities__),
			'cast_map'      : dict(o.__cast_map__),
		}

		o.DATA_DIR = os.path.join('__tmp__', os.path.basename(root))

		return state

	# ----------------------------------------------------------------------
	@classmethod
	def _restore_runtime(cls, state):
		o.DATA_DIR = state['data_dir']

		o.__entities__.clear()
		o.__entities__.update(state['entities'])

		o.__cast_map__.clear()
		o.__cast_map__.update(state['cast_map'])

		cls._restore_registry(state['registry'])

		if os.path.isdir(state['temp_root']):
			shutil.rmtree(state['temp_root'])

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
	def test_dict_supports_object_attrs(cls):
		state = cls._patch_runtime()

		try:
			root_name               = os.path.basename(state['root'])
			DictSupportsObjectAttrs = o.T.extend(f'DictSupportsObjectAttrs_{root_name}', dict)
			x                       = DictSupportsObjectAttrs({'a': 1})
			x.title = 'scores'

			assert x.title == 'scores'
			assert o.services.Memory.get(f'{x.__proto__}.title', UNDEFINED) is not UNDEFINED
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
			x.tag = 'hot'
			id    = x.id
			proto = x.__proto__

			del o.__entities__[id]

			reopened = o.get(id)

			assert isinstance(reopened, ReconstructsDictOnCacheMiss)
			assert reopened.id == id
			assert reopened.__proto__ == proto
			assert dict(reopened.items()) == {'a': 1, 'b': 2}
			assert reopened.tag == 'hot'
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


if __name__ == '__main__':
	TestDict.run()
