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
	# PRIVATE METHODS
	# ======================================================================

	# Reinitialize services that have already completed startup.
	# ----------------------------------------------------------------------
	def _initialize(self, service, **kwargs):
		if service.__dict__.get('_is_initialized'):
			type(service).initialize(service, **kwargs)
		else:
			service.initialize(**kwargs)

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

		is_reconnecting = 'env' in o.services.Memory.__dict__

		if not is_reconnecting:
			self._initialize(o.services.Cache)

		self._initialize(o.services.Memory, sync=sync)

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

		self._initialize(o.services.Id)
		self._initialize(o.services.Route)
		self._initialize(o.services.Garbage)

		if is_reconnecting:
			o.services.Cache.invalidate_all()

		for item in o:
			if not item.is_directory():
				item.load()

		o.services.Entity.ensure_value()
