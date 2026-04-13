import o


class Dict(o.T):
	__annotation__ = dict

	# Initialize dict
	# ----------------------------------------------------------------------
	def __init__(self, value):
		items = {}

		for key, value in value.items():
			key_instance   = o.T(key)
			value_instance = o.T(value)

			items[key_instance.id] = value_instance.id

		self.__disk_instance__.dict.items = items

	# Get dict item
	# ----------------------------------------------------------------------
	def __getitem__(self, key):
		o.Timer.start('o.Dict.__getitem__')

		value_id     = self.__disk_instance__.dict.get(key)
		value        = o.undefined

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

		value_instance = o.T(value)

		self.__disk_instance__.dict.set(key, value_instance.id)

		o.Timer.stop('o.Dict.__setitem__')

	# Delete dict item
	# ----------------------------------------------------------------------
	def __delitem__(self, key):
		key_id = self.__disk_instance__.dict.get_key_id(key)
		items  = self.__disk_instance__.dict.items

		if key_id is o.undefined:
			raise KeyError(key)

		del items[key_id]

		self.__disk_instance__.dict.items = items

	# Check dict key
	# ----------------------------------------------------------------------
	def __contains__(self, key):
		key_id = self.__disk_instance__.dict.get_key_id(key)

		return key_id is not o.undefined

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

			if isinstance(key,   o.Atom) : key   = key.__value__
			if isinstance(value, o.Atom) : value = value.__value__

			yield key, value

	# Update dict items
	# ----------------------------------------------------------------------
	def update(self, items):
		for key, value in items.items():
			self[key] = value
