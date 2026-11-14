# ==============================================================================
# ONTOLOGY SERVICE
# ==============================================================================
# Start persistence and load ontology classes after the library has been created.
# ==============================================================================

import os

import o


class Ontology(o.Service):

	_multiprocess_enabled = False

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Require a single safe directory name for each ontology.
	# ----------------------------------------------------------------------
	def _is_valid_fork_name(self, name):
		return (
			isinstance(name, str)
			and name not in ('', '.', '..')
			and os.path.basename(name) == name
			and '\\' not in name
		)

	# Reinitialize services that have already completed startup.
	# ----------------------------------------------------------------------
	def _initialize_service(self, service, **kwargs):
		if service.__dict__.get('_is_initialized'):
			type(service).initialize(service, **kwargs)
		else:
			service.initialize(**kwargs)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Allocate an isolated runtime namespace without opening its LMDB.
	# ----------------------------------------------------------------------
	def fork(self, name):
		if not self._is_valid_fork_name(name):
			raise ValueError(f'Invalid ontology name: {name}')

		library = o.__dict__.get('__fork_source__', o)

		try:
			result = library[name]
		except KeyError:
			result       = type(library).fork(library, name)
			result.start = result.services.Ontology.start
			result.fork  = result.services.Ontology.fork

		return result

	# Open or create this ontology under the application-owned ontology folder.
	# sync=False favors throughput; multiprocess=True enables IPC.
	# ----------------------------------------------------------------------
	def start(self, sync: bool = False, tree_mode: bool | None = None, multiprocess: bool = False):
		app = o.__app__
		if app is None:
			raise RuntimeError('O requires an active Almasi application before start()')

		name       = o.__dict__.get('__fork_name__', 'default')
		o.DATA_DIR = os.path.join(app.__lib_path__, 'ontology', name)

		if tree_mode is not None and type(tree_mode) is not bool:
			raise TypeError('tree_mode must be bool or None')

		if type(multiprocess) is not bool:
			raise TypeError('multiprocess must be bool')

		is_reconnecting = 'env' in o.services.Memory.__dict__

		if not is_reconnecting:
			self._initialize_service(o.services.Cache)
			self._initialize_service(o.services.Sync)

		self._initialize_service(o.services.Memory, sync=sync)

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
				o.services.Memory.set('system/tree_mode', saved_mode, 0)
		else:
			raise ValueError('Tree mode does not match the existing ontology')

		o.TREE_MODE = saved_mode

		self._initialize_service(o.services.Id)
		self._initialize_service(o.services.Route)
		self._initialize_service(o.services.Garbage)

		if is_reconnecting:
			o.services.Cache.invalidate_all()

		# Test carriers change the shared Tester class and stay outside fork startup.
		# ----------------------------------------------------------------------
		for item in o:
			if not item.is_directory() and item.get_name() not in ('test.py', 'tester.py'):
				item.load()

		o.services.Entity.ensure_value()
		o.__cached_names__.add('V')

		if multiprocess and not self._multiprocess_enabled:
			self._initialize_service(
				o.services.Transport,
				path = o.services.Memory.path,
				sync = o.services.Sync,
			)
		elif not multiprocess and self._multiprocess_enabled:
			o.services.Transport.close()

		self._multiprocess_enabled = multiprocess
