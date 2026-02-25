import o


class Many(o.Object):

	def __init__(self, word, id=None, data=None):
		if id is None and data is None:
			raise RuntimeError('Data and id can not both be None')

		self.__type_id__ = 0
		self.__id__      = o.services.Many.create(word) if id is None else id

		if data is None:
			self.__items__, self.__index__ = self.__read__()
		else:
			self.__items__, self.__index__ = self.__cast__(data)
			self.__write__()

	# ======================================================================
	# Item-Wise Methods
	# ======================================================================

	# Access single item by accessor
	# ----------------------------------------------------------------------
	def __get__(self, accessor):
		raise NotImplementedError

	# Insert or update single item in container
	# ----------------------------------------------------------------------
	def __set__(self, accessor, type_id, item_id, insert=False):
		raise NotImplementedError

	# Remove single item from container
	# ----------------------------------------------------------------------
	def __unset__(self, accessor):
		raise NotImplementedError

	# Cast Python item value into internal item representation
	# ----------------------------------------------------------------------
	def __cast_item__(self, value):
		if isinstance(value, o.Object):
			return value

		cls = o.Object.__cast_map__.get(type(value))
		if cls is not None:
			return cls(data=value)

		raise TypeError(f'Unsupported cast type `{type(value).__name__}`')

	# Convert internal item back into Python value
	# ----------------------------------------------------------------------
	def __uncast_item__(self, obj):
		py_type = o.Object.__uncast_map__.get(obj.__type_id__)

		if py_type is not None:
			return obj.__uncast__()

		return obj

	# ======================================================================
	# Object-Wise Methods
	# ======================================================================

	# Read full container state from storage
	# ----------------------------------------------------------------------
	def __read__(self):
		return o.services.Many.read(self.__id__), {}

	# Persist full container state to storage
	# ----------------------------------------------------------------------
	def __write__(self):
		return o.services.Many.write(self.__id__, self.__items__)

	# Cast Python structure into internal container state
	# ----------------------------------------------------------------------
	def __cast__(self):
		raise NotImplementedError

	# Convert internal container state back into Python structure
	# ----------------------------------------------------------------------
	def __uncast__(self):
		raise NotImplementedError

	# Clear all items from container
	# ----------------------------------------------------------------------
	def __clear__(self):
		return o.services.Many.clear(self.__id__)

	# Delete container from storage
	# ----------------------------------------------------------------------
	def __delete__(self):
		return o.services.Many.delete(self.__id__)

	# Flush pending changes to storage
	# ----------------------------------------------------------------------
	def __commit__(self):
		return o.services.Many.commit()