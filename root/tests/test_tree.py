import o


class TestTree(o.Tester):
	RUNTIME_PREFIX = 'o_tree_'

	# ----------------------------------------------------------------------
	@classmethod
	def test_render_description_tree_with_indexes(cls):
		state = cls._patch_runtime()

		try:
			root_name = state['root'].split('/')[-1]
			Step = o.T.extend(
				f'TreeStep_{root_name}',
				children=o.F(list, default=None),
			)
			root = Step(
				description='Make homemade pizza from scratch.',
				children=[
					Step(
						description='Prepare pizza dough.',
						children=[
							Step(description='Mix flour, water, yeast, salt, and oil.'),
							Step(description='Knead dough until smooth.'),
						],
					),
					Step(description='Ferment the dough.'),
					Step(description='Prepare tomato sauce.'),
					Step(description='Bake the assembled pizza.'),
				],
			)
			text = root.to_tree().render(lambda node: node.description)

			assert text == '\n'.join((
				'(1) Make homemade pizza from scratch.',
				'├── (1.1) Prepare pizza dough.',
				'│   ├── (1.1.1) Mix flour, water, yeast, salt, and oil.',
				'│   └── (1.1.2) Knead dough until smooth.',
				'├── (1.2) Ferment the dough.',
				'├── (1.3) Prepare tomato sauce.',
				'└── (1.4) Bake the assembled pizza.',
			))
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_render_without_indexes(cls):
		state = cls._patch_runtime()

		try:
			root_name = state['root'].split('/')[-1]
			Node = o.T.extend(
				f'TreeNoIndexNode_{root_name}',
				children=o.F(list, default=None),
			)
			root = Node(
				description='Root',
				children=[
					Node(description='Left'),
					Node(description='Right'),
				],
			)
			text = root.to_tree().render(lambda node: node.description, index=False)

			assert text == '\n'.join((
				'Root',
				'├── Left',
				'└── Right',
			))
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestTree.run()
