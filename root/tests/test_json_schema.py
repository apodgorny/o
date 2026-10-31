import os
import runpy

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

	# Filter only generated fields, including nested objects, without changing the full type schema.
	# ----------------------------------------------------------------------
	@classmethod
	def test_prompt_schema_filters_nested_fields(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Child = o.T.extend(
				f'PromptSchemaChild_{root_name}',
				seen   = o.F(str),
				hidden = o.F(str, default=None, prompt=False),
			)
			Parent = o.T.extend(
				f'PromptSchemaParent_{root_name}',
				events    = o.F(list[Child]),
				show_time = o.F(str, default=None, prompt=False),
			)

			full      = Parent.to_json_schema()
			generated = Parent.to_prompt_schema()
			child_id  = Child.__proto__

			assert 'show_time' in full['properties']
			assert 'show_time' not in generated['properties']
			assert 'show_time' not in generated.get('required', [])
			assert 'hidden' in full['$defs'][child_id]['properties']
			assert 'hidden' not in generated['$defs'][child_id]['properties']
			assert 'seen' in generated['$defs'][child_id]['properties']
			assert Parent.to_json_schema() == full
			assert "'show_time'" not in Parent.to_prompt()
			assert "'hidden'" not in Parent.to_prompt()
			assert "'seen'" in Parent.to_prompt()

			parent = Parent(events=[Child(seen='visible')])
			assert parent.show_time is None
			parent.show_time = '2026-10-30T12:00:00+00:00'
			assert parent.show_time == '2026-10-30T12:00:00+00:00'
		finally:
			cls._restore_runtime(state)

	# Preserve optionality for defaults, nullable unions, and required unions.
	# ----------------------------------------------------------------------
	@classmethod
	def test_schema_optional_fields_and_unions(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Example = o.T.extend(
				f'JsonSchemaOptionality_{root_name}',
				required         = o.F(str),
				defaulted        = o.F(str, default='ready'),
				default_null     = o.F(str, default=None),
			)

			schema     = Example.to_json_schema()
			properties = schema['properties']

			assert schema['required'] == ['required']
			assert properties['required'] == { 'type' : 'string' }
			assert properties['defaulted'] == { 'type' : 'string' }
			assert properties['default_null'] == { 'type' : ['string', 'null'] }
			assert o.JsonSchema._get_annotation_schema(str | int, {}, ()) == {
				'anyOf' : [{ 'type' : 'integer' }, { 'type' : 'string' }]
			}
			assert o.JsonSchema._get_annotation_schema(str | None, {}, ()) == {
				'anyOf' : [{ 'type' : 'null' }, { 'type' : 'string' }]
			}
		finally:
			cls._restore_runtime(state)

	# Keep shared child definitions reusable and preserve unsupported-key errors.
	# ----------------------------------------------------------------------
	@classmethod
	def test_schema_repeated_children_and_dict_key_errors(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Child = o.T.extend(f'JsonSchemaSharedChild_{root_name}', value=str)
			Pair = o.T.extend(
				f'JsonSchemaSharedPair_{root_name}',
				left  = o.F(Child),
				right = o.F(Child),
			)
			schema = Pair.to_json_schema()
			child_ref = { '$ref' : f'#/$defs/{Child.__proto__}' }

			assert schema['properties']['left'] == child_ref
			assert schema['properties']['right'] == child_ref
			assert len(schema['$defs']) == 1
			assert schema['required'] == ['left', 'right']

			Invalid = o.T.extend(f'JsonSchemaInvalidKeys_{root_name}', dict[int, str])
			raised = False

			try:
				Invalid.to_json_schema()
			except TypeError as error:
				raised = 'JSON schema requires string dict keys' in str(error)

			assert raised
		finally:
			cls._restore_runtime(state)

	# Compare representative schemas directly with the archived implementation.
	# ----------------------------------------------------------------------
	@classmethod
	def test_schema_matches_preserved_implementation(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			path      = os.path.join(os.path.dirname(__file__), '..', '_json_schema.py')
			legacy    = runpy.run_path(path)['JsonSchema']

			Child = o.T.extend(
				f'JsonSchemaLegacyChild_{root_name}',
				name     = o.F(str),
				nickname = o.F(str, default=None),
			)
			Parent = o.T.extend(
				f'JsonSchemaLegacyParent_{root_name}',
				first        = o.F(Child),
				second       = o.F(Child, default=None),
				many         = o.F(list[Child]),
				by_name      = o.F(dict[str, Child]),
				with_default = o.F(str, default='ready'),
			)

			for target in (o.Int, o.Str, o.Null, Child, Parent):
				assert target.to_json_schema() == legacy.build(target)

			assert (
				o.JsonSchema._get_annotation_schema(str | int | None, {}, ())
				== legacy._get_annotation_schema(str | int | None, {}, ())
			)
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestJsonSchema.run()
