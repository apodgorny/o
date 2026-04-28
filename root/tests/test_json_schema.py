import os
import shutil
import tempfile

import o

UNDEFINED = o.Undefined


class TestJsonSchema(o.Tester):

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
		root = tempfile.mkdtemp(prefix='o_json_schema_', dir=temp_root)

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
	def test_plain_t_has_no_single_schema(cls):
		raised = False

		try:
			o.T.to_json_schema()
		except TypeError as e:
			raised = '`o.T` has no single JSON schema' in str(e)

		assert raised == True

	# ----------------------------------------------------------------------
	@classmethod
	def test_atomic_schema(cls):
		assert o.Str.to_json_schema() == { 'type' : 'string' }
		assert o.Int.to_json_schema() == { 'type' : 'integer' }
		assert o.Float.to_json_schema() == { 'type' : 'number' }
		assert o.Bool.to_json_schema() == { 'type' : 'boolean' }
		assert o.Null.to_json_schema() == { 'type' : 'null' }

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_schema(cls):
		state = cls._patch_runtime()

		try:
			root_name    = os.path.basename(state['root'])
			ListOfString = o.T.extend(f'JsonSchemaListOfString_{root_name}', list[str])

			assert ListOfString.to_json_schema() == {
				'type'  : 'array',
				'items' : { 'type' : 'string' },
			}
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_schema(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			DictOfInt = o.T.extend(f'JsonSchemaDictOfInt_{root_name}', dict[str, int])

			assert DictOfInt.to_json_schema() == {
				'type'                 : 'object',
				'additionalProperties' : { 'type' : 'integer' },
			}
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_object_schema_uses_declared_fields(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			User = o.T.extend(
				f'JsonSchemaUser_{root_name}',
				name=str,
				age=o.F(int, default=None),
			)

			assert User.to_json_schema() == {
				'type'                 : 'object',
				'properties'           : {
					'name' : { 'type' : 'string' },
					'age'  : { 'type' : ['integer', 'null'] },
				},
				'required'             : ['name'],
				'additionalProperties' : False,
			}
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_object_schema_uses_defs_for_nested_child(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Child     = o.T.extend(f'JsonSchemaChild_{root_name}', name=str)
			Parent    = o.T.extend(f'JsonSchemaParent_{root_name}', child=Child)

			assert Parent.to_json_schema() == {
				'type'                 : 'object',
				'properties'           : {
					'child' : { '$ref' : f'#/$defs/{Child.__proto__}' },
				},
				'required'             : ['child'],
				'additionalProperties' : False,
				'$defs'                : {
					Child.__proto__ : {
						'type'                 : 'object',
						'properties'           : {
							'name' : { 'type' : 'string' },
						},
						'required'             : ['name'],
						'additionalProperties' : False,
					}
				},
			}
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestJsonSchema.run()
