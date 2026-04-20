import os
import struct

import o


class Attributes(o.Module):

	FILE = '__attributes__'
	WORD = struct.Struct('<Q')

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Constructor
	# ----------------------------------------------------------------------
	def __init__(self, instance_path):
		self.instance_path = instance_path
		self.path          = os.path.join(instance_path, self.FILE)
		self.items         = {}

		if os.path.exists(self.path):
			with open(self.path, 'rb') as file:
				content = file.read()

			if content:
				offset = 0
				count  = self.WORD.unpack(content[offset:offset + self.WORD.size])[0]
				offset += self.WORD.size

				for _ in range(count):
					name_len = self.WORD.unpack(content[offset:offset + self.WORD.size])[0]
					offset  += self.WORD.size

					name = content[offset:offset + name_len].decode('utf-8')
					offset += name_len

					id = self.WORD.unpack(content[offset:offset + self.WORD.size])[0]
					offset += self.WORD.size

					self.items[name] = id

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Write full attribute state
	# ----------------------------------------------------------------------
	def _write(self):
		parts = [self.WORD.pack(len(self.items))]

		for name, id in self.items.items():
			name_bytes = name.encode('utf-8')

			parts.append(self.WORD.pack(len(name_bytes)))
			parts.append(name_bytes)
			parts.append(self.WORD.pack(id))

		with open(self.path, 'wb') as file:
			file.write(b''.join(parts))

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Set attribute state
	# ----------------------------------------------------------------------
	def set(self, name, id):
		old_id = self.items.get(name, o.Undefined)

		self.items[name] = id
		self._write()

		o.services.GC.update(old_id, id)

		return old_id

	# Get attribute state
	# ----------------------------------------------------------------------
	def get(self, name):
		return self.items.get(name)

	# Delete attribute state
	# ----------------------------------------------------------------------
	def delete(self, name):
		if name not in self.items:
			raise AttributeError(name)

		id = self.items[name]

		del self.items[name]
		self._write()
		o.services.GC.dec(id)

		return id

	# Check attribute state
	# ----------------------------------------------------------------------
	def has(self, name):
		return name in self.items