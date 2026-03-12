import o


class Dict(o.Many):
	__annotation__ = dict

	# ----------------------------------------------------------------------
	def __init__(self, data=None):
		data = data if data is not None else {}
		super().__init__(data, word='IQIQ')

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS - ITEM-WISE
	# ======================================================================

	# Iterate child instances
	# ----------------------------------------------------------------------
	def __children__(self):
		for k, v in self.items():
			yield k, v

	# Get value type and id by key
	# ----------------------------------------------------------------------
	def __get__(self, key):
		if key not in self.__index__:
			raise KeyError(key)

		ref = self.__index__[key]
		idx = self.__ref_index__[ref]

		_, _, type_id, item_id = self.__items__[idx]
		return type_id, item_id

	# Set value type and id by key
	# ----------------------------------------------------------------------
	def __set__(self, key, type_id, item_id, value_obj):
		if key in self.__index__:
			ref = self.__index__[key]
			idx = self.__ref_index__[ref]

			key_t, key_i = ref
			self.__items__[idx] = (key_t, key_i, type_id, item_id)
			key_obj = self.__refs__[key][0]
		else:
			key_obj = self.__cast_in_item__(key)
			ref     = (key_obj.__type_id__, key_obj.__id__)
			idx     = len(self.__items__)

			self.__items__.append((ref[0], ref[1], type_id, item_id))
			self.__index__[key]     = ref
			self.__ref_index__[ref] = idx

		self.__refs__[key] = (key_obj, value_obj)
		self.__write__()

	# Delete key and reindex internal refs
	# ----------------------------------------------------------------------
	def __unset__(self, key):
		if key not in self.__index__:
			raise KeyError(key)

		ref     = self.__index__.pop(key)
		idx     = self.__ref_index__.pop(ref)
		key_ref = self.__refs__.pop(key, None)

		if key_ref is not None:
			key_obj = key_ref[0]
		else:
			raise RuntimeError(f'Missing ref for key `{key}`')

		key_obj.__delete__()

		self.__items__.pop(idx)

		for _ref, _idx in self.__ref_index__.items():
			if _idx > idx:
				self.__ref_index__[_ref] = _idx - 1

		self.__write__()

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS - SELF-WISE
	# ======================================================================
	
	# Cast Python dict into storage state
	# ----------------------------------------------------------------------
	def __cast_in__(self, data):
		old_refs = getattr(self, '__refs__', {})

		self.__items__      = []
		self.__ref_index__  = {}
		self.__index__      = {}
		self.__refs__       = {}

		for key, value in data.items():
			pair = old_refs.get(key, None)

			key_obj = None
			reuse_item = None
			if pair is None:
				key_obj = self.__cast_in_item__(key)
			else:
				key_obj, reuse_item = pair

			value_obj = self.__cast_in_item__(value, reuse_item=reuse_item)

			ref = (key_obj.__type_id__, key_obj.__id__)

			idx = len(self.__items__)
			self.__items__.append((ref[0], ref[1], value_obj.__type_id__, value_obj.__id__))

			self.__ref_index__[ref] = idx
			self.__index__[key]     = ref
			self.__refs__[key]      = (key_obj, value_obj)

	# Cast storage state into public dict
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		result = {}

		for key in self.__index__:
			_, val_obj = self.__refs__[key]
			value = self.__cast_out_item__(val_obj)
			result[key] = value

		return result

	# Read dict state and reconcile refs
	# ----------------------------------------------------------------------
	def __read__(self):
		old_items     = getattr(self, '__items__',     [])
		old_index     = getattr(self, '__index__',     {})
		old_ref_index = getattr(self, '__ref_index__', {})
		old_refs      = getattr(self, '__refs__',      {})

		old_entries = {}
		for key_value, (key_obj, val_obj) in old_refs.items():
			ref = old_index.get(key_value, None)
			if ref is None:
				continue

			idx = old_ref_index.get(ref, None)
			if idx is None or idx >= len(old_items):
				continue

			_, _, val_t, val_i = old_items[idx]
			old_entries[ref] = ((val_t, val_i), key_obj, val_obj)

		self.__items__     = super().__read__()
		self.__ref_index__ = {}
		self.__index__     = {}
		self.__refs__      = {}

		for pos, (key_t, key_i, val_t, val_i) in enumerate(self.__items__):
			ref = (key_t, key_i)
			entry = old_entries.get(ref, None)

			if entry is None:
				key_obj = o.__types_by_id__[key_t].instantiate(key_i)
				val_obj = o.__types_by_id__[val_t].instantiate(val_i)
			else:
				old_val_ref, key_obj, val_obj = entry
				if old_val_ref != (val_t, val_i):
					val_obj = o.__types_by_id__[val_t].instantiate(val_i)

			key_value = key_obj.__cast_out__()

			self.__ref_index__[ref]   = pos
			self.__index__[key_value] = ref
			self.__refs__[key_value]  = (key_obj, val_obj)

	# Write dict state to storage
	# ----------------------------------------------------------------------
	def __write__(self):
		return super().__write__()

	# Delete dict and key objects
	# ----------------------------------------------------------------------
	def __delete__(self):
		for key_obj, _ in self.__refs__.values():
			key_obj.__delete__()

		self.__refs__ = {}

		return super().__delete__()

	# Clear dict and key objects
	# ----------------------------------------------------------------------
	def __clear__(self):
		for key_obj, _ in self.__refs__.values():
			key_obj.__delete__()

		self.__refs__ = {}

		self.__items__     = []
		self.__index__     = {}
		self.__ref_index__ = {}

		super().__clear__()

	# ======================================================================
	# PYTHON INTERFACE
	# ======================================================================

	# Read value by key
	# ----------------------------------------------------------------------
	def __getitem__(self, key):
		o.Timer.start('o.Dict.__getitem__')
		obj   = self.__refs__[key][1]
		value = self.__cast_out_item__(obj)
		o.Timer.stop('o.Dict.__getitem__')
		return value

	# Set value by key with reuse path
	# ----------------------------------------------------------------------
	def __setitem__(self, key, value):
		o.Timer.start('o.Dict.__setitem__')
		exists = key in self.__index__
		reuse_item = None

		if exists:
			reuse_item = self.__refs__[key][1]

		value = self.__cast_in_item__(value, reuse_item=reuse_item)

		if exists:
			ref = self.__index__[key]
			idx = self.__ref_index__[ref]
			_, _, old_t, old_i = self.__items__[idx]
			next_ref = (value.__type_id__, value.__id__)
			if (old_t, old_i) != next_ref:
				self.__set__(
					key       = key,
					type_id   = value.__type_id__,
					item_id   = value.__id__,
					value_obj = value
				)
		else:
			self.__set__(
				key       = key,
				type_id   = value.__type_id__,
				item_id   = value.__id__,
				value_obj = value
			)
		o.Timer.stop('o.Dict.__setitem__')

	# Delete value by key
	# ----------------------------------------------------------------------
	def __delitem__(self, key):
		self.__unset__(key)
