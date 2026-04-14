import os
import mmap
import struct

import o


class Registry(o.Service):

	FILE      = '__registry__'
	CAPACITY  = 1048576
	SLOT_SIZE = 256
	ID_SIZE   = 8
	PATH_SIZE = 248

	# ======================================================================
	# SERVICE METHODS
	# ======================================================================

	# Initialize Registry
	# ----------------------------------------------------------------------
	def initialize(self):
		self.path  = os.path.join(o.core_path, o.DATA_DIR, self.FILE)
		self.items = {}

		# Create fixed-size binary registry table
		# - - - - - - - - - - - - - - - - - - - - - - - 
		os.makedirs(os.path.dirname(self.path), exist_ok=True)

		if not os.path.exists(self.path):
			with open(self.path, 'wb') as file:
				file.write(b'\x00' * (self.CAPACITY * self.SLOT_SIZE))

		self._file = open(self.path, 'r+b')
		self._mmap = mmap.mmap(self._file.fileno(), 0)
		self._view = memoryview(self._mmap)

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Find registry slot
	# ----------------------------------------------------------------------
	def _find_slot(self, id, create=False):
		start_index = (id % self.CAPACITY)
		index       = start_index
		offset      = o.undefined

		for _ in range(self.CAPACITY):
			slot_offset = index * self.SLOT_SIZE
			slot_id     = struct.unpack('<Q', self._view[slot_offset : slot_offset + self.ID_SIZE])[0]

			if slot_id == id:
				offset = slot_offset
				break

			if slot_id == 0:
				if create:
					struct.pack_into('<Q', self._view, slot_offset, id)
					offset = slot_offset
				break

			index = (index + 1) % self.CAPACITY

		if offset is o.undefined and create:
			raise RuntimeError('Registry index is full')

		return offset

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Add registry entry
	# ----------------------------------------------------------------------
	def add(self, id, dir_path):
		offset     = self._find_slot(id, create=True)
		path_bytes = dir_path.encode('utf-8')

		if len(path_bytes) > self.PATH_SIZE:
			raise ValueError(f'Path too long for registry index: `{dir_path}`')

		self._view[offset + self.ID_SIZE : offset + self.SLOT_SIZE] = b'\x00' * self.PATH_SIZE
		self._view[offset + self.ID_SIZE : offset + self.ID_SIZE + len(path_bytes)] = path_bytes

		self.items[id] = dir_path

	# Remove registry entry
	# ----------------------------------------------------------------------
	def remove(self, id):
		offset = self._find_slot(id)

		if offset is not o.undefined:
			struct.pack_into('<Q', self._view, offset, 0)
			self._view[offset + self.ID_SIZE : offset + self.SLOT_SIZE] = b'\x00' * self.PATH_SIZE

		if id in self.items:
			del self.items[id]

	# Resolve entity directory by id
	# ----------------------------------------------------------------------
	def get(self, id):
		dir_path = self.items.get(id, o.undefined)

		if dir_path is o.undefined:
			offset = self._find_slot(id)

			if offset is not o.undefined:
				path_data = self._view[offset + self.ID_SIZE : offset + self.SLOT_SIZE]
				dir_path  = path_data.tobytes().rstrip(b'\x00').decode('utf-8')

				if os.path.exists(dir_path):
					self.items[id] = dir_path
				else:
					dir_path = o.undefined

		return dir_path
