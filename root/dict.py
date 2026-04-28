import o

UNDEFINED = o.Undefined


class Dict(o.T):
	__annotation__ = dict

	# Resolve stored key id
	# ----------------------------------------------------------------------
	def _key_id(self, key):
		o.Timer.start('o.Dict._key_id')
		key_id      = UNDEFINED
		visible_key = key
		items       = self.__items__

		if isinstance(key, o.T) and not key.__class__.__is_atom__:
			if key.id in items:
				key_id = key.id
		else:
			if isinstance(key, o.T):
				visible_key = key.__value__

			for item_key_id in items:
				if o.value(item_key_id) == visible_key:
					key_id = item_key_id
					break

		o.Timer.stop('o.Dict._key_id')
		return key_id

	# Initialize dict
	# ----------------------------------------------------------------------
	def __init__(self, value):
		self.__cast_in__(value)

	# Read dict instance
	# ----------------------------------------------------------------------
	@classmethod
	def __read__(cls, version):
		self      = super().__read__(version)
		items_key = f'{self.__proto__}.__items__'

		with o.services.Memory.read() as memory:
			items = memory.get(items_key, {})

		object.__setattr__(self, '__items_key__', items_key)
		object.__setattr__(self, '__items__', items)

		return self

	# Get dict item
	# ----------------------------------------------------------------------
	def __getitem__(self, key):
		o.Timer.start('o.Dict.__getitem__')

		value    = UNDEFINED
		key_id   = self._key_id(key)
		value_id = self.__items__.get(key_id, UNDEFINED)

		if value_id is not UNDEFINED:
			value = o.value(value_id)

		if value is UNDEFINED:
			raise KeyError(key)

		o.Timer.stop('o.Dict.__getitem__')
		return value

	# Set dict item
	# ----------------------------------------------------------------------
	def __setitem__(self, key, value):
		o.Timer.start('o.Dict.__setitem__')

		with o.services.Memory.write() as memory:
			value_child = value if isinstance(value, o.T) else o.T(value)
			key_id      = self._key_id(key)
			items       = self.__items__

			if key_id is UNDEFINED:
				key_child = key if isinstance(key, o.T) else o.T(key)
				key_id    = key_child.id

			items[key_id] = value_child.id
			memory.set(self.__items_key__, items)

		o.Timer.stop('o.Dict.__setitem__')

	# Delete dict item
	# ----------------------------------------------------------------------
	def __delitem__(self, key):
		key_id = self._key_id(key)

		with o.services.Memory.write() as memory:
			if key_id in self.__items__:
				del self.__items__[key_id]
				memory.set(self.__items_key__, self.__items__)
			else:
				raise KeyError(key)

	# Check dict key
	# ----------------------------------------------------------------------
	def __contains__(self, key):
		key_id = self._key_id(key)
		result = key_id is not UNDEFINED

		return result

	# Get dict length
	# ----------------------------------------------------------------------
	def __len__(self):
		length = len(self.__items__)
		return length

	# Cast to dict
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		return dict(self.items())

	# Cast visible dict into entity
	# ----------------------------------------------------------------------
	def __cast_in__(self, value):
		new_items = {}

		with o.services.Memory.write() as memory:
			for key, item in value.items():
				key_child   = key  if isinstance(key, o.T)  else o.T(key)
				value_child = item if isinstance(item, o.T) else o.T(item)
				new_items[key_child.id] = value_child.id

			memory.set(self.__items_key__, new_items)

		object.__setattr__(self, '__items__', new_items)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Iterate dict items
	# ----------------------------------------------------------------------
	def items(self):
		for key_id, value_id in self.__items__.items():
			key   = o.value(key_id)
			value = o.value(value_id)

			yield key, value

	# Update dict items
	# ----------------------------------------------------------------------
	def update(self, items):
		with o.services.Memory.write():
			for key, value in items.items():
				self[key] = value
