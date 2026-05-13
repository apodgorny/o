import o


class Tree(o.Module):

	# Create tree projection
	# ----------------------------------------------------------------------
	def __init__(self, node):
		self.node = node

	# Render tree
	# ----------------------------------------------------------------------
	def render(self, node_render, index=True):
		lines = self._render_node(
			self.node,
			node_render,
			index,
			(1,),
			'',
			'',
			True,
		)
		text = '\n'.join(lines)

		return text

	# Render one node
	# ----------------------------------------------------------------------
	def _render_node(self, node, node_render, index, indexes, prefix, pointer, is_last):
		text     = node_render(node)
		lines    = []
		children = self._children(node)

		if index:
			text = f'({self._index_text(indexes)}) {text}'

		lines.append(f'{prefix}{pointer}{text}')

		for child_index, child in enumerate(children):
			child_is_last = child_index == len(children) - 1
			child_pointer = '└── ' if child_is_last else '├── '
			child_prefix  = self._child_prefix(prefix, pointer, is_last)
			child_indexes = indexes + (child_index + 1,)
			child_lines   = self._render_node(
				child,
				node_render,
				index,
				child_indexes,
				child_prefix,
				child_pointer,
				child_is_last,
			)
			lines.extend(child_lines)

		return lines

	# Read render children
	# ----------------------------------------------------------------------
	def _children(self, node):
		children      = []
		node_children = self._node_children(node)

		if node_children is not None:
			for child in node_children:
				children.append(child)
		elif isinstance(node, o.T):
			for name, child_path, child in node.__dependants__():
				if not child.__class__.__is_atom__:
					children.append(child)

		return children

	# Read named node children
	# ----------------------------------------------------------------------
	def _node_children(self, node):
		children = None

		try:
			children = node.children
		except AttributeError:
			children = None

		return children

	# Resolve child prefix
	# ----------------------------------------------------------------------
	def _child_prefix(self, prefix, pointer, is_last):
		child_prefix = prefix

		if pointer:
			if is_last:
				child_prefix += '    '
			else:
				child_prefix += '│   '

		return child_prefix

	# Resolve index text
	# ----------------------------------------------------------------------
	def _index_text(self, indexes):
		text = '.'.join(str(index) for index in indexes)

		return text
