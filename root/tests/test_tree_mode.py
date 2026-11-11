# ==============================================================================
# TEST TREE MODE
# ==============================================================================
# Verify persistent tree constraints and startup mode compatibility.
# ==============================================================================

import os
import subprocess
import sys
import tempfile

import o


class TestTreeMode(o.Tester):
	RUNTIME_PREFIX = 'o_tree_mode_'

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Prevent cycles, multiple owners, and attaching the root.
	# ----------------------------------------------------------------------
	@classmethod
	def test_tree_rejects_cycles_and_second_parents(cls):
		state    = cls._patch_runtime()
		old_mode = o.TREE_MODE
		o.TREE_MODE = True

		try:
			Node = o.T.extend('TreeModeNode', child=o.F(o.T, default=None))
			a    = Node()
			b    = Node()
			c    = Node()

			a.child = b
			b.child = c

			try:
				c.child = a
				assert False
			except ValueError as error:
				assert 'Cycle' in str(error)

			try:
				o.List([b])
				assert False
			except ValueError as error:
				assert 'parent' in str(error)

			assert a.child is b
			assert b.child is c

			del a.child
			root = o.List([b])

			assert root[0] is b

			try:
				root.append(o.V)
				assert False
			except ValueError as error:
				assert 'root' in str(error)
		finally:
			o.TREE_MODE = old_mode
			cls._restore_runtime(state)

	# Preserve links through list reordering and release removed children.
	# ----------------------------------------------------------------------
	@classmethod
	def test_tree_list_rebuild_and_reparent(cls):
		state    = cls._patch_runtime()
		old_mode = o.TREE_MODE
		o.TREE_MODE = True

		try:
			a     = o.T()
			b     = o.T()
			items = o.List([a, b])

			items.reverse()
			assert list(items) == [b, a]

			try:
				items.append(a)
				assert False
			except ValueError as error:
				assert 'parent' in str(error)

			try:
				items.append(items)
				assert False
			except ValueError as error:
				assert 'Cycle' in str(error)

			items.clear()
			assert len(items) == 0

			other = o.List([a, b])
			assert list(other) == [a, b]
		finally:
			o.TREE_MODE = old_mode
			cls._restore_runtime(state)

	# Dictionary keys and values are both holding edges.
	# ----------------------------------------------------------------------
	@classmethod
	def test_tree_dict_keys_values_and_clear(cls):
		state    = cls._patch_runtime()
		old_mode = o.TREE_MODE
		o.TREE_MODE = True

		try:
			key   = o.T()
			value = o.T()
			items = o.Dict({key: value})
			other = o.List([])

			try:
				other.append(key)
				assert False
			except ValueError as error:
				assert 'parent' in str(error)

			try:
				other.append(value)
				assert False
			except ValueError as error:
				assert 'parent' in str(error)

			items.clear()
			other.append(key)
			other.append(value)

			assert list(other) == [key, value]
		finally:
			o.TREE_MODE = old_mode
			cls._restore_runtime(state)

	# Validate single-edge value replacement without prechecking it twice.
	# ----------------------------------------------------------------------
	@classmethod
	def test_tree_dict_replaces_existing_value(cls):
		state    = cls._patch_runtime()
		old_mode = o.TREE_MODE
		o.TREE_MODE = True

		try:
			key       = o.T()
			old_value = o.T()
			new_value = o.T()
			foreign   = o.T()
			items     = o.Dict({key: old_value})
			other     = o.List([foreign])

			items[key] = new_value
			assert items[key] is new_value

			try:
				items[key] = foreign
				assert False
			except ValueError as error:
				assert 'parent' in str(error)

			assert items[key] is new_value
			o.List([old_value])
		finally:
			o.TREE_MODE = old_mode
			cls._restore_runtime(state)

	# Persist the mode across processes and reject conflicting restarts.
	# ----------------------------------------------------------------------
	@classmethod
	def test_startup_mode_is_permanent(cls):
		with tempfile.TemporaryDirectory() as path:
			source = '''
import sys
from types import SimpleNamespace
import o

type(o).__app__ = SimpleNamespace(__lib_path__=sys.argv[1])
mode = sys.argv[2]
value = None if mode == 'load' else mode == 'tree'
o.start(tree_mode=value)
assert o.TREE_MODE is True
'''
			environment = dict(os.environ)
			environment['PYTHONPATH'] = os.pathsep.join((
				os.path.dirname(o.__lib_file__),
				os.path.join(os.path.dirname(os.path.dirname(o.__lib_file__)), 'almasi'),
			))

			for mode in ('tree', 'load'):
				result = subprocess.run(
					[sys.executable, '-c', source, path, mode],
					env            = environment,
					capture_output = True,
					text           = True,
					timeout        = 30,
				)
				assert result.returncode == 0, result.stdout + result.stderr

			result = subprocess.run(
				[sys.executable, '-c', source, path, 'graph'],
				env            = environment,
				capture_output = True,
				text           = True,
				timeout        = 30,
			)
			assert result.returncode != 0
			assert 'Tree mode does not match' in result.stderr


if __name__ == '__main__':
	TestTreeMode.run()
