import os

import o


class TestJsonPrompt(o.Tester):
	RUNTIME_PREFIX = 'o_json_prompt_'

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
				'    \'description\' : str,         # Semantic search description of the situation this node represents\n'
				'    \'age\'         : int | null,  # Age\n'
				'    \'name\'        : str          # Human readable full name\n'
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
				'    \'description\' : str,     # Semantic search description of the situation this node represents\n'
				'    \'child\'       : {        # Nested child\n'
				'        \'description\' : str, # Semantic search description of the situation this node represents\n'
				'        \'name\'        : str  # Child name\n'
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
				'    \'description\' : str,  # Semantic search description of the situation this node represents\n'
				'    \'scores\'      : {     # Score by subject\n'
				'        \'key\' : int       # str key\n'
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
				'    \'description\' : str,          # Semantic search description of the situation this node represents\n'
				'    \'contacts\'    : [             # Previous contacts\n'
				'        {\n'
				'            \'description\' : str,  # Semantic search description of the situation this node represents\n'
				'            \'email\'       : str   # Primary email\n'
				'        }\n'
				'    ]\n'
				'}'
			)
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestJsonPrompt.run()
