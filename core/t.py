import operator, hashlib, types

import o

class TMeta(type(o.Module)):

	# Enable getting dynamic types with o.T['MyClass']
	# ----------------------------------------------------------------------
	def __getitem__(cls, name):
		value    = None
		o_module = None
		type_id  = None

		# Getting dynamic type
		# - - - - - - - - - - - - - - - - - - - -
		if cls is o.T and isinstance(name, str):
			o_module = f'{cls.__o_module__}.{name}'

			# From cache
			# - - - - - - - - - - - - - - - - - - - -
			if o_module in o.__types_by_name__:
				value = o.__types_by_name__[o_module]

			# Redefining and storing to cache
			# - - - - - - - - - - - - - - - - - - - -
			else:
				type_id  = cls.__class__.__hash_type_id__(o_module)
				value    = o.services.Definition.get(type_id)
				o.__types_by_name__[o_module] = value
		else:
			value = super().__getitem__(name)

		return value

	# Enable getting dynamic types with o.T.MyClass
	# ----------------------------------------------------------------------
	def __getattr__(cls, name):
		value = None

		if not name.startswith('_') and cls is o.T:
			try:
				value = cls[name]
			except FileNotFoundError:
				raise AttributeError(name)
		else:
			value = super().__getattr__(name)

		return value

	# Collect class fields
	# ----------------------------------------------------------------------
	@classmethod
	def __collect_fields__(mcls, namespace):
		fields      = {}
		annotations = namespace.get('__annotations__', {})

		# Add fields declared as annotation
		# - - - - - - - - - - - - - - - - - - - -
		for name, ftype in annotations.items():
			default = o.undefined

			if name in namespace:
				default = namespace[name]
				del namespace[name]

			fields[name] = o.F(
				name        = name,
				type        = ftype,
				description = None,
				default     = default,
			)
		
		# Add fields declared as o.F
		# - - - - - - - - - - - - - - - - - - - -
		for name, value in list(namespace.items()):
			if isinstance(value, o.F):
				value.name   = name
				fields[name] = value
				del namespace[name]

		return fields

	# Normalize bases – second baseclass can be python annotation
	# ----------------------------------------------------------------------
	@classmethod
	def __cast__(mcls, annotation):
		base_type  = o.__cast_map__.get(annotation.origin)
		if base_type is None:
			raise ValueError(f'Annotation `{annotation.__name__}` is not castable to `o.T`')
		return base_type

	# Generate unique type id hash
	# ----------------------------------------------------------------------
	@classmethod
	def __hash_type_id__(mcls, o_module):
		hashed = hashlib.sha256(o_module.encode()).digest()
		return int.from_bytes(hashed[:4], 'little', signed=False)

	# Generate unique type id hash, if not unique – raise
	# ----------------------------------------------------------------------
	@classmethod
	def __get_type_id__(mcls, o_module):
		type_id = mcls.__hash_type_id__(o_module)

		if type_id in o.__types_by_id__:
			raise RuntimeError(f'Type `{o_module}` already exists.')

		return type_id

	# Create new type
	# ----------------------------------------------------------------------
	def __new__(mcls, name, bases, namespace, **kwargs):
		o.Timer.start('o.T.__init_subclass__')

		# Accept second baseclass (annotation)
		# Enable cool things like: class Users(o.T, list[o.User]): pass
		# - - - - - - - - - - - - - - - - - - - -
		if len(bases) > 1:
			annotation = namespace.get('__annotation__', o.Annotation(bases[1]))
			namespace['__annotation__'] = annotation
			bases = (mcls.__cast__(annotation),)

		# Collect field declarations
		# - - - - - - - - - - - - - - - - - - - -
		else:
			fields = mcls.__collect_fields__(namespace)
			namespace['__annotations__'] = {}
			namespace['__fields__']      = fields

			if len(fields) > 0 and bases == (o.T,):
				bases = (o.Object,)
		
		# cls.__annotation__ -> o.Annotation
		# - - - - - - - - - - - - - - - - - - - -
		if '__annotation__' in namespace:
			annotation = o.Annotation(namespace['__annotation__'])
			namespace['__annotation__'] = annotation

		# Create type
		# - - - - - - - - - - - - - - - - - - - -
		cls = super().__new__(mcls, name, bases, namespace)
		if not cls.__has_own_module__:
			cls.__o_module__ = f'o.T.{name}'

		o_module = cls.__o_module__
		type_id  = mcls.__get_type_id__(o_module)
		cls.__type_id__ = type_id

		# cls.__annotation__ -> o.Annotation
		# - - - - - - - - - - - - - - - - - - - -
		if hasattr(cls, '__annotation__'):
			annotation = o.Annotation(cls.__annotation__)
			cls.__annotation__ = annotation

			# Register type in o.__cast_map__ ONCE
			# - - - - - - - - - - - - - - - - - - - -
			if annotation.origin not in o.__cast_map__:
				o.__cast_map__[annotation.origin] = cls

		# Register type in o.__types_by_id__
		# - - - - - - - - - - - - - - - - - - - -
		o.__types_by_id__   [type_id]  = cls
		o.__types_by_name__ [o_module] = cls

		if not cls.__has_own_module__:
			o.services.Definition.define(cls)

		o.Timer.stop('o.T.__init_subclass__')
		return cls


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

		if annotation is not None:
			annotation = str(annotation)

		return dict(
			type_name  = cls.__name__,
			annotation = annotation,
			fields     = fields,
			o_module   = cls.__o_module__,
		)
