import os
import shutil
import tempfile

import o

UNDEFINED = o.Undefined


class TestList(o.Tester):

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
		root           = None
		registry_state = cls._patch_registry()

		os.makedirs(temp_root, exist_ok=True)
		root = tempfile.mkdtemp(prefix='o_list_', dir=temp_root)

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

		if os.path.isdir(state['root']):
			shutil.rmtree(state['root'])

		if os.path.isdir(state['temp_root']):
			shutil.rmtree(state['temp_root'])

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_basic_surface(cls):
		state = cls._patch_runtime()

		try:
			x = o.List([1, 'a', None])

			assert len(x) == 3
			assert x[0] == 1
			assert x[1] == 'a'
			assert x[2] is None
			assert list(x) == [1, 'a', None]
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_setitem_append_and_delitem(cls):
		state = cls._patch_runtime()

		try:
			x        = o.List([1, 2])
			items    = o.services.Memory.get(f'{x.__proto__}.__items__', [])
			first_id = items[1]

			x[1] = 'b'
			x.append(3)
			del x[0]

			assert x[0] == 'b'
			assert x[1] == 3
			assert len(x) == 2
			assert o.services.Memory.get(f'{x.__proto__}.__items__', [])[0] != first_id
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_non_atomic_child_surface(cls):
		state = cls._patch_runtime()

		try:
			Child = o.T.extend(name=str)
			x     = o.List([Child(name='alex')])

			assert isinstance(x[0], Child)
			assert x[0].name == 'alex'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_supports_object_attrs(cls):
		state = cls._patch_runtime()

		try:
			x = o.List([1, 2, 3])
			x.title = 'numbers'

			assert x.title == 'numbers'
			assert o.services.Memory.get(f'{x.__proto__}.title', UNDEFINED) is not UNDEFINED
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_get_reconstructs_list_instance_on_cache_miss(cls):
		state = cls._patch_runtime()

		try:
			ReconstructsListOnCacheMiss = o.T.extend('ReconstructsListOnCacheMiss', list)
			x                           = ReconstructsListOnCacheMiss([1, 2, 3])
			x.tag = 'hot'
			id    = x.id
			proto = x.__proto__

			del o.__entities__[id]

			reopened = o.get(id)

			assert isinstance(reopened, ReconstructsListOnCacheMiss)
			assert reopened.id == id
			assert reopened.__proto__ == proto
			assert list(reopened) == [1, 2, 3]
			assert reopened.tag == 'hot'
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestList.run()
