import o


class Node(o.Many):
	__fields__ = {}  # For T

	# ------------------------------------------------------------------
	def __init__(self, data):
		super().__init__(data, word='QHQ')

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS - ITEM-WISE
	# ======================================================================

	# ----------------------------------------------------------------------
	def __get__(self, accessor):
		if accessor not in self.__index__:
			raise AttributeError(accessor)

		idx = self.__index__[accessor]
		_, type_id, item_id = self.__items__[idx]

		return type_id, item_id

	# ----------------------------------------------------------------------
	def __set__(self, accessor, type_id, item_id):
		if accessor in self.__index__:
			idx                 = self.__index__[accessor]
			key_id, _, _        = self.__items__[idx]
			self.__items__[idx] = (key_id, type_id, item_id)
		else:
			key_id = o.Key(accessor).__id__
			idx    = len(self.__items__)
			self.__items__.append((key_id, type_id, item_id))
			self.__index__[accessor] = idx

		self.__write__()

	# ----------------------------------------------------------------------
	def __unset__(self, accessor):
		if accessor not in self.__index__:
			raise AttributeError(accessor)

		idx = self.__index__.pop(accessor)

		key_id, _, _ = self.__items__[idx]
		o.Key.bind(key_id).__delete__()

		self.__items__.pop(idx)

		for _accessor, _idx in self.__index__.items():
			if _idx > idx:
				self.__index__[_accessor] = _idx - 1

		self.__write__()

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS - SELF-WISE
	# ======================================================================

	# ----------------------------------------------------------------------
	def __cast_in__(self, data=None):
		raise RuntimeError('Node does not support cast')

	# ----------------------------------------------------------------------
	def __cast_out__(self):
		raise RuntimeError('Node does not support uncast')

	# ----------------------------------------------------------------------
	def __read__(self):
		self.__items__ = super().__read__()
		self.__index__ = {}

		for pos, (key_id, _, _) in enumerate(self.__items__):
			accessor = o.Key.bind(key_id).__cast_out__()
			self.__index__[accessor] = pos

	# ----------------------------------------------------------------------
	def __write__(self):
		return super().__write__()

	# ----------------------------------------------------------------------
	def __delete__(self):
		for key_id, _, _ in self.__items__:
			o.Key.bind(key_id).__delete__()

		return super().__delete__()

	# ----------------------------------------------------------------------
	def __clear__(self):
		for key_id, _, _ in self.__items__:
			o.Key.bind(key_id).__delete__()

		self.__items__ = []
		self.__index__ = {}

		super().__clear__()

	# ======================================================================
	# PYTHON INTERFACE
	# ======================================================================

	def __getattr__(self, name):
		if name.startswith('_'):
			raise AttributeError(name)

		if name in self.__index__:
			type_id, item_id = self.__get__(name)
			t_object         = o.types[type_id].bind(item_id)
			
			if isinstance(t_object, o.Many):
				value = t_object
			else:
				value = t_object.__cast_out__()
		else:
			value = super().__getattr__(name)
		
		return value
		
	# ----------------------------------------------------------------------
	def __setattr__(self, name, value):
		if name.startswith('_'):
			return super().__setattr__(name, value)

		value = self.__cast_in_item__(value)

		self.__set__(
			accessor = name,
			type_id  = value.__type_id__,
			item_id  = value.__id__
		)

	# ----------------------------------------------------------------------
	def __delattr__(self, name):
		if name.startswith('_'):
			return super().__delattr__(name)

		self.__unset__(name)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================