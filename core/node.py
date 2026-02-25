import o


class Node(o.Many):

	# ------------------------------------------------------------------
	def __init__(self, id=None, data=None):
		super().__init__(word='QHQ', id=id, data=data)

	# ======================================================================
	# Item-Wise Methods
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
			key_id = o.Key(data=accessor).__id__
			idx    = len(self.__items__)
			self.__items__.append((key_id, type_id, item_id))
			self.__index__[accessor] = idx

		self.__write__()

	# ----------------------------------------------------------------------
	def __unset__(self, accessor):
		if accessor not in self.__index__:
			raise AttributeError(accessor)

		idx = self.__index__.pop(accessor)
		self.__items__.pop(idx)

		# reindex positions after removal
		for _accessor, _idx in self.__index__.items():
			if _idx > idx:
				self.__index__[_accessor] = _idx - 1

		self.__write__()

	# ======================================================================
	# Object-Wise Methods
	# ======================================================================

	# ----------------------------------------------------------------------
	def __read__(self):
		items = o.services.Many.read(self.__id__)
		index = {}

		for pos, (key_id, _, _) in enumerate(items):
			accessor = o.Key(id=key_id).__uncast__()
			index[accessor] = pos

		return items, index

	# ----------------------------------------------------------------------
	def __write__(self):
		return o.services.Many.write(self.__id__, self.__items__)

	# ======================================================================
	
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		if name.startswith('_'):
			raise AttributeError(name)

		type_id, item_id = self.__get__(name)
		obj = o.types[type_id](id=item_id)
		return self.__uncast_item__(obj)

	# ----------------------------------------------------------------------
	def __setattr__(self, name, value):
		if name.startswith('_'):
			return super().__setattr__(name, value)

		value = self.__cast_item__(value)

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