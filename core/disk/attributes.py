import os
import struct

import o


class Attributes(o.Module):

	DIR  = '__attributes__'
	WORD = struct.Struct('<Q')

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Constructor
	# ----------------------------------------------------------------------
	def __init__(self, instance_path):
		self.instance_path = instance_path
		self.path          = os.path.join(instance_path, self.DIR)
		self.items         = {}

		os.makedirs(self.path, exist_ok=True)

		for name in os.listdir(self.path):
			path = os.path.join(self.path, name)

			if os.path.isfile(path):
				self.items[name] = None

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Set attribute state
	# ----------------------------------------------------------------------
	def set(self, name, id):
		self.items[name] = id

		with open(os.path.join(self.path, name), 'wb') as file:
			file.write(self.WORD.pack(id))

	# Get attribute state
	# ----------------------------------------------------------------------
	def get(self, name):
		item = self.items.get(name)

		if item is None and name in self.items:
			with open(os.path.join(self.path, name), 'rb') as file:
				item = self.WORD.unpack(file.read())[0]

			self.items[name] = item

		return item

	# Check attribute state
	# ----------------------------------------------------------------------
	def has(self, name):
		return name in self.items
