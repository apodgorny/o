import os
import struct

import o


class Dict(o.Module):

	FILE = '__dict__'
	WORD = struct.Struct('<Q')

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Constructor
	# ----------------------------------------------------------------------
	def __init__(self, instance_path):
		self.instance_path = instance_path
		self.path          = os.path.join(instance_path, self.FILE)
		self.__items__     = {}   # key id -> value id
		self.__keys__      = {}   # key atomi_value or non_atomic_id -> key id

		if not os.path.exists(self.path):
			self.__write__()

		self.__read__()

	# Get key lookup token
	# ----------------------------------------------------------------------
	def __key__(self, key):
		token = ('value', key)

		if isinstance(key, o.Atom):
			token = ('value', key.__value__)
		elif isinstance(key, o.T):
			token = ('id', key.id)

		return token

	# Bind keys index
	# ----------------------------------------------------------------------
	def __bind_keys__(self):
		keys = {}

		for key_id in self.__items__:
			key = key_id

			if o.is_atomic(key_id):
				key = o.get(key_id)

			keys[self.__key__(key)] = key_id

		self.__keys__ = keys

	# Read dict state
	# ----------------------------------------------------------------------
	def __read__(self):
		with open(self.path, 'rb') as file:
			content = file.read()

		if content:
			num_ints   = len(content) // self.WORD.size
			items_word = struct.Struct(f'<{num_ints}Q')
			unpacked   = items_word.unpack(content)
			items      = {}

			for i in range(0, len(unpacked), 2):
				key_id   = unpacked[i]
				value_id = unpacked[i + 1]

				items[key_id] = value_id

			self.__items__ = items

		self.__bind_keys__()

	# Write dict state
	# ----------------------------------------------------------------------
	def __write__(self):
		data       = []
		content    = b''

		for key_id, value_id in self.__items__.items():
			data.append(key_id)
			data.append(value_id)

		if data:
			content = struct.Struct(f'<{len(data)}Q').pack(*data)

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
		self.__bind_keys__()
		self.__write__()

	# Get dict item
	# ----------------------------------------------------------------------
	def get(self, key):
		value  = o.undefined
		key    = self.__key__(key)
		key_id = self.__keys__.get(key, o.undefined)

		if key_id is not o.undefined:
			value = self.__items__.get(key_id, o.undefined)

		return value

	# Get dict key id
	# ----------------------------------------------------------------------
	def get_key_id(self, key):
		key    = self.__key__(key)
		key_id = self.__keys__.get(key, o.undefined)

		return key_id

	# Set dict item
	# ----------------------------------------------------------------------
	def set(self, key, id):
		key_id = self.get_key_id(key)

		if key_id is o.undefined:
			if not isinstance(key, o.T):
				key = o.T(key)

			key_id = key.id

		self.__items__[key_id] = id
		self.__keys__[self.__key__(key)] = key_id
		self.__write__()
