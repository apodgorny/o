# ==============================================================================
# TEST AUTH SERVICE
# ==============================================================================
# Verify tree-only permissions, integer identities, and inherited overrides.
# ==============================================================================

import tempfile
from types import SimpleNamespace

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
				lambda: o.services.Auth.set(o.V, 7, 'r'),
				lambda: o.services.Auth.can(7, o.V, 'r'),
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
		state    = cls._patch_runtime()
		old_mode = o.TREE_MODE

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
			assert auth.can(7, leaf, 'r') is False

			auth.set(root, 7, 'rw')
			assert auth.can(7, leaf, 'r') is True
			assert auth.can(7, leaf, 'w') is True
			assert auth.can(8, leaf, 'r') is False
			assert auth.can(7, other, 'r') is False

			auth.set(middle, 7, 'w')
			assert auth.can(7, leaf, 'r') is False
			assert auth.can(7, leaf, 'w') is True

			auth.set(leaf, 7, '')
			assert auth.can(7, leaf, 'w') is False
			assert auth.can(7, middle, 'w') is True

			assert o.V.__auth__[leaf.id][7] == ''

			auth.set(leaf, 7, None)
			assert auth.can(7, leaf, 'w') is True
			assert leaf.id not in o.V.__auth__

			auth.set(middle, 7, None)
			assert auth.can(7, leaf, 'r') is True
		finally:
			o.TREE_MODE = old_mode
			cls._restore_runtime(state)

	# Accept only integer client IDs and preserve rules after invalid calls.
	# ----------------------------------------------------------------------
	@classmethod
	def test_client_identity_and_validation(cls):
		state    = cls._patch_runtime()
		old_mode = o.TREE_MODE

		o.TREE_MODE = True

		try:
			auth = o.services.Auth
			node = o.T()

			auth.set(node, 7, 'r')
			assert auth.can(7, node, 'r') is True
			assert auth.can(8, node, 'r') is False
			assert o.V.__auth__[node.id][7] == 'r'

			for invalid in ('7', True, 7.0, o.T()):
				try:
					auth.set(node, invalid, 'w')
					assert False
				except TypeError:
					assert auth.can(7, node, 'r') is True

				try:
					auth.can(invalid, node, 'r')
					assert False
				except TypeError:
					assert auth.can(7, node, 'r') is True

			for invalid in ('x', 'rr', 'rwq', 1):
				try:
					auth.set(node, 7, invalid)
					assert False
				except ValueError:
					assert auth.can(7, node, 'r') is True
		finally:
			o.TREE_MODE = old_mode
			cls._restore_runtime(state)


if __name__ == '__main__':
	with tempfile.TemporaryDirectory(prefix='o_auth_test_') as directory:
		type(o).__app__ = SimpleNamespace(__lib_path__=directory)
		o.start(tree_mode=True)

		try:
			TestAuth.run()
		finally:
			o.services.Memory.env.close()
