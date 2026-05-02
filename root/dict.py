import o

UNDEFINED = o.Undefined


class Dict(o.T):
	__annotation__ = dict

	# Get key id
	# ----------------------------------------------------------------------
	def _key_id(self, key):
		key_id = key

		if isinstance(key, o.T):
			if key.__class__.__is_atom__:
				key_id = key.__value__
			else:
				key_id = key.id

		return key_id

	# Resolve item key id
	# ----------------------------------------------------------------------
	def _item_key_id(self, key):
		o.Timer.start('o.Dict._key_id')
		key_id = self.__key_ids__.get(self._key_id(key), UNDEFINED)

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
		self    = super().__read__(version)
		items   = self.__zone__.get('__items__', {})
		key_ids = {}

		for key_id in items:
			key_ids[self._key_id(o.get(key_id))] = key_id

		object.__setattr__(self, '__items__', items)
		object.__setattr__(self, '__key_ids__', key_ids)

		return self

	# Get dict item
	# ----------------------------------------------------------------------
	def __getitem__(self, key):
		o.Timer.start('o.Dict.__getitem__')

		value    = UNDEFINED
		key_id   = self._item_key_id(key)
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

		with o.services.Memory.write():
			value_child = value if isinstance(value, o.T) else o.T(value)
			key_id      = self._item_key_id(key)
			old_value_id = UNDEFINED
			items       = self.__items__

			if key_id is UNDEFINED:
				key_child = key if isinstance(key, o.T) else o.T(key)
				o.services.Garbage.on_instance_link(key_child)

				key_id    = key_child.id
				self.__key_ids__[self._key_id(key_child)] = key_id
			else:
				old_value_id = items[key_id]

			if old_value_id != value_child.id:
				if old_value_id is not UNDEFINED:
					o.services.Garbage.on_instance_unlink(o.get(old_value_id))

				o.services.Garbage.on_instance_link(value_child)

			items[key_id] = value_child.id
			self.__zone__.set('__items__', items)

		o.Timer.stop('o.Dict.__setitem__')

	# Delete dict item
	# ----------------------------------------------------------------------
	def __delitem__(self, key):
		key_id = self._item_key_id(key)

		if key_id in self.__items__:
			with o.services.Memory.write():
				o.services.Garbage.on_instance_unlink(o.get(key_id))
				o.services.Garbage.on_instance_unlink(o.get(self.__items__[key_id]))
				del self.__key_ids__[self._key_id(key)]
				del self.__items__[key_id]
				self.__zone__.set('__items__', self.__items__)
		else:
			raise KeyError(key)

	# Check dict key
	# ----------------------------------------------------------------------
	def __contains__(self, key):
		return self._item_key_id(key) is not UNDEFINED

	# Get dict length
	# ----------------------------------------------------------------------
	def __len__(self):
		return len(self.__items__)
	
	# Get retained dependants
	# ----------------------------------------------------------------------
	def __dependants__(self):
		for item in super().__dependants__():
			yield item

		for key_id, value_id in self.__items__.items():
			yield o.get(key_id)
			yield o.get(value_id)

	# Cast to dict
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		return dict(self.items())

	# Cast visible dict into entity
	# ----------------------------------------------------------------------
	def __cast_in__(self, value):
		new_items = {}
		key_ids   = {}

		with o.services.Memory.write():
			for key, item in value.items():
				key_child   = key  if isinstance(key, o.T)  else o.T(key)
				value_child = item if isinstance(item, o.T) else o.T(item)
				o.services.Garbage.on_instance_link(key_child)
				o.services.Garbage.on_instance_link(value_child)
				new_items[key_child.id] = value_child.id
				key_ids[self._key_id(key_child)] = key_child.id

			self.__zone__.set('__items__', new_items)

		object.__setattr__(self, '__items__', new_items)
		object.__setattr__(self, '__key_ids__', key_ids)

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
