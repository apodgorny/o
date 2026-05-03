import os, sys

dev_root    = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
almasi_root = os.path.join(dev_root, 'almasi')

if os.path.isdir(almasi_root) and almasi_root not in sys.path:
	sys.path.insert(0, almasi_root)

import o
o.tester.run()
