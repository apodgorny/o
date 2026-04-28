import os
import shutil
import tempfile

import o

UNDEFINED = o.Undefined


class TestJsonPrompt(o.Tester):

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
		root = tempfile.mkdtemp(prefix='o_json_prompt_', dir=temp_root)

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
	def test_plain_t_has_no_single_prompt(cls):
		raised = False

		try:
			o.T.to_prompt()
		except TypeError as e:
			raised = '`o.T` has no single JSON prompt' in str(e)

		assert raised == True

	# ----------------------------------------------------------------------
	@classmethod
	def test_atomic_prompt(cls):
		assert o.Str.to_prompt() == 'str'
		assert o.Int.to_prompt() == 'int'
		assert o.Float.to_prompt() == 'float'
		assert o.Bool.to_prompt() == 'bool'
		assert o.Null.to_prompt() == 'null'

	# ----------------------------------------------------------------------
	@classmethod
	def test_container_prompt(cls):
		state = cls._patch_runtime()

		try:
			root_name    = os.path.basename(state['root'])
			ListOfString = o.T.extend(f'JsonPromptListOfString_{root_name}', list[str])
			DictOfInt    = o.T.extend(f'JsonPromptDictOfInt_{root_name}', dict[str, int])

			assert ListOfString.to_prompt() == '[str]'
			assert DictOfInt.to_prompt() == (
				'{\n'
				'    \'key\' : int  # str key\n'
				'}'
			)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_object_prompt_uses_declared_fields_and_description(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			User = o.T.extend(
				f'JsonPromptUser_{root_name}',
				name = o.F(str, description='Human readable full name'),
				age  = o.F(int, description='Age', default=None),
			)

			assert User.to_prompt() == (
				'{\n'
				'    \'age\'  : int | null,  # Age\n'
				'    \'name\' : str          # Human readable full name\n'
				'}'
			)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_nested_object_prompt_is_recursive(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Child  = o.T.extend(
				f'JsonPromptChild_{root_name}',
				name = o.F(str, description='Child name'),
			)
			Parent = o.T.extend(
				f'JsonPromptParent_{root_name}',
				child = o.F(Child, description='Nested child'),
			)

			assert Parent.to_prompt() == (
				'{\n'
				'    \'child\' : {      # Nested child\n'
				'        \'name\' : str # Child name\n'
				'    }\n'
				'}'
			)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_field_prompt_keeps_field_and_key_comments_separate(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			User = o.T.extend(
				f'JsonPromptDictFieldUser_{root_name}',
				scores = o.F(dict[str, int], description='Score by subject'),
			)

			assert User.to_prompt() == (
				'{\n'
				'    \'scores\' : {      # Score by subject\n'
				'        \'key\' : int   # str key\n'
				'    }\n'
				'}'
			)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_of_object_prompt_uses_nested_class(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Contact = o.T.extend(
				f'JsonPromptListObjectContact_{root_name}',
				email = o.F(str, description='Primary email'),
			)
			User = o.T.extend(
				f'JsonPromptListObjectUser_{root_name}',
				contacts = o.F(list[Contact], description='Previous contacts'),
			)

			assert User.to_prompt() == (
				'{\n'
				'    \'contacts\' : [         # Previous contacts\n'
				'        {\n'
				'            \'email\' : str  # Primary email\n'
				'        }\n'
				'    ]\n'
				'}'
			)
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestJsonPrompt.run()
