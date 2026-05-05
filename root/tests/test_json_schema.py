import os

import o


class TestJsonSchema(o.Tester):
	RUNTIME_PREFIX = 'o_json_schema_'

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
					'description' : { 'type' : 'string' },
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
					'description' : { 'type' : 'string' },
					'child' : { '$ref' : f'#/$defs/{Child.__proto__}' },
				},
				'required'             : ['child'],
				'additionalProperties' : False,
				'$defs'                : {
					Child.__proto__ : {
						'type'                 : 'object',
						'properties'           : {
							'description' : { 'type' : 'string' },
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
