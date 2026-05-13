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
			tree_dict = do.tests.fixtures.Tree1
			root_spec = tree_dict['instance']
			tree      = o.T.deserialize(tree_dict)

			assert isinstance(tree, o.T)
			assert tree.__class__.__proto__ == root_spec['__class__']
			assert tree.civilization_browser.overview.description == root_spec['civilization_browser']['overview']['description']
			assert tree.resonance_lab.experiments[1].description == root_spec['resonance_lab']['experiments']['__items__'][1]['description']
			assert tree.vector_architecture.proto.description == root_spec['vector_architecture']['proto']['description']
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_round_trip_tree_fixture_spec(cls):
		state = cls._patch_runtime()

		try:
			tree  = o.T.deserialize(do.tests.fixtures.Tree1)
			spec  = tree.serialize()
			tree2 = o.T.deserialize(spec)

			assert tree2.civilization_browser.overview.description == tree.civilization_browser.overview.description
			assert tree2.resonance_lab.experiments[1].description == tree.resonance_lab.experiments[1].description
			assert tree2.vector_architecture.proto.description == tree.vector_architecture.proto.description
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestSerializer.run()
