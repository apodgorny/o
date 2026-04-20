import os
import shutil
import tempfile

import o


class TestAtomic(o.Test):

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
			return state['paths'].get(id, o.Undefined)

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

		root = tempfile.mkdtemp(prefix='o_atomic_', dir=temp_root)

		state = {
			'root'      : root,
			'temp_root' : temp_root,
			'registry'  : registry_state,
			'data_dir'  : o.DATA_DIR,
			'entities'  : dict(o.__entities__),
			'disk_classes' : dict(o.__disk_classes__),
			'cast_map'  : dict(o.__cast_map__),
			'value'     : o.__dict__.get('V', o.Undefined),
		}

		o.DATA_DIR = os.path.join('__tmp__', os.path.basename(root))

		return state

	# ----------------------------------------------------------------------
	@classmethod
	def _restore_runtime(cls, state):
		o.DATA_DIR = state['data_dir']

		o.__entities__.clear()
		o.__entities__.update(state['entities'])

		o.__disk_classes__.clear()
		o.__disk_classes__.update(state['disk_classes'])

		o.__cast_map__.clear()
		o.__cast_map__.update(state['cast_map'])

		if state['value'] is o.Undefined:
			if 'V' in o.__dict__:
				del o.__dict__['V']
		else:
			o.__dict__['V'] = state['value']

		cls._restore_registry(state['registry'])

		if os.path.exists(state['root']):
			shutil.rmtree(state['root'])

		if os.path.isdir(state['temp_root']):
			shutil.rmtree(state['temp_root'])

	# ----------------------------------------------------------------------
	@classmethod
	def test_atomic_roundtrip(cls):
		state = cls._patch_runtime()

		try:
			values = [
				(o.Int, 7),
				(o.Str, 'alex'),
				(o.Bool, True),
				(o.Float, 1.5),
				(o.Null, None),
			]

			for Type, value in values:
				x = Type(value)

				assert x.__value__ == value
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_atomic_type_validation(cls):
		state = cls._patch_runtime()

		try:
			raised_int  = False
			raised_str  = False
			raised_bool = False

			try:
				o.Int('7')
			except TypeError:
				raised_int = True

			try:
				o.Str(7)
			except TypeError:
				raised_str = True

			try:
				o.Bool('True')
			except TypeError:
				raised_bool = True

			assert raised_int == True
			assert raised_str == True
			assert raised_bool == True
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestAtomic.run()
