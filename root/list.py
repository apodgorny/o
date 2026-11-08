# ==============================================================================
# LIST
# ==============================================================================
# Implement persistent list behavior for ontology entities.
# ==============================================================================

from collections import Counter

import o

UNDEFINED = o.Undefined
ENDIAN = 'little'


class List(o.T):
	__annotation__ = list

	# Initialize list
	# ----------------------------------------------------------------------
	def __init__(self, value=UNDEFINED):
		if value is UNDEFINED:
			value = []

		self.__cast_in__(value)

	# Read list instance
	# ----------------------------------------------------------------------
	@classmethod
	def __read__(cls, version):
		self = super().__read__(version)

		self.__load_items__()

		return self

	# Get list item
	# ----------------------------------------------------------------------
	def __getitem__(self, index):
		o.Timer.start('o.List.__getitem__')

		value = o.services.Entity.value(self.__items__[index])

		o.Timer.stop('o.List.__getitem__')
		return value

	# Set list item
	# ----------------------------------------------------------------------
	def __setitem__(self, index, value):
		o.Timer.start('o.List.__setitem__')

		item_type = o.T if self.__class__.__annotation__.value is None else o.TMeta.__embody__(self.__class__.__annotation__.value.annotation)

		with o.services.Memory.write():
			old_id = self.__items__[index]
			child  = o.services.Entity.cast(item_type, value)

			if old_id != child.id:
				self.__link__(child)
				self.__unlink__(o.services.Entity.get(old_id))

			items        = list(self.__items__)
			items[index] = child.id
			self.__save_items__(items)

		o.Timer.stop('o.List.__setitem__')

	# Delete list item
	# ----------------------------------------------------------------------
	def __delitem__(self, index):
		with o.services.Memory.write():
			self.__unlink__(o.services.Entity.get(self.__items__[index]))
			items = list(self.__items__)
			del items[index]
			self.__save_items__(items)

	# Get list length
	# ----------------------------------------------------------------------
	def __len__(self):
		return len(self.__items__)

	# Iterate list values
	# ----------------------------------------------------------------------
	def __iter__(self):
		for item_id in self.__items__:
			yield o.services.Entity.value(item_id)

	# Get retained dependants
	# ----------------------------------------------------------------------
	def __dependants__(self, path=None):
		path = self.__proto__ if path is None else path

		for key, child_path, child in super().__dependants__(path):
			yield key, child_path, child

		for index, item_id in enumerate(self.__items__):
			yield index, f'{path}[{index}]', o.services.Entity.get(item_id)

	# Cast to list
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		return list(self)

	# Cast visible list into entity
	# ----------------------------------------------------------------------
	def __cast_in__(self, value):
		new_children = []
		additions    = []
		remaining    = Counter(self.__dict__.get('__items__', []))
		item_type    = o.T if self.__class__.__annotation__.value is None else o.TMeta.__embody__(self.__class__.__annotation__.value.annotation)

		with o.services.Memory.write():
			for item in value:
				child = o.services.Entity.cast(item_type, item)
				new_children.append(child)

			for child in new_children:
				if remaining[child.id] > 0:
					remaining[child.id] -= 1
				else:
					additions.append(child)

			if o.TREE_MODE:
				pending = set()

				for child in additions:
					self.__link__(child, check_only=True, pending=pending)

			for child in additions:
				self.__link__(child)

			for old_id, count in remaining.items():
				for _ in range(count):
					self.__unlink__(o.services.Entity.get(old_id))

			self.__save_items__([child.id for child in new_children])

	# Save list ids
	# ----------------------------------------------------------------------
	def __save_items__(self, items):
		buffer = bytearray()

		for item in items:
			buffer.extend(item.to_bytes(8, ENDIAN))

		object.__setattr__(self, '__items__', list(items))
		self.__zone__.set('__items__', bytes(buffer))

	# Load list ids
	# ----------------------------------------------------------------------
	def __load_items__(self):
		value = self.__zone__.get('__items__', b'')
		items = []

		if isinstance(value, list):
			items = value
		else:
			for i in range(0, len(value), 8):
				items.append(int.from_bytes(value[i:i + 8], ENDIAN))

		object.__setattr__(self, '__items__', items)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Append list item
	# ----------------------------------------------------------------------
	def append(self, value):
		item_type = o.T if self.__class__.__annotation__.value is None else o.TMeta.__embody__(self.__class__.__annotation__.value.annotation)

		with o.services.Memory.write():
			child = o.services.Entity.cast(item_type, value)
			self.__link__(child)
			items = list(self.__items__)
			items.append(child.id)
			self.__save_items__(items)
