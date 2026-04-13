import gc
import os
import shutil
import tempfile

import o


class TestGC(o.Test):

	# ----------------------------------------------------------------------
	@classmethod
	def _patch_registry(cls):
		services = o.services
		registry = type('RegistryState', (), {})()
		state    = {
			'services'     : services,
			'had_registry' : 'Registry' in services.__dict__,
			'registry'     : services.__dict__.get('Registry'),
			'paths'        : {},
		}

		def add(id, path):
			state['paths'][id] = path

		def remove(id):
			if id in state['paths']:
				del state['paths'][id]

		def get(id):
			return state['paths'].get(id, o.undefined)

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
		temp_root      = os.path.join(o.core_path, '__tmp__')
		registry_state = cls._patch_registry()

		os.makedirs(temp_root, exist_ok=True)

		root = tempfile.mkdtemp(prefix='o_gc_', dir=temp_root)

		state = {
			'root'      : root,
			'temp_root' : temp_root,
			'registry'  : registry_state,
			'data_dir'  : o.DATA_DIR,
			'entities'  : dict(o.__entities__),
			'cast_map'  : dict(o.__cast_map__),
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

		if os.path.exists(state['root']):
			shutil.rmtree(state['root'])

		if os.path.isdir(state['temp_root']) and not os.listdir(state['temp_root']):
			os.rmdir(state['temp_root'])

	# ----------------------------------------------------------------------
	@classmethod
	def test_instance_gc_deletes_runtime_entity_and_room(cls):
		state = cls._patch_runtime()

		try:
			GCProbe = o.T.extend('GCProbe', foo=str)

			x    = GCProbe(foo='hello')
			id   = x.id
			path = x.__disk_instance__.path

			assert id in o.__entities__
			assert os.path.exists(path) == True

			del x
			gc.collect()

			assert id not in o.__entities__
			assert os.path.exists(path) == False
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestGC.run()