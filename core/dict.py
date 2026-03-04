import o


class Dict(o.Many):
	__python_type__ = dict

	# ------------------------------------------------------------------
	def __init__(self, data=None):
		data = data if data is not None else {}
		super().__init__(data, word='HQHQ')

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS - ITEM-WISE
	# ======================================================================

	# ----------------------------------------------------------------------
	def __get__(self, key):
		if key not in self.__index__:
			raise KeyError(key)

		ref = self.__index__[key]
		idx = self.__ref_index__[ref]

		_, _, type_id, item_id = self.__items__[idx]

		return type_id, item_id

	# ----------------------------------------------------------------------
	def __set__(self, key, type_id, item_id):
		if key in self.__index__:
			ref = self.__index__[key]
			idx = self.__ref_index__[ref]

			key_t, key_i = ref
			self.__items__[idx] = (key_t, key_i, type_id, item_id)
		else:
			key_obj = self.__cast_in_item__(key)
			ref     = (key_obj.__type_id__, key_obj.__id__)

			idx = len(self.__items__)
			self.__items__.append((ref[0], ref[1], type_id, item_id))

			self.__index__[key]     = ref
			self.__ref_index__[ref] = idx

		self.__write__()

	# ----------------------------------------------------------------------
	def __unset__(self, key):
		if key not in self.__index__:
			raise KeyError(key)

		ref = self.__index__.pop(key)
		idx = self.__ref_index__.pop(ref)

		key_t, key_i, _, _ = self.__items__[idx]
		o.types[key_t].bind(key_i).__delete__()

		self.__items__.pop(idx)

		for _ref, _idx in self.__ref_index__.items():
			if _idx > idx:
				self.__ref_index__[_ref] = _idx - 1

		self.__write__()

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS - SELF-WISE
	# ======================================================================
	
	# ----------------------------------------------------------------------
	def __cast_in__(self, data):
		self.__items__      = []
		self.__ref_index__  = {}
		self.__index__      = {}

		for key, value in data.items():
			value_obj = self.__cast_in_item__(value)
			key_obj   = self.__cast_in_item__(key)

			ref = (key_obj.__type_id__, key_obj.__id__)

			idx = len(self.__items__)
			self.__items__.append((ref[0], ref[1], value_obj.__type_id__, value_obj.__id__))

			self.__ref_index__[ref] = idx
			self.__index__[key]     = ref

	# ----------------------------------------------------------------------
	def __cast_out__(self):
		result = {}

		for key_t, key_i, val_t, val_i in self.__items__:
			key_obj = o.types[key_t].bind(key_i)
			val_obj = o.types[val_t].bind(val_i)

			key   = key_obj.__cast_out__()
			value = self.__cast_out_item__(val_obj)

			result[key] = value

		return result

	# ----------------------------------------------------------------------
	def __read__(self):
		self.__items__     = super().__read__()
		self.__ref_index__ = {}
		self.__index__     = {}

		for pos, (key_t, key_i, _, _) in enumerate(self.__items__):
			key_obj   = o.types[key_t].bind(key_i)
			key_value = key_obj.__cast_out__()

			ref = (key_t, key_i)

			self.__ref_index__ [ref]       = pos
			self.__index__     [key_value] = ref

	# ----------------------------------------------------------------------
	def __write__(self):
		return super().__write__()

	# ----------------------------------------------------------------------
	def __delete__(self):
		for key_t, key_i, _, _ in self.__items__:
			o.types[key_t].bind(key_i).__delete__()

		return super().__delete__()

	# ----------------------------------------------------------------------
	def __clear__(self):
		for key_t, key_i, _, _ in self.__items__:
			o.types[key_t].bind(key_i).__delete__()

		self.__items__     = []
		self.__index__     = {}
		self.__ref_index__ = {}

		super().__clear__()

	# ======================================================================
	# PYTHON INTERFACE
	# ======================================================================

	# ----------------------------------------------------------------------
	def __getitem__(self, key):
		type_id, item_id = self.__get__(key)
		obj = o.types[type_id].bind(item_id)
		return self.__cast_out_item__(obj)

	# ----------------------------------------------------------------------
	def __setitem__(self, key, value):
		value = self.__cast_in_item__(value)

		self.__set__(
			key      = key,
			type_id  = value.__type_id__,
			item_id  = value.__id__
		)

	# ----------------------------------------------------------------------
	def __delitem__(self, key):
		self.__unset__(key)