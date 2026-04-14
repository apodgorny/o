import os
import shutil
import tempfile

import o


class TestBuiltins(o.Test):

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

		root = tempfile.mkdtemp(prefix='o_builtins_', dir=temp_root)

		state = {
			'root'      : root,
			'temp_root' : temp_root,
			'registry'  : registry_state,
			'data_dir'  : o.DATA_DIR,
			'entities'  : dict(o.__entities__),
			'cast_map'  : dict(o.__cast_map__),
			'value'     : o.__dict__.get('V', o.undefined),
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

		if state['value'] is o.undefined:
			if 'V' in o.__dict__:
				del o.__dict__['V']
		else:
			o.__dict__['V'] = state['value']

		cls._restore_registry(state['registry'])

		if os.path.isdir(state['temp_root']):
			shutil.rmtree(state['temp_root'])

	# ----------------------------------------------------------------------
	@classmethod
	def test_atomic_builtin_method_returns_python_value(cls):
		state = cls._patch_runtime()

		try:
			x      = o.Str('alex')
			result = x.upper()

			assert result == 'ALEX'
			assert x.__value__ == 'alex'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_builtin_method_mutates_in_place(cls):
		state = cls._patch_runtime()

		try:
			x      = o.List([3, 1, 2])
			result = x.sort()

			assert result is None
			assert list(x) == [1, 2, 3]
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_builtin_method_mutates_and_returns_python_value(cls):
		state = cls._patch_runtime()

		try:
			x      = o.List([1, 2, 3])
			result = x.pop()

			assert result == 3
			assert list(x) == [1, 2]
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_builtin_method_mutates_and_returns_python_value(cls):
		state = cls._patch_runtime()

		try:
			x      = o.Dict({'a': 1, 'b': 2})
			result = x.pop('a')

			assert result == 1
			assert dict(x.items()) == {'b': 2}
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestBuiltins.run()
