import o


entry_proto = 'o.T.LabTreeEntry'

Entry = o.get(entry_proto) if o.exists(entry_proto) else o.T.extend(
	'LabTreeEntry',
	title=str,
	children=o.F(list, default=None),
)

node = o.T({
	'title': 'lab tree',
	'branch': {
		'title': 'dict branch',
		'items': [
			'first leaf',
			'second leaf',
		],
	},
	'entry': Entry(
		title='o.T branch',
		children=[
			Entry(title='nested o.T leaf'),
			{'title': 'dict inside o.T'},
		],
	),
	'queue': [
		'list leaf',
		{'title': 'dict inside list'},
		Entry(title='o.T inside list'),
	],
})

some_one_node = node['entry']


def render_node(node, node_index):
	text = node.title if hasattr(node, 'title') else node.__class__.__name__

	if isinstance(node, o.Dict):
		text = node['title'] if 'title' in node else 'dict'
	elif isinstance(node, o.List):
		text = 'list'
	elif node.__class__.__is_atom__:
		text = repr(node.__value__)

	if isinstance(node, o.T) and node.id == some_one_node.id:
		text = f'{text}  # <== expand this node ({node_index})'

	return text


tree         = o.Tree(node)
tree_text    = tree.render(True, render_node)
expand_index = tree.get_index(some_one_node)

print(tree_text)
print(expand_index)
