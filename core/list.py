import o


class List(o.T):
	__annotation__ = list

	# Initialize list
	# ----------------------------------------------------------------------
	def __init__(self, value):
		ids = []

		for item in value:
			child = o.T(item)
			ids.append(child.id)

		self.__disk_instance__.list.items = ids

	# Get list item
	# ----------------------------------------------------------------------
	def __getitem__(self, index):
		o.Timer.start('o.List.__getitem__')

		id    = self.__disk_instance__.list.get(index)
		value = o.get(id)

		if isinstance(value, o.Atom):
			value = value.__value__

		o.Timer.stop('o.List.__getitem__')

		return value

	# Set list item
	# ----------------------------------------------------------------------
	def __setitem__(self, index, value):
		o.Timer.start('o.List.__setitem__')

		value_instance = o.T(value)
		self.__disk_instance__.list.set(index, value_instance.id)

		o.Timer.stop('o.List.__setitem__')

	# Delete list item
	# ----------------------------------------------------------------------
	def __delitem__(self, index):
		items = self.__disk_instance__.list.items

		del items[index]

		self.__disk_instance__.list.items = items

	# Get list length
	# ----------------------------------------------------------------------
	def __len__(self):
		return len(self.__disk_instance__.list.items)

	# Iterate list values
	# ----------------------------------------------------------------------
	def __iter__(self):
		for index in range(len(self)):
			yield self[index]

	# Append list item
	# ----------------------------------------------------------------------
	def append(self, value):
		items          = self.__disk_instance__.list.items
		value_instance = o.T(value)

		items.append(value_instance.id)

		self.__disk_instance__.list.items = items
