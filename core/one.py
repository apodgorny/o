import o


class One(o.T):

	# Constructor
	# ----------------------------------------------------------------------
	def __init__(self, data, word):
		if not isinstance(data, o.T):
			o.services.One.define(self.__o_module__, self.__type_id__, word)

			if '__id__' not in self.__dict__:
				self.__id__ = None

			self.__id__ = self.__cast_in__(data)

	# Destructor
	# ----------------------------------------------------------------------
	def __del__(self):
		try:
			instance_id = self.__dict__.get('__id__', None)
			if instance_id is not None:
				self.__delete__()
				self.__id__ = None
		except Exception:
			pass

	# Hash
	# ----------------------------------------------------------------------
	def __hash__(self):
		return hash(self.__cast_out__())

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS
	# ======================================================================

	# Cast Python structure into internal container state
	# ----------------------------------------------------------------------
	def __cast_in__(self, value):
		if self.__annotation__.is_none:
			raise AttributeError(f'{self.__o_module__}.__annotation__ is not defined')

		value = self.__annotation__.cast(value)	
		return self.__write__(value)

	# Convert internal container state back into Python structure
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		if self.__annotation__ is None:
			raise AttributeError(f'{self.__o_module__}.__annotation__ is not defined')
		
		value = self.__read__()
		return self.__annotation__.cast(value)

	# Read from disk
	# ----------------------------------------------------------------------
	def __read__(self):
		return o.services.One.read(self.__type_id__, self.__id__)

	# Write to disk
	# ----------------------------------------------------------------------
	def __write__(self, data):
		id, type_id    = self.__id__, self.__type_id__
		is_new         = id is None
		is_custom_type = not self.__class__.__has_own_module__

		id = o.services.One.write(type_id, id, data)

		if is_new:
			o.__instances__[(type_id, id)] = self

		if is_new and is_custom_type:
			o.services.Definition.inc_count(type_id)

		return id

	# Delete instance, if count instances zero – remove type
	# ----------------------------------------------------------------------
	def __delete__(self):
		id, type_id    = self.__id__, self.__type_id__
		result         = o.services.One.delete(type_id, id)
		is_custom_type = not self.__class__.__has_own_module__

		if result and is_custom_type:
			count = o.services.Definition.dec_count(type_id)
			if count == 0:
				o.services.Definition.undefine(type_id)
		return result

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Create instance for id
	# ----------------------------------------------------------------------
	@classmethod
	def instantiate(cls, id):
		obj = o.__instances__.get((cls.__type_id__, id))
		if obj is not None and obj.__dict__.get('__id__', None) == id:
			return obj

		obj = super().__new__(cls)
		obj.__id__ = id
		return obj
