import os

import o


class Registry(o.Service):

	def initialize(self):
		self.dir = os.path.join(o.core_path, o.DATA_DIR, '__registry__')

		if not os.path.exists(self.dir):
			os.makedirs(self.dir)

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Get symlink path by entity id
	# ----------------------------------------------------------------------
	def _get_link_path(self, id):
		return os.path.join(self.dir, str(id))

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Add registry symlink
	# ----------------------------------------------------------------------
	def add(self, id, dir_path):
		link_path = self._get_link_path(id)

		if os.path.lexists(link_path):
			os.remove(link_path)

		os.symlink(dir_path, link_path)

	# Remove registry symlink
	# ----------------------------------------------------------------------
	def remove(self, id):
		link_path = self._get_link_path(id)

		if os.path.lexists(link_path):
			os.remove(link_path)

	# Resolve entity directory by id
	# ----------------------------------------------------------------------
	def get(self, id):
		link_path = self._get_link_path(id)
		dir_path  = o.undefined

		if os.path.lexists(link_path):
			dir_path = os.path.realpath(link_path)

		if dir_path is not o.undefined and not os.path.exists(dir_path):
			dir_path = o.undefined

		return dir_path
