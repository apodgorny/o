import o


class Tree(o.Module):

	# Create tree projection
	# ----------------------------------------------------------------------
	def __init__(self, node):
		self.node        = node
		self.show_index  = False
		self.indexes     = {}
		self.render_text = None

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Render one node
	# ----------------------------------------------------------------------
	def _render_node(self, node, indexes, prefix, pointer, is_last):
		self._remember_index(node, indexes)
		text     = self._render_text(node)
		lines    = []
		children = self._children(node)

		if self.show_index:
			text = f'({self._index_text(indexes)}) {text}'

		lines.append(f'{prefix}{pointer}{text}')

		for child_index, child in enumerate(children):
			child_is_last = child_index == len(children) - 1
			child_pointer = '└── ' if child_is_last else '├── '
			child_prefix  = self._child_prefix(prefix, pointer, is_last)
			child_indexes = indexes + (child_index + 1,)
			child_lines   = self._render_node(
				child,
				child_indexes,
				child_prefix,
				child_pointer,
				child_is_last,
			)
			lines.extend(child_lines)

		return lines

	# Remember node index
	# ----------------------------------------------------------------------
	def _remember_index(self, node, indexes):
		self.indexes[self._node_key(node)] = self._index_text(indexes)

	# Resolve node index key
	# ----------------------------------------------------------------------
	def _node_key(self, node):
		key = id(node)

		if isinstance(node, o.T):
			key = ('o.T', node.id)

		return key

	# Render node text
	# ----------------------------------------------------------------------
	def _render_text(self, node):
		node_index = self.get_index(node)
		text = str(node)

		if self.render_text is not None:
			text = self.render_text(node, node_index)

		return text

	# Read render children
	# ----------------------------------------------------------------------
	def _children(self, node):
		children      = []
		node_children = self._node_children(node)

		if node_children is not None:
			for child in node_children:
				children.append(child)
		elif isinstance(node, o.T):
			for _, _, child in node.__dependants__():
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
			pass

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
		return '.'.join(str(index) for index in indexes)
	
	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================
	
	# Render tree
	# ----------------------------------------------------------------------
	def render(self, show_index=False, render_text=None):
		self.show_index  = show_index
		self.render_text = render_text
		self.indexes     = {}
		
		lines = self._render_node(
			self.node,
			(1,),
			'',
			'',
			True,
		)

		return '\n'.join(lines)

	# Read remembered node index
	# ----------------------------------------------------------------------
	def get_index(self, node):
		return self.indexes.get(self._node_key(node))
