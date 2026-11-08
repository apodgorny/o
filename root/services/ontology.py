# ==============================================================================
# ONTOLOGY SERVICE
# ==============================================================================
# Start persistence and load ontology classes after the library has been created.
# ==============================================================================

import inspect
import os

import o


class Ontology(o.Service):

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Start once; path defaults to the caller's ontology/ directory.
	# sync=False favors fast commits, but a crash may lose data or corrupt LMDB.
	# sync=True flushes each commit to disk for stronger durability.
	# ----------------------------------------------------------------------
	def start(self, path: str | None = None, sync: bool = False, tree_mode: bool | None = None):
		if path is None:
			path = os.path.join(os.path.dirname(inspect.currentframe().f_back.f_globals['__file__']), 'ontology')

		o.DATA_DIR = path

		if tree_mode is not None and type(tree_mode) is not bool:
			raise TypeError('tree_mode must be bool or None')

		o.services.Cache.initialize()
		o.services.Memory.initialize(sync=sync)

		with o.services.Memory.read() as memory:
			has_mode   = memory.has('system/tree_mode')
			saved_mode = memory.get('system/tree_mode') if has_mode else None
			has_data   = next(memory.keys(), None) is not None

		if not has_mode:
			saved_mode = False if has_data or tree_mode is None else tree_mode

		if type(saved_mode) is not bool:
			raise ValueError('Invalid stored tree mode')

		if tree_mode is None or tree_mode == saved_mode:
			if not has_mode:
				o.services.Memory.set('system/tree_mode', saved_mode)
		else:
			raise ValueError('Tree mode does not match the existing ontology')

		o.TREE_MODE = saved_mode

		o.services.Id.initialize()
		o.services.Route.initialize()
		o.services.Garbage.initialize()

		for item in o:
			if not item.is_directory():
				item.load()

		o.services.Entity.ensure_value()
