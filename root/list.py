import o


class List(o.T):
	__annotation__ = list

	# Initialize list
	# ----------------------------------------------------------------------
	def __init__(self, value):
		self.__cast_in__(value)

	# Get list item
	# ----------------------------------------------------------------------
	def __getitem__(self, index):
		o.Timer.start('o.List.__getitem__')

		child = o.get(self.__disk_instance__.list.get(index))
		value = child

		if child.__class__.__is_atom__:
			value = child.__value__

		o.Timer.stop('o.List.__getitem__')

		return value

	# Set list item
	# ----------------------------------------------------------------------
	def __setitem__(self, index, value):
		o.Timer.start('o.List.__setitem__')

		child = o.T(value)

		self.__disk_instance__.list.set(index, child.id)

		o.Timer.stop('o.List.__setitem__')

	# Delete list item
	# ----------------------------------------------------------------------
	def __delitem__(self, index):
		self.__disk_instance__.list.delete(index)

	# Get list length
	# ----------------------------------------------------------------------
	def __len__(self):
		return len(self.__disk_instance__.list.items)

	# Iterate list values
	# ----------------------------------------------------------------------
	def __iter__(self):
		for index in range(len(self)):
			yield self[index]

	# Cast to list
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		return list(self)

	# Cast visible list into entity
	# ----------------------------------------------------------------------
	def __cast_in__(self, value):
		ids = [o.T(item).id for item in value]

		self.__disk_instance__.list.items = ids

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Append list item
	# ----------------------------------------------------------------------
	def append(self, value):
		child = o.T(value)
		ids   = list(self.__disk_instance__.list.items)

		ids.append(child.id)

		self.__disk_instance__.list.items = ids
