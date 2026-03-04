import o


class Many(o.Object):

	def __init__(self, data, word):
		self.__id__ = o.services.Many.create(word)
		self.__cast_in__(data)
		self.__write__()

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS - ITEM-WISE
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
	def __cast_in_item__(self, value):
		if isinstance(value, o.Object):
			return value

		cls = self.__cast_map__.get(type(value))
		if cls is not None:
			return cls(value)

		raise TypeError(f'Unsupported cast type `{type(value).__name__}`')

	# Convert internal item back into Python value
	# ----------------------------------------------------------------------
	def __cast_out_item__(self, obj):
		py_type = self.__uncast_map__.get(obj.__type_id__)

		if py_type is not None:
			return obj.__cast_out__()

		return obj

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS - SELF-WISE
	# ======================================================================

	# Read full container state from storage
	# ----------------------------------------------------------------------
	def __read__(self):
		return o.services.Many.read(self.__id__)

	# Persist full container state to storage
	# ----------------------------------------------------------------------
	def __write__(self):
		return o.services.Many.write(self.__id__, self.__items__)

	# Clear all items from container
	# ----------------------------------------------------------------------
	def __clear__(self):
		return o.services.Many.clear(self.__id__)

	# Delete container from storage
	# ----------------------------------------------------------------------
	def __delete__(self):
		return o.services.Many.delete(self.__id__)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	@classmethod
	def bind(cls, id):
		obj = super().__new__(cls)

		obj.__id__ = id
		obj.__read__()

		return obj

	# ======================================================================
	# LIFECYCLE
	# ======================================================================

	# def __del__(self):
	# 	try:
	# 		instance_id = self.__dict__.get('__id__', None)
	# 		if instance_id is not None:
	# 			self.__delete__()
	# 			self.__id__ = None
	# 	except Exception:
	# 		pass
