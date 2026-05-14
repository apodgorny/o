import os

import o


class TestCast(o.Tester):
	RUNTIME_PREFIX = 'o_cast_'

	# ----------------------------------------------------------------------
	@classmethod
	def test_object_field_casts_raw_dict_into_declared_class(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Child     = o.T.extend(f'CastObjectFieldChild_{root_name}', name=str)
			Parent    = o.T.extend(f'CastObjectFieldParent_{root_name}', child=Child)
			parent    = Parent(child={'name': 'alex'})

			assert isinstance(parent.child, Child)
			assert parent.child.name == 'alex'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_object_field_recasts_generic_dict_into_declared_class(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Child     = o.T.extend(f'CastGenericObjectFieldChild_{root_name}', name=str)
			Parent    = o.T.extend(f'CastGenericObjectFieldParent_{root_name}', child=Child)
			parent    = Parent(child=o.Dict({'name': 'alex'}))

			assert isinstance(parent.child, Child)
			assert parent.child.name == 'alex'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_object_field_casts_list_items_into_declared_class(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Child     = o.T.extend(f'CastListFieldChild_{root_name}', name=str)
			Parent    = o.T.extend(f'CastListFieldParent_{root_name}', children=o.F(list[Child]))
			parent    = Parent(children=[{'name': 'alex'}, {'name': 'bob'}])

			assert isinstance(parent.children[0], Child)
			assert parent.children[0].name == 'alex'
			assert isinstance(parent.children[1], Child)
			assert parent.children[1].name == 'bob'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_typed_list_recasts_generic_input_and_mutations(cls):
		state = cls._patch_runtime()

		try:
			root_name     = os.path.basename(state['root'])
			Child         = o.T.extend(f'CastTypedListChild_{root_name}', name=str)
			TypedChildren = o.T.extend(f'CastTypedList_{root_name}', list[Child])
			x             = TypedChildren(o.List([{'name': 'alex'}]))

			x.append({'name': 'bob'})
			x[0] = {'name': 'aria'}

			assert isinstance(x[0], Child)
			assert x[0].name == 'aria'
			assert isinstance(x[1], Child)
			assert x[1].name == 'bob'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_object_field_casts_typed_dict_keys_and_values(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Child     = o.T.extend(f'CastDictFieldChild_{root_name}', name=str)
			Parent    = o.T.extend(f'CastDictFieldParent_{root_name}', children=o.F(dict[str, Child]))
			parent    = Parent(children={1: {'name': 'alex'}, 2: {'name': 'bob'}})
			items     = dict(parent.children.items())

			assert '1' in items
			assert items['1'].name == 'alex'
			assert '2' in items
			assert items['2'].name == 'bob'
			assert isinstance(items['1'], Child)
			assert isinstance(items['2'], Child)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_typed_dict_recasts_generic_input_and_mutations(cls):
		state = cls._patch_runtime()

		try:
			root_name     = os.path.basename(state['root'])
			Child         = o.T.extend(f'CastTypedDictChild_{root_name}', name=str)
			TypedChildren = o.T.extend(f'CastTypedDict_{root_name}', dict[str, Child])
			x             = TypedChildren(o.Dict({1: {'name': 'alex'}}))

			x[2] = {'name': 'bob'}
			x.update({3: {'name': 'aria'}})

			items = dict(x.items())

			assert '1' in items
			assert items['1'].name == 'alex'
			assert '2' in items
			assert items['2'].name == 'bob'
			assert '3' in items
			assert items['3'].name == 'aria'
			assert isinstance(items['1'], Child)
			assert isinstance(items['2'], Child)
			assert isinstance(items['3'], Child)
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestCast.run()
