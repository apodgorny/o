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
		self.__keys__      = {}   # key atomic_value or non_atomic_id -> key id

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
			visible_key = o.get(key_id)

			if visible_key is o.undefined:
				visible_key = key_id

			keys[self.__key__(visible_key)] = key_id

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
		old_items = dict(self.__items__)

		self.__items__ = dict(items)
		self.__bind_keys__()
		self.__write__()

		for key_id in set(old_items) - set(self.__items__):
			o.services.GC.dec(key_id)

		for key_id in set(self.__items__) - set(old_items):
			o.services.GC.inc(key_id)

		for key_id in set(old_items) | set(self.__items__):
			old_value_id = old_items.get(key_id, o.undefined)
			new_value_id = self.__items__.get(key_id, o.undefined)

			o.services.GC.update(old_value_id, new_value_id)

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
	def set(self, key, value_id):
		key_id       = self.get_key_id(key)
		old_value_id = o.undefined

		if key_id is o.undefined:
			if not isinstance(key, o.T):
				key = o.T(key)

			key_id = key.id
			o.services.GC.inc(key_id)
		else:
			old_value_id = self.__items__[key_id]

		self.__items__[key_id] = value_id
		self.__keys__[self.__key__(key)] = key_id
		self.__write__()
		o.services.GC.update(old_value_id, value_id)

		return old_value_id

	# Delete dict item
	# ----------------------------------------------------------------------
	def delete(self, key):
		token  = self.__key__(key)
		key_id = self.__keys__.get(token, o.undefined)

		if key_id is o.undefined:
			raise KeyError(key)

		value_id = self.__items__[key_id]

		del self.__items__[key_id]
		del self.__keys__[token]

		self.__write__()
		o.services.GC.dec(key_id)
		o.services.GC.dec(value_id)

		return value_id
