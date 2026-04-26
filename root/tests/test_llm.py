import os
import shutil
import tempfile

import o


class TestLlm(o.Tester):

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
		root           = None
		registry_state = cls._patch_registry()

		os.makedirs(temp_root, exist_ok=True)
		root = tempfile.mkdtemp(prefix='o_llm_', dir=temp_root)

		state = {
			'root'          : root,
			'temp_root'     : temp_root,
			'registry'      : registry_state,
			'data_dir'      : o.DATA_DIR,
			'entities'      : dict(o.__entities__),
			'disk_classes'  : dict(o.__disk_classes__),
			'cast_map'      : dict(o.__cast_map__),
			'llm'           : o.llm,
		}

		o.DATA_DIR = os.path.join('__tmp__', os.path.basename(root))

		return state

	# ----------------------------------------------------------------------
	@classmethod
	def _restore_runtime(cls, state):
		o.DATA_DIR = state['data_dir']
		o.llm      = state['llm']

		o.__entities__.clear()
		o.__entities__.update(state['entities'])

		o.__disk_classes__.clear()
		o.__disk_classes__.update(state['disk_classes'])

		o.__cast_map__.clear()
		o.__cast_map__.update(state['cast_map'])

		cls._restore_registry(state['registry'])
		shutil.rmtree(state['root'])

		if os.path.isdir(state['temp_root']):
			shutil.rmtree(state['temp_root'])

	# ----------------------------------------------------------------------
	@classmethod
	def test_generated_dict_can_embody_into_o_instance(cls):
		state = cls._patch_runtime()

		try:
			User  = o.T.extend(
				'LlmUser',
				name = str,
				age  = o.F(int, default=None),
			)
			model = o.models.Ollama('gemma3:4b')
			data  = None
			user  = None

			o.llm = model
			data  = o.generate(
				'Return a user with name Ada and age 37.',
				User.to_json_schema(),
				temperature = 0.0,
				verbose = False,
			)
			user = User(**data)

			assert data == { 'name' : 'Ada', 'age' : 37 }
			assert o.llm is model
			assert isinstance(user, User)
			assert user.name == 'Ada'
			assert user.age == 37
		finally:
			cls._restore_runtime(state)
