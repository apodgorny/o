# ==============================================================================
# TEST ONTOLOGY FORKS
# ==============================================================================
# Verify independent, persistent worlds behind the Almasi library fork API.
# ==============================================================================

import os
import subprocess
import sys
import tempfile
import time

from types import SimpleNamespace
from unittest.mock import patch

import o


class TestFork(o.Tester):

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Selecting a name must be idempotent and leave the filesystem untouched.
	# ----------------------------------------------------------------------
	@classmethod
	def test_fork_is_lazy_and_idempotent(cls):
		with tempfile.TemporaryDirectory(prefix='o_fork_') as directory:
			app  = SimpleNamespace(__lib_path__=directory)
			name = f'lazy_{time.time_ns()}'

			with patch.object(type(o), '__app__', app):
				world = o.fork(name)

				assert world is o.fork(name)
				assert world is o[name]
				assert world is world.fork(name)
				assert world.start.__self__ is world.services.Ontology
				assert not os.path.exists(os.path.join(directory, 'ontology'))

	# Keep LMDB, service instances, type classes and configuration independent.
	# ----------------------------------------------------------------------
	@classmethod
	def test_stores_and_types_are_isolated(cls):
		with tempfile.TemporaryDirectory(prefix='o_fork_') as directory:
			app     = SimpleNamespace(__lib_path__=directory)
			alice   = o.fork(f'alice_{time.time_ns()}')
			bob     = o.fork(f'bob_{time.time_ns()}')
			default = o.services.Memory.path

			with patch.object(type(o), '__app__', app):
				try:
					alice.start(tree_mode=True)
					bob.start(tree_mode=False)

					assert alice.services.Memory.path == os.path.realpath(os.path.join(directory, 'ontology', alice.__fork_name__))
					assert bob.services.Memory.path == os.path.realpath(os.path.join(directory, 'ontology', bob.__fork_name__))
					assert alice.services.Memory is not bob.services.Memory
					assert alice.T is not bob.T
					assert alice.V is not bob.V
					assert alice.TREE_MODE is True
					assert bob.TREE_MODE is False
					assert o.services.Memory.path == default

					alice.services.Memory.set('test/owner', 'alice')
					bob.services.Memory.set('test/owner', 'bob')

					assert alice.services.Memory.get('test/owner') == 'alice'
					assert bob.services.Memory.get('test/owner') == 'bob'

					OnlyAlice = alice.T.extend('OnlyAlice')
					assert alice.T.OnlyAlice is OnlyAlice
					assert not hasattr(bob.T, 'OnlyAlice')

					alice.start()
					assert alice.services.Memory.get('test/owner') == 'alice'
				finally:
					for world in (alice, bob):
						if 'env' in world.services.Memory.__dict__:
							world.services.Memory.env.close()

	# Data saved in one process must remain available after a fresh import.
	# ----------------------------------------------------------------------
	@classmethod
	def test_persists_across_processes(cls):
		with tempfile.TemporaryDirectory(prefix='o_fork_') as directory:
			source = '''
import sys
from types import SimpleNamespace
import o

type(o).__app__ = SimpleNamespace(__lib_path__=sys.argv[1])
world = o.fork('persisted')
world.start()

if sys.argv[2] == 'write':
	world.services.Memory.set('test/value', 123)
else:
	assert world.services.Memory.get('test/value') == 123

world.services.Memory.env.close()
'''
			environment = dict(os.environ)
			environment['PYTHONPATH'] = os.pathsep.join((
				os.path.dirname(o.__lib_file__),
				os.path.join(os.path.dirname(os.path.dirname(o.__lib_file__)), 'almasi'),
			))

			for mode in ('write', 'read'):
				result = subprocess.run(
					[sys.executable, '-c', source, directory, mode],
					env            = environment,
					capture_output = True,
					text           = True,
					timeout        = 30,
				)
				assert result.returncode == 0, result.stdout + result.stderr


if __name__ == '__main__':
	TestFork.run()
