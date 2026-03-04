import operator, hashlib

import o


class Object(o.Module):

	__cast_map__    = {}  # python_type → o_class
	__uncast_map__  = {}  # type_id     → python_type
	__python_type__ = None

	# Register type
	# ----------------------------------------------------------------------
	@classmethod
	def register(cls):
		cls.__o_module__ = f'o.T.{cls.__name__}'

		# Produce hash id from class name
		# - - - - - - - - - - - - - - - - - - - -
		hashed   = hashlib.sha256(cls.__o_module__.encode()).digest()
		type_id  = int.from_bytes(hashed[:2], 'little', signed=False)
		existing = o.types.get(type_id)

		# Type does not exist
		# - - - - - - - - - - - - - - - - - - - -
		if existing is None:
			o.types[type_id] = cls
			cls.__type_id__  = type_id

			# Add python_type to cast/uncast maps
			# - - - - - - - - - - - - - - - - - - - -
			if cls.__python_type__ is not None:
				Object.__cast_map__[cls.__python_type__] = cls
				Object.__uncast_map__[type_id]           = cls.__python_type__

		# Type already exists
		# - - - - - - - - - - - - - - - - - - - -
		else:
			if existing is not cls:
				raise RuntimeError(f'Type `{o.types[type_id].__o_module__}` already exists.')

	# Representation
	# ----------------------------------------------------------------------
	def __repr__(self):
		return f'<{self.__o_module__} id={self.__id__}>'

	# Get Attribute
	# ----------------------------------------------------------------------

	def __getattr__(self, name):
		if name.startswith('__'):
			raise AttributeError(name)
			
		base = self.__cast_out__()

		if hasattr(base, name):
			attr = getattr(base, name)

			if callable(attr):
				def wrapper(*args, **kwargs):
					result = attr(*args, **kwargs)
					self.__cast_in__(base)
					return result
				return wrapper
			# TODO: Implement this with respect to refcounts

			return attr

		raise AttributeError(name)

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS
	# ======================================================================

	# Increment refcount
	# ----------------------------------------------------------------------
	def __inc_refcount__(self):
		raise NotImplementedError

	# Decrement refcount
	# ----------------------------------------------------------------------
	def __dec_refcount__(self):
		raise NotImplementedError

	# Cast Python structure into internal container state
	# ----------------------------------------------------------------------
	def __cast_in__(self):
		raise NotImplementedError

	# Convert internal container state back into Python structure
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		raise NotImplementedError

	# Read full container state from storage
	# ----------------------------------------------------------------------
	def __read__(self):
		raise NotImplementedError

	# Persist full container state to storage
	# ----------------------------------------------------------------------
	def __write__(self):
		raise NotImplementedError

	# Delete object from storage
	# ----------------------------------------------------------------------
	def __delete__(self):
		raise NotImplementedError

	# ======================================================================
	# OPERATOR OVERRIDES
	# ======================================================================

	def __binary_op__(self, op, other, reflected=False):
		base  = self.__cast_out__()
		other = other.__cast_out__() if isinstance(other, Object) else other

		if reflected:
			return op(other, base)
		return op(base, other)


	def __add__(self, other): return self.__binary_op__(operator.add, other)
	def __radd__(self, other): return self.__binary_op__(operator.add, other, True)

	def __sub__(self, other): return self.__binary_op__(operator.sub, other)
	def __rsub__(self, other): return self.__binary_op__(operator.sub, other, True)

	def __mul__(self, other): return self.__binary_op__(operator.mul, other)
	def __rmul__(self, other): return self.__binary_op__(operator.mul, other, True)

	def __truediv__(self, other): return self.__binary_op__(operator.truediv, other)
	def __rtruediv__(self, other): return self.__binary_op__(operator.truediv, other, True)

	def __floordiv__(self, other): return self.__binary_op__(operator.floordiv, other)
	def __rfloordiv__(self, other): return self.__binary_op__(operator.floordiv, other, True)

	def __mod__(self, other): return self.__binary_op__(operator.mod, other)
	def __rmod__(self, other): return self.__binary_op__(operator.mod, other, True)

	def __pow__(self, other): return self.__binary_op__(operator.pow, other)
	def __rpow__(self, other): return self.__binary_op__(operator.pow, other, True)


	# UNARY OPERATORS
	# ----------------------------------------------------------------------

	def __neg__(self): return operator.neg(self.__cast_in__())
	def __pos__(self): return operator.pos(self.__cast_in__())
	def __abs__(self): return operator.abs(self.__cast_in__())


	# COMPARISONS
	# ----------------------------------------------------------------------

	def __eq__(self, other): return self.__binary_op__(operator.eq, other)
	def __ne__(self, other): return self.__binary_op__(operator.ne, other)
	def __lt__(self, other): return self.__binary_op__(operator.lt, other)
	def __le__(self, other): return self.__binary_op__(operator.le, other)
	def __gt__(self, other): return self.__binary_op__(operator.gt, other)
	def __ge__(self, other): return self.__binary_op__(operator.ge, other)


	# CONTAINER PROTOCOL
	# ----------------------------------------------------------------------

	def __len__(self):
		return len(self.__cast_out__())

	def __iter__(self):
		return iter(self.__cast_out__())

	def __contains__(self, item):
		return item in self.__cast_out__()

	def __getitem__(self, key):
		return self.__cast_out__()[key]

	def __setitem__(self, key, value):
		base = self.__cast_in__()
		base[key] = value
		self.__cast_out__(base)

	def __delitem__(self, key):
		base = self.__cast_in__()
		del base[key]
		self.__cast_out__(base)


	# TYPE CONVERSIONS
	# ----------------------------------------------------------------------

	def __int__   (self) : return int   (self.__cast_out__())
	def __float__ (self) : return float (self.__cast_out__())
	def __bool__  (self) : return bool  (self.__cast_out__())
	def __str__   (self) : return str   (self.__cast_out__())
