import os
import sys
import tempfile

from types import SimpleNamespace

dev_root    = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
almasi_root = os.path.join(dev_root, 'almasi')

if os.path.isdir(almasi_root) and almasi_root not in sys.path:
	sys.path.insert(0, almasi_root)

import o

with tempfile.TemporaryDirectory(prefix='o_test_') as directory:
	type(o).__app__ = SimpleNamespace(__lib_path__=directory)
	o.start()

	import tester
	o.tester.run()
