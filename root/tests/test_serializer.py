import os

import do
import o


class TestSerializer(o.Tester):
	RUNTIME_PREFIX = 'o_serializer_'

	# ----------------------------------------------------------------------
	@classmethod
	def test_serialize_instance_collects_class_graph(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			User      = o.T.extend(
				f'SerializerUser_{root_name}',
				name=o.F(str, description='Human name'),
				age=o.F(int, description='Age')
			)
			user = User(name='Alexander', age=38)
			spec = user.serialize()

			assert spec == {
				'classes': {
					User.__proto__: {
						'name': {
							'type': 'o.T.Atom.Str',
							'description': 'Human name',
						},
						'age': {
							'type': 'o.T.Atom.Int',
							'description': 'Age',
						},
					},
					'o.T.Atom.Str': {},
					'o.T.Atom.Int': {},
				},
				'instance': {
					'__class__': User.__proto__,
					'name': {
						'__class__': 'o.T.Atom.Str',
						'__items__': 'Alexander',
					},
					'age': {
						'__class__': 'o.T.Atom.Int',
						'__items__': 38,
					},
				},
			}
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_deserialize_given_spec_creates_class_and_instance(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			proto     = f'o.T.SerializerFromSpec_{root_name}'
			spec      = {
				'classes': {
					proto: {
						'name': {
							'type': 'o.T.Atom.Str',
							'description': 'Field description',
						},
					},
					'o.T.Atom.Str': {},
				},
				'instance': {
					'__class__': proto,
					'name': 'Alexander',
				},
			}

			instance = o.T.deserialize(spec)
			Class    = o.get(proto)

			assert isinstance(instance, Class)
			assert Class._.name.description == 'Field description'
			assert instance.name == 'Alexander'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_nested_object_and_list_roundtrip(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Child     = o.T.extend(f'SerializerChild_{root_name}', name=str)
			Parent    = o.T.extend(f'SerializerParent_{root_name}', child=Child, tags=list[str])
			parent    = Parent(
				child=Child(name='Alex'),
				tags=['one', 'two'],
			)
			spec      = parent.serialize()
			copy      = o.T.deserialize(spec)

			assert spec['instance']['__class__'] == Parent.__proto__
			assert spec['instance']['child']['__class__'] == Child.__proto__
			assert spec['instance']['child']['name']['__items__'] == 'Alex'
			assert spec['instance']['tags'] == {
				'__class__': 'o.T.List',
				'__items__': ['one', 'two'],
			}
			assert isinstance(copy, Parent)
			assert isinstance(copy.child, Child)
			assert copy.child.name == 'Alex'
			assert list(copy.tags) == ['one', 'two']
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_serialize_and_deserialize_list_payload(cls):
		state = cls._patch_runtime()

		try:
			items = o.List(['a', 'b'])
			spec  = items.serialize()
			copy  = o.T.deserialize(spec)

			assert spec == {
				'classes': {
					'o.T.List': {},
				},
				'instance': {
					'__class__': 'o.T.List',
					'__items__': ['a', 'b'],
				},
			}
			assert isinstance(copy, o.List)
			assert list(copy) == ['a', 'b']
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_serialize_and_deserialize_dict_payload(cls):
		state = cls._patch_runtime()

		try:
			scores = o.Dict({'a': 1, 'b': 2})
			spec   = scores.serialize()
			copy   = o.T.deserialize(spec)

			assert spec == {
				'classes': {
					'o.T.Dict': {},
				},
				'instance': {
					'__class__': 'o.T.Dict',
					'__items__': {'a': 1, 'b': 2},
				},
			}
			assert isinstance(copy, o.Dict)
			assert dict(copy.items()) == {'a': 1, 'b': 2}
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_deserialize_tree_fixture(cls):
		state = cls._patch_runtime()

		try:
			tree_dict = do.tests.fixtures.tree_small
			root_spec = tree_dict['instance']
			tree      = o.T.deserialize(tree_dict)

			assert isinstance(tree, o.T)
			assert tree.__class__.__proto__ == root_spec['__class__']
			assert tree.description == root_spec['description']
			assert tree.food.a.description == root_spec['food']['a']['description']
			assert tree.machines.b.description == root_spec['machines']['b']['description']
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_round_trip_tree_fixture_spec(cls):
		state = cls._patch_runtime()

		try:
			tree  = o.T.deserialize(do.tests.fixtures.tree_small)
			spec  = tree.serialize()
			tree2 = o.T.deserialize(spec)

			assert tree2.description == tree.description
			assert tree2.food.a.description == tree.food.a.description
			assert tree2.machines.b.description == tree.machines.b.description
		finally:
			cls._restore_runtime(state)

	# Restore concrete subclasses in fields with typed collection annotations.
	# ----------------------------------------------------------------------
	@classmethod
	def test_polymorphic_collections_roundtrip(cls):
		state = cls._patch_runtime()
		try:
			root_name = os.path.basename(state['root'])
			Base = o.T.extend(f'SerializerBase_{root_name}', label=str)
			Derived = Base.extend('Derived', conclusion=str)
			Parent = o.T.extend(
				f'SerializerHolder_{root_name}',
				reactions=dict[str, Base],
				entries=list[Base],
			)
			child = Derived(label='seen', conclusion='learned')
			instance = Parent(reactions={'alex': child}, entries=[child])
			spec = instance.serialize()
			copy = o.T.deserialize(spec)

			assert spec['instance']['reactions']['__class__'] == 'o.T.Dict'
			assert spec['instance']['reactions']['__items__']['alex']['__class__'] == Derived.__proto__
			assert isinstance(copy.reactions['alex'], Derived)
			assert isinstance(copy.entries[0], Derived)
			assert copy.reactions['alex'].conclusion == 'learned'
			assert copy.entries[0].conclusion == 'learned'
		finally:
			cls._restore_runtime(state)

if __name__ == '__main__':
	TestSerializer.run()
