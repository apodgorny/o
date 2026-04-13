import o


class List(o.Many):

	__annotation__ = list

	# ----------------------------------------------------------------------
	def __init__(self, data=None):
		data = data if data is not None else []
		super().__init__(data, word='IQ')

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS - ITEM-WISE
	# ======================================================================

	# Iterate child instances
	# ----------------------------------------------------------------------
	def __children__(self):
		for i, v in enumerate(self):
			yield i, v

	# Validate and normalize list index
	# ----------------------------------------------------------------------
	def __normalize_index__(self, index):
		if not isinstance(index, int):
			raise TypeError(index)

		size = len(self.__items__)
		if index < 0:
			index = size + index

		if index < 0 or index >= size:
			raise IndexError(index)

		return index

	# Get item type and id by index
	# ----------------------------------------------------------------------
	def __get__(self, index):
		index = self.__normalize_index__(index)
		type_id, item_id = self.__items__[index]

		return type_id, item_id

	# Set item type and id by index
	# ----------------------------------------------------------------------
	def __set__(self, index, type_id, item_id, value_obj):
		self.__items__[index] = (type_id, item_id)

		self.__refs__.pop(index, None)
		self.__refs__[index] = value_obj
		self.__write__()

	# Delete item by index and reindex refs
	# ----------------------------------------------------------------------
	def __unset__(self, index):
		index = self.__normalize_index__(index)

		self.__refs__.pop(index, None)
		self.__items__.pop(index)

		for pos in range(index + 1, len(self.__items__) + 1):
			if pos in self.__refs__:
				self.__refs__[pos - 1] = self.__refs__.pop(pos)

		self.__write__()

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS - SELF-WISE
	# ======================================================================

	# Cast Python list into storage state
	# ----------------------------------------------------------------------
	def __cast_in__(self, data):
		if not isinstance(data, list):
			raise TypeError('List expects list')

		old_refs = getattr(self, '__refs__', {})

		self.__items__ = []
		self.__refs__ = {}

		for idx, value in enumerate(data):
			reuse_item = old_refs.get(idx, None)
			value_obj = self.__cast_in_item__(value, reuse_item=reuse_item)

			self.__items__.append((
				value_obj.__type_id__,
				value_obj.__id__
			))
			self.__refs__[idx] = value_obj

	# Cast storage state into public list
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		result = []

		for idx, (type_id, item_id) in enumerate(self.__items__):
			obj = self.__refs__[idx]
			value = self.__cast_out_item__(obj)
			result.append(value)

		return result

	# Read list state and reconcile refs
	# ----------------------------------------------------------------------
	def __read__(self):
		old_items = getattr(self, '__items__', [])
		old_refs  = getattr(self, '__refs__', {})

		refs_by_item = {}
		for idx, obj in old_refs.items():
			if idx < len(old_items):
				ref = old_items[idx]
				refs_by_item.setdefault(ref, []).append(obj)

		self.__items__ = super().__read__()
		self.__refs__  = {}

		for idx, (type_id, item_id) in enumerate(self.__items__):
			ref = (type_id, item_id)
			pool = refs_by_item.get(ref)

			if pool : obj = pool.pop()
			else    : obj = o.__types_by_id__[type_id].instantiate(item_id)

			self.__refs__[idx] = obj

	# Write list state to storage
	# ----------------------------------------------------------------------
	def __write__(self):
		return super().__write__()

	# Delete list and drop refs
	# ----------------------------------------------------------------------
	def __delete__(self):
		self.__refs__ = {}
		return super().__delete__()

	# Clear list and drop refs
	# ----------------------------------------------------------------------
	def __clear__(self):
		self.__refs__ = {}
		self.__items__ = []
		super().__clear__()

	# ======================================================================
	# PYTHON INTERFACE
	# ======================================================================

	# Read list item or slice
	# ----------------------------------------------------------------------
	def __getitem__(self, index):
		o.Timer.start('o.List.__getitem__')
		value = None

		if isinstance(index, slice):
			start, stop, step = index.indices(len(self.__items__))
			value = []

			for pos in range(start, stop, step):
				obj = self.__refs__[pos]
				value.append(self.__cast_out_item__(obj))
		else:
			index = self.__normalize_index__(index)
			obj = self.__refs__[index]
			value = self.__cast_out_item__(obj)

		o.Timer.stop('o.List.__getitem__')
		return value

	# Update item value by index
	# ----------------------------------------------------------------------
	def __setitem__(self, index, value):
		o.Timer.start('o.List.__setitem__')
		index = self.__normalize_index__(index)
		reuse_item = self.__refs__[index]
		value      = self.__cast_in_item__(value, reuse_item=reuse_item)

		next_ref = (value.__type_id__, value.__id__)
		if self.__items__[index] != next_ref:
			self.__set__(
				index     = index,
				type_id   = value.__type_id__,
				item_id   = value.__id__,
				value_obj = value
			)
		o.Timer.stop('o.List.__setitem__')

	# Remove item by index
	# ----------------------------------------------------------------------
	def __delitem__(self, index):
		self.__unset__(index)

	# Append value to the list
	# ----------------------------------------------------------------------
	def append(self, value):
		value = self.__cast_in_item__(value)
		index = len(self.__items__)

		self.__items__.append((
			value.__type_id__,
			value.__id__
		))
		self.__refs__[index] = value

		self.__write__()

	# Pop value by index
	# ----------------------------------------------------------------------
	def pop(self, index=-1):
		index = self.__normalize_index__(index)
		type_id, item_id = self.__items__[index]
		obj = self.__refs__.get(index, None)
		if obj is None:
			obj = o.__types_by_id__[type_id].instantiate(item_id)
			self.__refs__[index] = obj
		value = self.__cast_out_item__(obj)

		self.__unset__(index)

		return value

	# Return list length
	# ----------------------------------------------------------------------
	def __len__(self):
		return len(self.__items__)
