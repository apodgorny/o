import o


class Many(o.T):

	# Constructor
	# ----------------------------------------------------------------------
	def __init__(self, data, word):
		if not isinstance(data, o.T):
			self.__word__ = word
			self.__id__   = None

			if data != o.undefined:
				self.__cast_in__(data)
				self.__id__ = self.__write__()

	# # Delete container on object finalization
	# # ----------------------------------------------------------------------
	# def __del__(self):
	# 	try:
	# 		instance_id = self.__dict__.get('__id__', None)
	# 		if instance_id is not None:
	# 			self.__delete__()
	# 			self.__id__ = None
	# 	except Exception as e:
	# 		print('WARNING', e)

	# Delete container on object finalization
	# ----------------------------------------------------------------------
	def __del__(self):
		try:
			instance_id = self.__dict__.get('__id__', None)

			if instance_id is not None:
				self.__delete__()
		except Exception as e:
			print('WARNING', e)

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
	def __cast_in_item__(self, value, reuse_item=None):
		item = value

		if not isinstance(value, o.T):
			cls = o.__cast_map__.get(type(value))
			if cls is None:
				raise TypeError(f'Unsupported cast type `{type(value).__name__}`')

			if reuse_item is not None and isinstance(reuse_item, cls):
				reuse_item.__cast_in__(value)
				item = reuse_item
			else:
				item = cls(value)

		return item

	# Convert internal item back into Python value
	# ----------------------------------------------------------------------
	def __cast_out_item__(self, obj):
		value = obj

		if isinstance(obj, o.Many):
			if isinstance(obj, o.Str):
				value = obj.__cast_out__()
		else:
			value = obj.__cast_out__()

		return value

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
		id             = self.__id__
		is_new         = id is None
		is_custom_type = not self.__class__.__has_own_module__

		if id is None:
			id = o.services.Many.create(self.__word__)

		o.services.Many.write(id, self.__items__)

		if is_new:
			o.__instances_by_id__[(self.__type_id__, id)] = self

		if is_new and is_custom_type:
			o.services.Definition.inc_count(self.__type_id__)

		return id

	# Clear all items from container
	# ----------------------------------------------------------------------
	def __clear__(self):
		return o.services.Many.clear(self.__id__)

	# Delete instance, if count instances zero – remove type 
	# ----------------------------------------------------------------------
	# def __delete__(self):
	# 	is_custom_type = not self.__class__.__has_own_module__
	# 	result         = o.services.Many.delete(self.__id__)

	# 	if result and is_custom_type:
	# 		count = o.services.Definition.dec_count(self.__type_id__)
	# 		if count == 0:
	# 			o.services.Definition.undefine(self.__type_id__)
	# 	return result


	# Delete persistent container
	# ----------------------------------------------------------------------
	def __delete__(self):
		id             = self.__dict__.get('__id__', None)
		result         = False
		is_custom_type = not self.__class__.__has_own_module__

		if id is not None:
			result = o.services.Many.delete(id)

			if result and is_custom_type:
				count = o.services.Definition.dec_count(self.__type_id__)
				if count == 0:
					o.services.Definition.undefine(self.__type_id__)

			self.__id__ = None

		return result

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Bind existing container by id
	# ----------------------------------------------------------------------
	@classmethod
	def instantiate(cls, id):
		obj = o.__instances_by_id__.get((cls.__type_id__, id))
		if obj is not None and obj.__dict__.get('__id__', None) == id:
			return obj

		obj = super().__new__(cls)

		obj.__id__ = id
		obj.__read__()

		return obj

	
