import os
import struct

import o


class Instances(o.Module):

	DIR  = '__instances__'
	FILE = '__index__'
	WORD = struct.Struct('<Q')

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Constructor
	# ----------------------------------------------------------------------
	def __init__(self, parent_path):
		self.parent_path = parent_path
		self.path        = os.path.join(parent_path, self.DIR)
		self.count       = 0
		self.order       = []
		index_path       = self._get_index_path()

		os.makedirs(self.path, exist_ok=True)

		if not os.path.exists(index_path):
			self.set(self.count, self.order)

		with open(index_path, 'rb') as file:
			content = file.read()

		if content:
			self.count = self.WORD.unpack(content[:self.WORD.size])[0]

			if len(content) > self.WORD.size:
				num_versions = (len(content) - self.WORD.size) // self.WORD.size
				order_word   = struct.Struct(f'<{num_versions}Q')
				self.order   = list(order_word.unpack(content[self.WORD.size:]))

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Get __index__ path
	# ----------------------------------------------------------------------
	def _get_index_path(self):
		return os.path.join(self.path, self.FILE)

	# Get instance path
	# ----------------------------------------------------------------------
	def _get_instance_path(self, version):
		return os.path.join(self.path, f'_{version}')

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Set sequence state
	# ----------------------------------------------------------------------
	def set(self, count, order):
		self.count = count
		self.order = order

		index_path = self._get_index_path()
		content    = self.WORD.pack(count)

		if order:
			order_word = struct.Struct(f'<{len(order)}Q')
			content   += order_word.pack(*order)

		with open(index_path, 'wb') as file:
			file.write(content)

	# Create next instance room
	# ----------------------------------------------------------------------
	def create(self, annotation):
		version = self.count
		path    = self._get_instance_path(version)

		os.makedirs(path, exist_ok=True)

		self.count += 1
		self.order.append(version)
		self.set(self.count, self.order)

		return o.disk.Instance(path, annotation)

	# Remove instance from live order
	# ----------------------------------------------------------------------
	def remove(self, version):
		new_order = []

		for item in self.order:
			if item != version:
				new_order.append(item)

		self.set(self.count, new_order)

	# Get instance room by underscored version name
	# ----------------------------------------------------------------------
	def get(self, version):
		instance = None

		if o.is_instance_version(version):
			path = self._get_instance_path(int(version[1:]))

			if os.path.isdir(path):
				instance = o.disk.Instance(path, o.undefined)

		return instance
