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

	# Open storage, initialize dependent services, then load ontology classes.
	# ----------------------------------------------------------------------
	def start(self, path: str | None = None):
		if path is None:
			path = os.path.join(os.path.dirname(inspect.currentframe().f_back.f_globals['__file__']), 'ontology')

		o.DATA_DIR = path

		o.services.Cache.initialize()
		o.services.Memory.initialize()
		o.services.Id.initialize()
		o.services.Route.initialize()
		o.services.Garbage.initialize()

		for item in o:
			if not item.is_directory():
				item.load()

		o.services.Entity.ensure_value()
