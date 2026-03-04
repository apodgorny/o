import o


class One(o.Object):

	def __init__(self, data, word):
		o.services.One.define(self.__o_module__, self.__type_id__, word)
		instance_id = self.__id__ if '__id__' in self.__dict__ else None

		self.__id__ = o.services.One.write(
			self.__type_id__,
			instance_id,
			data
		)

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS
	# ======================================================================

	# Cast Python structure into internal container state
	# ----------------------------------------------------------------------
	def __cast_in__(self, value):
		if self.__python_type__ is None:
			raise AttributeError(f'{self.__o_module__}.__python_type__ is not defined')

		value = self.__python_type__(value)	
		return self.__write__(value)

	# Convert internal container state back into Python structure
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		if self.__python_type__ is None:
			raise AttributeError(f'{self.__o_module__}.__python_type__ is not defined')
		
		value = self.__read__()
		return self.__python_type__(value)

	def __read__(self):
		return o.services.One.read(self.__type_id__, self.__id__)

	def __write__(self, data):
		return o.services.One.write(self.__type_id__, self.__id__, data)

	def __delete__(self):
		return o.services.One.delete(self.__type_id__, self.__id__)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	@classmethod
	def bind(cls, id):
		obj = super().__new__(cls)
		obj.__id__ = id
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