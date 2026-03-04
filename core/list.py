import o


class List(o.Many):

	__python_type__ = list

	# ------------------------------------------------------------------
	def __init__(self, data):
		super().__init__(data, word='HQ')

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS - ITEM-WISE
	# ======================================================================

	# ----------------------------------------------------------------------
	def __get__(self, index):
		if not isinstance(index, int):
			raise TypeError(index)

		try:
			type_id, item_id = self.__items__[index]
		except IndexError:
			raise IndexError(index)

		return type_id, item_id

	# ----------------------------------------------------------------------
	def __set__(self, index, type_id, item_id):
		if not isinstance(index, int):
			raise TypeError(index)

		try:
			self.__items__[index] = (type_id, item_id)
		except IndexError:
			raise IndexError(index)

		self.__write__()

	# ----------------------------------------------------------------------
	def __unset__(self, index):
		if not isinstance(index, int):
			raise TypeError(index)

		try:
			self.__items__.pop(index)
		except IndexError:
			raise IndexError(index)

		self.__write__()

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS - SELF-WISE
	# ======================================================================

	# ----------------------------------------------------------------------
	def __cast_in__(self, data):
		if not isinstance(data, list):
			raise TypeError('List expects list')

		self.__items__ = []

		for value in data:
			value_obj = self.__cast_in_item__(value)
			self.__items__.append((
				value_obj.__type_id__,
				value_obj.__id__
			))

	# ----------------------------------------------------------------------
	def __cast_out__(self):
		result = []

		for type_id, item_id in self.__items__:
			obj   = o.types[type_id].bind(item_id)
			value = self.__cast_out_item__(obj)
			result.append(value)

		return result

	# ----------------------------------------------------------------------
	def __read__(self):
		self.__items__ = super().__read__()

	# ----------------------------------------------------------------------
	def __write__(self):
		return super().__write__()

	# ----------------------------------------------------------------------
	def __delete__(self):
		return super().__delete__()

	# ----------------------------------------------------------------------
	def __clear__(self):
		self.__items__ = []
		super().__clear__()

	# ======================================================================
	# PYTHON INTERFACE
	# ======================================================================

	# ----------------------------------------------------------------------
	def __getitem__(self, index):
		type_id, item_id = self.__get__(index)
		obj = o.types[type_id].bind(item_id)
		return self.__cast_out_item__(obj)

	# ----------------------------------------------------------------------
	def __setitem__(self, index, value):
		value = self.__cast_in_item__(value)

		self.__set__(
			index    = index,
			type_id  = value.__type_id__,
			item_id  = value.__id__
		)

	# ----------------------------------------------------------------------
	def __delitem__(self, index):
		self.__unset__(index)

	# ----------------------------------------------------------------------
	def append(self, value):
		value = self.__cast_in_item__(value)

		self.__items__.append((
			value.__type_id__,
			value.__id__
		))

		self.__write__()

	# ----------------------------------------------------------------------
	def pop(self, index=-1):
		type_id, item_id = self.__get__(index)

		obj = o.types[type_id].bind(item_id)
		value = self.__cast_out_item__(obj)

		self.__unset__(index)

		return value

	# ----------------------------------------------------------------------
	def __len__(self):
		return len(self.__items__)