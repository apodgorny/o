import o


class Object(o.Many):
	__annotation__ = None

	# Constructor
	# ----------------------------------------------------------------------
	def __init__(self, data=o.undefined, **kwargs):
		if kwargs:
			data = kwargs
			
		super().__init__(data, word='QIQ')

		if data == o.undefined:
			self.__items__ = []
			self.__index__ = {}
			self.__refs__  = {}
		else:
			self.__cast_in__(data)

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS - ITEM-WISE
	# ======================================================================

	# Iterate child instances
	# ----------------------------------------------------------------------
	def __children__(self):
		for fname in self.__class__.__fields__:
			yield fname, getattr(self, fname)

	# Get value type and id by accessor
	# ----------------------------------------------------------------------
	def __get__(self, accessor):
		if accessor not in self.__index__:
			raise AttributeError(accessor)

		idx = self.__index__[accessor]
		_, type_id, item_id = self.__items__[idx]

		return type_id, item_id

	# Set value type and id by accessor
	# ----------------------------------------------------------------------
	def __set__(self, accessor, type_id, item_id, value_obj):
		if accessor in self.__index__:
			idx                 = self.__index__[accessor]
			key_id, _, _        = self.__items__[idx]
			self.__items__[idx] = (key_id, type_id, item_id)
			key_obj = self.__refs__[accessor][0]
		else:
			key_obj = o.Key(accessor)
			key_id  = key_obj.__id__
			idx     = len(self.__items__)
			self.__items__.append((key_id, type_id, item_id))
			self.__index__[accessor] = idx

		self.__refs__[accessor] = (key_obj, value_obj)

		self.__write__()

	# Delete accessor and reindex entries
	# ----------------------------------------------------------------------
	def __unset__(self, accessor):
		if accessor not in self.__index__:
			raise AttributeError(accessor)

		idx = self.__index__.pop(accessor)

		key_id, _, _ = self.__items__[idx]
		key_ref = self.__refs__.pop(accessor, None)
		if key_ref is None:
			raise RuntimeError(f'Missing ref for accessor `{accessor}`')
		else:
			key_obj = key_ref[0]

		key_obj.__delete__()

		self.__items__.pop(idx)

		for _accessor, _idx in self.__index__.items():
			if _idx > idx:
				self.__index__[_accessor] = _idx - 1

		self.__write__()

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS - SELF-WISE
	# ======================================================================

	# Cast Python dict into node state
	# ----------------------------------------------------------------------
	def __cast_in__(self, data=None):
		if not isinstance(data, dict):
			raise TypeError('Node expects dict')

		old_refs = getattr(self, '__refs__', {})

		self.__items__ = []
		self.__index__ = {}
		self.__refs__ = {}

		for accessor, value in data.items():
			pair = old_refs.get(accessor, None)

			key_obj = None
			reuse_item = None
			if pair is None:
				key_obj = o.Key(accessor)
			else:
				key_obj, reuse_item = pair

			value_obj = self.__cast_in_item__(value, reuse_item=reuse_item)

			idx = len(self.__items__)
			self.__items__.append((key_obj.__id__, value_obj.__type_id__, value_obj.__id__))
			self.__index__[accessor] = idx
			self.__refs__[accessor] = (key_obj, value_obj)

	# Cast node state into Python dict
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		result = {}

		for accessor, idx in self.__index__.items():
			key_id, type_id, item_id = self.__items__[idx]

			pair = self.__refs__.get(accessor, None)
			if pair is None:
				key_obj = o.Key.instantiate(key_id)
				value_obj = o.__types_by_id__[type_id].instantiate(item_id)
				self.__refs__[accessor] = (key_obj, value_obj)
			else:
				_, value_obj = pair

			result[accessor] = self.__cast_out_item__(value_obj)

		return result

	# Read node state and reconcile refs
	# ----------------------------------------------------------------------
	def __read__(self):
		old_items = getattr(self, '__items__', [])
		old_index = getattr(self, '__index__', {})
		old_refs  = getattr(self, '__refs__', {})

		old_entries = {}
		for accessor, (key_obj, value_obj) in old_refs.items():
			idx = old_index.get(accessor, None)
			if idx is None or idx >= len(old_items):
				continue

			key_id, type_id, item_id = old_items[idx]
			old_entries[key_id] = ((type_id, item_id), key_obj, value_obj)

		self.__items__ = super().__read__()
		self.__index__ = {}
		self.__refs__  = {}

		for pos, (key_id, type_id, item_id) in enumerate(self.__items__):
			entry = old_entries.get(key_id, None)

			if entry is None:
				key_obj = o.Key.instantiate(key_id)
				value_obj = o.__types_by_id__[type_id].instantiate(item_id)
			else:
				old_value_ref, key_obj, value_obj = entry
				if old_value_ref != (type_id, item_id):
					value_obj = o.__types_by_id__[type_id].instantiate(item_id)

			accessor = key_obj.__cast_out__()
			self.__index__[accessor] = pos
			self.__refs__[accessor] = (key_obj, value_obj)

	# Write node state to storage
	# ----------------------------------------------------------------------
	def __write__(self):
		return super().__write__()

	# Delete node and key objects
	# ----------------------------------------------------------------------
	def __delete__(self):
		for key_obj, _ in self.__refs__.values():
			key_obj.__delete__()

		self.__refs__ = {}

		return super().__delete__()

	# Clear node and key objects
	# ----------------------------------------------------------------------
	def __clear__(self):
		for key_obj, _ in self.__refs__.values():
			key_obj.__delete__()

		self.__refs__ = {}

		self.__items__ = []
		self.__index__ = {}

		super().__clear__()

	# ======================================================================
	# PYTHON INTERFACE
	# ======================================================================

	# Read node field value
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		o.Timer.start('o.Object.__getattr__')
		if name.startswith('_'):
			raise AttributeError(name)

		if name in self.__index__:
			t_object = self.__refs__[name][1]
			value = self.__cast_out_item__(t_object)
		else:
			value = super().__getattr__(name)
		
		o.Timer.stop('o.Object.__getattr__')
		return value
		
	# Set node field value
	# ----------------------------------------------------------------------
	def __setattr__(self, name, value):
		o.Timer.start('o.Object.__setattr__')
		if name.startswith('_'):
			super().__setattr__(name, value)
		else:
			exists = name in self.__index__
			reuse_item = None
			if exists:
				reuse_item = self.__refs__[name][1]

			value = self.__cast_in_item__(value, reuse_item=reuse_item)

			if exists:
				idx = self.__index__[name]
				_, old_t, old_i = self.__items__[idx]
				next_ref = (value.__type_id__, value.__id__)
				if (old_t, old_i) != next_ref:
					self.__set__(
						accessor  = name,
						type_id   = value.__type_id__,
						item_id   = value.__id__,
						value_obj = value
					)
			else:
				self.__set__(
					accessor  = name,
					type_id   = value.__type_id__,
					item_id   = value.__id__,
					value_obj = value
				)
		o.Timer.stop('o.Object.__setattr__')

	# Delete node field value
	# ----------------------------------------------------------------------
	def __delattr__(self, name):
		if name.startswith('_'):
			return super().__delattr__(name)

		self.__unset__(name)

	
