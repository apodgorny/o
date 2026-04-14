import o


class Dict(o.T):
	__annotation__ = dict

	# Initialize dict
	# ----------------------------------------------------------------------
	def __init__(self, value):
		items = {}

		for key, item in value.items():
			key_child   = o.T(key)
			value_child = o.T(item)

			items[key_child.id] = value_child.id

		self.__disk_instance__.dict.items = items

	# Get dict item
	# ----------------------------------------------------------------------
	def __getitem__(self, key):
		o.Timer.start('o.Dict.__getitem__')

		value_id = self.__disk_instance__.dict.get(key)
		value    = o.undefined

		if value_id is not o.undefined:
			value = o.get(value_id)

			if isinstance(value, o.Atom):
				value = value.__value__

		if value is o.undefined:
			o.Timer.stop('o.Dict.__getitem__')
			raise KeyError(key)

		o.Timer.stop('o.Dict.__getitem__')
		return value

	# Set dict item
	# ----------------------------------------------------------------------
	def __setitem__(self, key, value):
		o.Timer.start('o.Dict.__setitem__')

		child = o.T(value)

		self.__disk_instance__.dict.set(key, child.id)

		o.Timer.stop('o.Dict.__setitem__')

	# Delete dict item
	# ----------------------------------------------------------------------
	def __delitem__(self, key):
		self.__disk_instance__.dict.delete(key)

	# Check dict key
	# ----------------------------------------------------------------------
	def __contains__(self, key):
		stored_key = self.__disk_instance__.dict.get_key_id(key)

		return stored_key is not o.undefined

	# Get dict length
	# ----------------------------------------------------------------------
	def __len__(self):
		return len(self.__disk_instance__.dict.items)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Iterate dict items
	# ----------------------------------------------------------------------
	def items(self):
		for key_id, value_id in self.__disk_instance__.dict.items.items():
			key   = o.get(key_id)
			value = o.get(value_id)

			if isinstance(key, o.Atom):
				key = key.__value__

			if isinstance(value, o.Atom):
				value = value.__value__

			yield key, value

	# Update dict items
	# ----------------------------------------------------------------------
	def update(self, items):
		for key, value in items.items():
			self[key] = value
