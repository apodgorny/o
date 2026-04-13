import os
import struct

import o


class List(o.Module):

	FILE = '__list__'
	WORD = struct.Struct('<Q')

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Constructor
	# ----------------------------------------------------------------------
	def __init__(self, instance_path):
		self.instance_path = instance_path
		self.path          = os.path.join(instance_path, self.FILE)
		self.__items__     = []

		if not os.path.exists(self.path):
			self.__write__()

		with open(self.path, 'rb') as file:
			content = file.read()

		if content:
			num_ints   = len(content) // self.WORD.size
			items_word = struct.Struct(f'<{num_ints}Q')
			unpacked   = items_word.unpack(content)
			self.__items__ = list(unpacked)

	# Write list state
	# ----------------------------------------------------------------------
	def __write__(self):
		content    = b''

		if self.__items__:
			content = struct.Struct(f'<{len(self.__items__)}Q').pack(*self.__items__)

		with open(self.path, 'wb') as file:
			file.write(content)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Read whole items state
	# ----------------------------------------------------------------------
	@property
	def items(self):
		return self.__items__

	# Write whole items state
	# ----------------------------------------------------------------------
	@items.setter
	def items(self, items):
		self.__items__ = items
		self.__write__()

	# Get list item
	# ----------------------------------------------------------------------
	def get(self, index):
		item = None

		if 0 <= index < len(self.__items__):
			item = self.__items__[index]

		return item

	# Set list item
	# ----------------------------------------------------------------------
	def set(self, index, id):
		self.__items__[index] = id
		self.__write__()
