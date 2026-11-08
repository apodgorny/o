# ==============================================================================
# TEST AUTH SERVICE
# ==============================================================================
# Verify persistent tree-only permissions, overrides, and isolation.
# ==============================================================================

import o


class TestAuth(o.Tester):

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Reject authorization calls outside tree mode.
	# ----------------------------------------------------------------------
	@classmethod
	def test_requires_tree_mode(cls):
		old_mode    = o.TREE_MODE
		o.TREE_MODE = False

		try:
			for operation in (
				lambda: o.services.Auth.set(o.V, 'alice', 'r'),
				lambda: o.services.Auth.can('alice', o.V, 'r'),
				lambda: o.V.__auth__,
			):
				try:
					operation()
					assert False
				except RuntimeError as error:
					assert 'tree mode' in str(error)
		finally:
			o.TREE_MODE = old_mode

	# Apply the nearest complete rule, including an explicit denial.
	# ----------------------------------------------------------------------
	@classmethod
	def test_inherited_permissions(cls):
		state       = cls._patch_runtime()
		old_mode    = o.TREE_MODE
		o.TREE_MODE = True

		try:
			Node   = o.T.extend('AuthNode', child=o.F(o.T, default=None))
			root   = Node()
			middle = Node()
			leaf   = Node()
			other  = o.T()

			root.child   = middle
			middle.child = leaf

			auth = o.services.Auth
			assert auth.can('alice', leaf, 'r') is False

			auth.set(root, 'alice', 'rw')
			assert auth.can('alice', leaf, 'r') is True
			assert auth.can('alice', leaf, 'w') is True
			assert auth.can('bob', leaf, 'r') is False
			assert auth.can('alice', other, 'r') is False

			auth.set(middle, 'alice', 'w')
			assert auth.can('alice', leaf, 'r') is False
			assert auth.can('alice', leaf, 'w') is True

			auth.set(leaf, 'alice', '')
			assert auth.can('alice', leaf, 'w') is False
			assert auth.can('alice', middle, 'w') is True

			assert o.V.__auth__[leaf.id]['name:alice'] == ''

			auth.set(leaf, 'alice', None)
			assert auth.can('alice', leaf, 'w') is True
			assert leaf.id not in o.V.__auth__

			auth.set(middle, 'alice', None)
			assert auth.can('alice', leaf, 'r') is True
		finally:
			o.TREE_MODE = old_mode
			cls._restore_runtime(state)

	# Track O client identities by stable ID, not object references.
	# ----------------------------------------------------------------------
	@classmethod
	def test_client_identity_and_validation(cls):
		state       = cls._patch_runtime()
		old_mode    = o.TREE_MODE
		o.TREE_MODE = True

		try:
			auth   = o.services.Auth
			client = o.T()
			node   = o.T()

			auth.set(node, client, 'r')
			assert auth.can(client, node, 'r') is True
			assert auth.can(str(client.id), node, 'r') is False

			for invalid in ('x', 'rr', 'rwq', 1):
				try:
					auth.set(node, client, invalid)
					assert False
				except ValueError:
					assert auth.can(client, node, 'r') is True
		finally:
			o.TREE_MODE = old_mode
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestAuth.run()
