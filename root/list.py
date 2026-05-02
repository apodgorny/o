import o


class List(o.T):
	__annotation__ = list

	# Initialize list
	# ----------------------------------------------------------------------
	def __init__(self, value):
		self.__cast_in__(value)

	# Read list instance
	# ----------------------------------------------------------------------
	@classmethod
	def __read__(cls, version):
		self      = super().__read__(version)
		items_key = f'{self.__proto__}.__items__'
		items     = o.services.Memory.get(items_key, [])

		object.__setattr__(self, '__items_key__', items_key)
		object.__setattr__(self, '__items__', items)

		return self

	# Get list item
	# ----------------------------------------------------------------------
	def __getitem__(self, index):
		o.Timer.start('o.List.__getitem__')

		value = o.value(self.__items__[index])

		o.Timer.stop('o.List.__getitem__')
		return value

	# Set list item
	# ----------------------------------------------------------------------
	def __setitem__(self, index, value):
		o.Timer.start('o.List.__setitem__')

		with o.services.Memory.write():
			old_id = self.__items__[index]
			child  = value if isinstance(value, o.T) else o.T(value)

			if old_id != child.id:
				o.services.Garbage.on_instance_unlink(o.get(old_id))
				o.services.Garbage.on_instance_link(child)

			self.__items__[index] = child.id
			o.services.Memory.set(self.__items_key__, self.__items__)

		o.Timer.stop('o.List.__setitem__')

	# Delete list item
	# ----------------------------------------------------------------------
	def __delitem__(self, index):
		with o.services.Memory.write():
			o.services.Garbage.on_instance_unlink(o.get(self.__items__[index]))
			del self.__items__[index]
			o.services.Memory.set(self.__items_key__, self.__items__)

	# Get list length
	# ----------------------------------------------------------------------
	def __len__(self):
		return len(self.__items__)

	# Iterate list values
	# ----------------------------------------------------------------------
	def __iter__(self):
		for item_id in self.__items__:
			yield o.value(item_id)

	# Get retained dependants
	# ----------------------------------------------------------------------
	def __dependants__(self):
		for item in super().__dependants__():
			yield item

		for item_id in self.__items__:
			yield o.get(item_id)

	# Cast to list
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		return list(self)

	# Cast visible list into entity
	# ----------------------------------------------------------------------
	def __cast_in__(self, value):
		new_ids = []

		with o.services.Memory.write():
			for item in value:
				child = item if isinstance(item, o.T) else o.T(item)
				o.services.Garbage.on_instance_link(child)
				new_ids.append(child.id)

			o.services.Memory.set(self.__items_key__, new_ids)

		object.__setattr__(self, '__items__', new_ids)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Append list item
	# ----------------------------------------------------------------------
	def append(self, value):
		with o.services.Memory.write():
			child = value if isinstance(value, o.T) else o.T(value)
			o.services.Garbage.on_instance_link(child)
			self.__items__.append(child.id)
			o.services.Memory.set(self.__items_key__, self.__items__)
