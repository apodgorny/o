import operator, hashlib

import o


class Object(o.Module):

	__cast_map__    = {}  # python_type → o_class
	__uncast_map__  = {}  # type_id     → python_type
	__python_type__ = None

	# ----------------------------------------------------------------------
	def __init__(self):
		self.__id__   = None
		self.__data__ = None

	# ----------------------------------------------------------------------
	def __init_subclass__(cls, **kwargs):
		super().__init_subclass__(**kwargs)

		h = hashlib.sha256(cls.__o_module__.encode()).digest()
		cls.__type_id__ = int.from_bytes(h[:8], 'little', signed=False)

		if cls.__type_id__ in o.types:
			raise RuntimeError(f'duplicate type_id `{cls.__type_id__}`')

		o.types[cls.__type_id__] = cls

		if cls.__python_type__ is not None:
			Object.__cast_map__[cls.__python_type__] = cls
			Object.__uncast_map__[cls.__type_id__]   = cls.__python_type__
		
	# ----------------------------------------------------------------------
	def __repr__(self):
		return f'<{self.__o_module__} id={self.__id__}>'

	# ----------------------------------------------------------------------
	# FALLBACK FOR NORMAL METHODS
	# ----------------------------------------------------------------------

	def __getattr__(self, name):
		base = self.__cast__()

		if hasattr(base, name):
			attr = getattr(base, name)

			if callable(attr):
				def wrapper(*args, **kwargs):
					result = attr(*args, **kwargs)
					self.__uncast__(base)
					return result
				return wrapper

			return attr

		raise AttributeError(name)

	# ------------------------------------------------------------
	# CORE CAST BRIDGE
	# ------------------------------------------------------------

	def __cast__(self):
		return self.__read__()

	def __uncast__(self, value):
		self.__write__(value)

	def __coerce_other__(self, other):
		return other.__cast__() if isinstance(other, Object) else other


	# ------------------------------------------------------------
	# BINARY OPERATORS
	# ------------------------------------------------------------

	def __binary_op__(self, op, other, reflected=False):
		base  = self.__cast__()
		other = self.__coerce_other__(other)

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


	# ------------------------------------------------------------
	# UNARY OPERATORS
	# ------------------------------------------------------------

	def __neg__(self): return operator.neg(self.__cast__())
	def __pos__(self): return operator.pos(self.__cast__())
	def __abs__(self): return operator.abs(self.__cast__())


	# ------------------------------------------------------------
	# COMPARISONS
	# ------------------------------------------------------------

	def __eq__(self, other): return self.__binary_op__(operator.eq, other)
	def __ne__(self, other): return self.__binary_op__(operator.ne, other)
	def __lt__(self, other): return self.__binary_op__(operator.lt, other)
	def __le__(self, other): return self.__binary_op__(operator.le, other)
	def __gt__(self, other): return self.__binary_op__(operator.gt, other)
	def __ge__(self, other): return self.__binary_op__(operator.ge, other)


	# ------------------------------------------------------------
	# CONTAINER PROTOCOL
	# ------------------------------------------------------------

	def __len__(self):
		return len(self.__cast__())

	def __iter__(self):
		return iter(self.__cast__())

	def __contains__(self, item):
		return item in self.__cast__()

	def __getitem__(self, key):
		return self.__cast__()[key]

	def __setitem__(self, key, value):
		base = self.__cast__()
		base[key] = value
		self.__uncast__(base)

	def __delitem__(self, key):
		base = self.__cast__()
		del base[key]
		self.__uncast__(base)


	# ------------------------------------------------------------
	# TYPE CONVERSIONS
	# ------------------------------------------------------------

	def __int__(self): return int(self.__cast__())
	def __float__(self): return float(self.__cast__())
	def __bool__(self): return bool(self.__cast__())
	def __str__(self): return str(self.__cast__())
