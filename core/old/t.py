import operator, hashlib, types

import o

# ======================================================================
# CLASS T
# ======================================================================


class T(o.Module, metaclass=TMeta):

	# Subclass Instance factory
	# ----------------------------------------------------------------------
	def __new__(cls, *args, **kwargs):
		value = o.undefined

		# Check if single value is supplied
		# - - - - - - - - - - - - - - - - - -
		if len(args) == 1:
			value = args[0]
		elif len(args) > 1:
			raise TypeError(f'Too many positional arguments for `{cls.__o_module__}`')

		# In base class o.T
		# - - - - - - - - - - - - - - - - - -
		if cls is o.T:
			if kwargs: value = kwargs

			if value is o.undefined:
				raise TypeError('o.T(value) requires one root value')

			value_type = type(value)

			if isinstance(value, o.T):
				instance = value  # Passthrough
			else:
				if value_type in o.__cast_map__:
					value_cls = o.__cast_map__[value_type]
					instance  = object.__new__(value_cls)
				else:
					raise TypeError(
						f'Cannot cast `{value_type}` into `o.T`'
					)
		# Subclasses construct normally
		# - - - - - - - - - - - - - - - - - -
		else:
			instance = object.__new__(cls)

		return instance

	# Initialize type
	# ----------------------------------------------------------------------
	def __init__(self, value=o.undefined, **kwargs):
		self.__id__ = None

	# Delegate o-unrelated behavior to python type
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

			return attr

		raise AttributeError(name)

	# Representation
	# ----------------------------------------------------------------------
	def __repr__(self):
		cls     = self.__class__
		parent  = None
		t_found = False

		for base in cls.__mro__:
			if not t_found:
				if base is o.T:
					t_found = True
			else:
				if base is not o.T:
					parent = base
					break

		if parent:
			return f'<{self.__o_module__} ({parent.__o_module__}) id={self.__id__}>'
		return f'<{self.__o_module__} id={self.__id__}>'

	def __hash__(self):
		raise TypeError(f'Unhashable type `{self.__o_module__}`')

	# ======================================================================
	# OPERATOR OVERRIDES
	# ======================================================================

	def __binary_op__(self, op, other, reflected=False):
		base  = self.__cast_out__()
		other = other.__cast_out__() if isinstance(other, T) else other
		return op(other, base) if reflected else op(base, other)

	def __add__       (self, other): return self.__binary_op__( operator.add,      other       )
	def __radd__      (self, other): return self.__binary_op__( operator.add,      other, True )
	def __sub__       (self, other): return self.__binary_op__( operator.sub,      other       )
	def __rsub__      (self, other): return self.__binary_op__( operator.sub,      other, True )
	def __mul__       (self, other): return self.__binary_op__( operator.mul,      other       )
	def __rmul__      (self, other): return self.__binary_op__( operator.mul,      other, True )
	def __truediv__   (self, other): return self.__binary_op__( operator.truediv,  other       )
	def __rtruediv__  (self, other): return self.__binary_op__( operator.truediv,  other, True )
	def __floordiv__  (self, other): return self.__binary_op__( operator.floordiv, other       )
	def __rfloordiv__ (self, other): return self.__binary_op__( operator.floordiv, other, True )
	def __mod__       (self, other): return self.__binary_op__( operator.mod,      other       )
	def __rmod__      (self, other): return self.__binary_op__( operator.mod,      other, True )
	def __pow__       (self, other): return self.__binary_op__( operator.pow,      other       )
	def __rpow__      (self, other): return self.__binary_op__( operator.pow,      other, True )

	# UNARY OPERATORS
	# ----------------------------------------------------------------------

	def __neg__(self): return operator.neg( self.__cast_out__() )
	def __pos__(self): return operator.pos( self.__cast_out__() )
	def __abs__(self): return operator.abs( self.__cast_out__() )

	# COMPARISONS
	# ----------------------------------------------------------------------

	def __eq__(self, other): return self.__binary_op__( operator.eq, other )
	def __ne__(self, other): return self.__binary_op__( operator.ne, other )
	def __lt__(self, other): return self.__binary_op__( operator.lt, other )
	def __le__(self, other): return self.__binary_op__( operator.le, other )
	def __gt__(self, other): return self.__binary_op__( operator.gt, other )
	def __ge__(self, other): return self.__binary_op__( operator.ge, other )

	# CONTAINER PROTOCOL
	# ----------------------------------------------------------------------

	def __len__(self)            : return len(self.__cast_out__())
	def __iter__(self)           : return iter(self.__cast_out__())
	def __contains__(self, item) : return item in self.__cast_out__()
	def __getitem__(self, key)   : return self.__cast_out__()[key]

	def __setitem__(self, key, value):
		base = self.__cast_out__()
		base[key] = value
		self.__cast_in__(base)

	def __delitem__(self, key):
		base = self.__cast_out__()
		del base[key]
		self.__cast_in__(base)

	# TYPE CONVERSIONS
	# ----------------------------------------------------------------------

	def __int__   (self) : return int   (self.__cast_out__())
	def __float__ (self) : return float (self.__cast_out__())
	def __bool__  (self) : return bool  (self.__cast_out__())
	def __str__   (self) : return str   (self.__cast_out__())

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	def __cast_in__  (self): raise NotImplementedError  # Cast Python structure into internal container state
	def __cast_out__ (self): raise NotImplementedError  # Convert internal container state back into Python structure
	def __read__     (self): raise NotImplementedError  # Read full container state from storage
	def __write__    (self): raise NotImplementedError  # Persist full container state to storage
	def __delete__   (self): raise NotImplementedError  # Delete object from storage

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Define
	# ----------------------------------------------------------------------
	@classmethod
	def define(cls, type_name, annotation=None, **fields):
		o.Timer.start('o.T.define')

		if o[type_name] is not None:
			raise TypeError(f'Namespace `o.{type_name}` is occupied or type with this name exists')
			
		has_annotation = annotation is not None
		has_fields     = len(fields) > 0
		
		# Either annotation or fields, not both
		# - - - - - - - - - - - - - - - - - - - -
		if has_annotation == has_fields:
			raise ValueError(f'Either named fields or annotation can/must be provided')

		# Fields – o.Object
		# - - - - - - - - - - - - - - - - - - - -
		if has_fields:
			bases     = (o.Object,)
			namespace = {}

			for fname, f in fields.items():
				if isinstance(f, o.F):
					f.name = fname
					namespace[fname] = f
				else:
					namespace[fname] = o.F(
						name        = fname,
						type        = f,
						description = None,
						default     = o.undefined
					)

		# Annotation – not o.Object
		# - - - - - - - - - - - - - - - - - - - -
		else:
			bases      = (T, annotation)
			namespace  = { '__annotation__': o.Annotation(annotation) }

		# Create type
		# - - - - - - - - - - - - - - - - - - - -
		new_type = types.new_class(
			type_name,
			bases,
			{},
			lambda ns: ns.update(namespace),
		)

		o.Timer.stop('o.T.define')
		return new_type

	# Serialize
	# ----------------------------------------------------------------------
	@classmethod
	def serialize(cls):
		fields = []
		annotation = getattr(cls, '__annotation__', None)

		if hasattr(cls, '__fields__') and cls.__fields__:
			fields = [
				field.serialize()
				for field in cls.__fields__.values()
			]

		if annotation is not None and not getattr(annotation, 'is_none', False):
			annotation = str(annotation)
		else:
			annotation = None

		return dict(
			type_name  = cls.__name__,
			annotation = annotation,
			fields     = fields,
			o_module   = cls.__o_module__,
		)
