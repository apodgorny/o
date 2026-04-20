import os
import struct
import mmap

import o


class GC(o.Service):

	FILE      = '__refcounts__'
	CAPACITY  = 1048576
	SLOT_SIZE = 16

	# ======================================================================
	# SERVICE METHODS
	# ======================================================================

	# Initialize GC
	# ----------------------------------------------------------------------
	def initialize(self):
		self.enabled = True
		self.path    = os.path.join(o.__path__, o.DATA_DIR, self.FILE)

		# Create fixed-size binary refcount table
		# - - - - - - - - - - - - - - - - - - - - - - - 
		if not os.path.exists(self.path):
			with open(self.path, 'wb') as file:
				file.write(b'\x00' * (self.CAPACITY * self.SLOT_SIZE))

		self._file = open(self.path, 'r+b')
		self._mmap = mmap.mmap(self._file.fileno(), 0)
		self._view = memoryview(self._mmap).cast('Q')

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Find refcount slot
	# ----------------------------------------------------------------------
	def _find_slot(self, id, create=False):
		start_index = (id % self.CAPACITY)
		index       = start_index
		slot_ptr    = o.Undefined

		for _ in range(self.CAPACITY):
			ptr     = index * 2
			slot_id = self._view[ptr]

			if slot_id == id:
				slot_ptr = ptr
				break

			if slot_id == 0:
				if create:
					self._view[ptr] = id
					slot_ptr = ptr

				break

			index = (index + 1) % self.CAPACITY

		if slot_ptr is o.Undefined and create:
			raise RuntimeError('GC refcount table is full')

		return slot_ptr

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Read persistent reference count
	# ----------------------------------------------------------------------
	def get(self, id):
		slot_ptr = self._find_slot(id)
		count    = 0

		if slot_ptr is not o.Undefined:
			count = self._view[slot_ptr + 1]

		return count

	# Write persistent reference count
	# ----------------------------------------------------------------------
	def set(self, id, count):
		slot_ptr = self._find_slot(id, create=True)
		self._view[slot_ptr + 1] = count

	# Get direct child ids of entity room
	# ----------------------------------------------------------------------
	def get_children(self, id):
		path     = o.id_to_path(id)
		children = []

		if path is not o.Undefined:
			entity = o.disk.Entity.load(id)

			for name in entity.attributes.items:
				children.append(entity.attributes.get(name))

			if hasattr(entity, 'list'):
				for child_id in entity.list.items:
					children.append(child_id)

			if hasattr(entity, 'dict'):
				for key_id, value_id in entity.dict.items.items():
					children.append(key_id)
					children.append(value_id)

		return children

	# Release zero-ref instance entity
	# ----------------------------------------------------------------------
	def release(self, id):
		path        = o.id_to_path(id)
		is_released = False
		root_id     = o.__dict__.get('V', o.Undefined)

		if root_id is not o.Undefined:
			root_id = root_id.id

		if path is not o.Undefined and id != root_id:
			version = os.path.basename(path)

			if o.is_instance_version(version):
				children   = self.get_children(id)
				instance   = o.disk.Entity.load(id)
				parent_dir = os.path.dirname(os.path.dirname(path))

				o.disk.Instances(parent_dir).remove(int(version[1:]))

				if id in o.__entities__:
					del o.__entities__[id]

				instance.delete()
				o.services.Registry.remove(id)
				is_released = True

				for child_id in children:
					self.dec(child_id)

		return is_released

	# Sweep zero-ref orphans on startup
	# ----------------------------------------------------------------------
	def sweep(self):
		ids      = []
		root_id  = o.__dict__.get('V', o.Undefined)
		registry = o.services.Registry

		if root_id is not o.Undefined:
			root_id = root_id.id

		for i in range(registry.CAPACITY):
			offset  = i * registry.SLOT_SIZE
			slot_id = struct.unpack('<Q', registry._view[offset : offset + registry.ID_SIZE])[0]

			if slot_id != 0:
				ids.append(slot_id)

		for id in ids:
			path = o.id_to_path(id)

			if path is not o.Undefined:
				version = os.path.basename(path)

				if o.is_instance_version(version) and id != root_id and self.get(id) == 0:
					self.release(id)

	# Update persistent reference edge
	# ----------------------------------------------------------------------
	def update(self, old_id, new_id):
		if old_id != new_id:
			if old_id is not o.Undefined:
				self.dec(old_id)

			if new_id is not o.Undefined:
				self.inc(new_id)

	# Increment persistent reference count
	# ----------------------------------------------------------------------
	def inc(self, id):
		slot_ptr = self._find_slot(id, create=True)
		self._view[slot_ptr + 1] += 1

	# Decrement persistent reference count
	# ----------------------------------------------------------------------
	def dec(self, id):
		slot_ptr = self._find_slot(id, create=True)
		count    = self._view[slot_ptr + 1]

		if count <= 0:
			raise ValueError(f'Cannot decrement refcount below zero for `{id}`')

		count -= 1
		self._view[slot_ptr + 1] = count

		if count == 0:
			self.release(id)
