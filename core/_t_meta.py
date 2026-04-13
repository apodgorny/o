import operator, types

import o

class TMeta(type(o.Module)):

	# Enable getting dynamic types with o.T['MyClass']
	# ----------------------------------------------------------------------
	def __getitem__(cls, name):
		value    = None
		o_module = None

		# Getting dynamic type
		# - - - - - - - - - - - - - - - - - - - -
		if cls is o.T and isinstance(name, str):
			o_module = f'{cls.__o_module__}.{name}'
			value    = o.__types_by_name__[o_module]
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
			except LookupError:
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

	# Create new type
	# ----------------------------------------------------------------------
	def __new__(mcls, name, bases, namespace, **kwargs):
		o.Timer.start('o.TMeta.__new__')

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

		# cls.__annotation__ -> o.Annotation
		# - - - - - - - - - - - - - - - - - - - -
		if hasattr(cls, '__annotation__'):
			annotation = o.Annotation(cls.__annotation__)
			cls.__annotation__ = annotation

			# Register type in o.__cast_map__ ONCE
			# - - - - - - - - - - - - - - - - - - - -
			if annotation.origin not in o.__cast_map__:
				o.__cast_map__[annotation.origin] = cls

		o.__types_by_name__[cls.__o_module__] = cls

		o.Timer.stop('o.TMeta.__new__')
		return cls

# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

class T(o.Module, metaclass=TMeta):

	# Resolve class instance by local numeric index
	# ----------------------------------------------------------------------
	@classmethod
	def __class_getitem__(cls, n):
		id = cls.__instances__[n]
		return cls.embody(id)

	# Subclass T factory
	# ----------------------------------------------------------------------
	def __new__(cls, *args, **kwargs):
		value = o.undefined

		# Single value o.MyType(foo)
		# - - - - - - - - - - - - - - - - - -
		if len(args) == 1:
			value = args[0]
		elif len(args) > 1:
			raise TypeError(f'Too many positional arguments for `{cls.__o_module__}`')

		# In base class o.T
		# - - - - - - - - - - - - - - - - - -
		if cls is o.T:
			if kwargs:
				value = kwargs

			if value is o.undefined:
				raise TypeError('o.T(value) requires one root value')

			value_type = type(value)

			if isinstance(value, o.T):
				instance = value
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

		if not hasattr(instance, '__id__'):
			instance.__id__ = o.services.Store.create()
			o.__instances_by_id__[instance.__id__] = instance

		return instance

	# Read store and restore internal state
	# ----------------------------------------------------------------------
	def __read__(self):

		# Read internal state from disk
		# - - - - - - - - - - - - - - - - - -
		(
			self.__o_module__,
			attributes,
			self.__idx_to_ref__,
			self.__key_to_ref__,
			self.__proto_parent__,
			self.__proto_children__,
			self.__value__,
		) = o.services.Store.read(self.__id__)

		# Set attributes to object from dict
		# - - - - - - - - - - - - - - - - - -
		for key, ref in attributes.items():
			setattr(self, key, ref)

	# Write internal state to store
	# ----------------------------------------------------------------------
	def __write__(self):

		# Collect attributes into dict
		# - - - - - - - - - - - - - - - - - -
		attributes = {
			key:ref
			for key, ref in vars(self).items()
			if not key.startswith('_')
		}

		# Write internal state to disk
		# - - - - - - - - - - - - - - - - - -
		o.services.Store.write(
			self.__id__,
			o_module       = self.__o_module__,
			attributes     = attributes,
			list_items     = getattr(self, '__idx_to_ref__', []),
			dict_items     = getattr(self, '__key_to_ref__', {}),
			proto_parent   = getattr(self, '__proto_parent__', None),
			proto_children = getattr(self, '__proto_children__', []),
			value          = getattr(self, '__value__', None),
		)

	# Cast external data into internal state and write to disk
	# ----------------------------------------------------------------------
	def __cast_in__(self, data):
		raise NotImplementedError

	# Cast internal state into python object
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		raise NotImplementedError

	# Load canonical T wrapper by id
	# ----------------------------------------------------------------------
	@classmethod
	def embody(cls, id):
		instance = o.__instances_by_id__.get(id)

		if not o.services.Store.exists(id):
			raise RuntimeError(f'No instance exists for `{cls.__o_module__}`[{id}]')

		o_module, _, _, _, _, _, _ = o.services.Store.read(id)

		if o_module != cls.__o_module__:
			raise RuntimeError(
				f'Cannot embody `{cls.__o_module__}`[{id}]: id belongs to `{o_module}`'
			)

		instance = object.__new__(cls)
		instance.__id__ = id
		instance.__read__()

		o.__instances_by_id__[id] = instance

		return instance

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


def embody(id):
	instance = o.__instances_by_id__.get(id)

	if isinstance is None:
		if not o.services.Store.exists(id):
			raise RuntimeError(f'No instance exists for `o.T`[{id}]')

		# Read from disk
		# - - - - - - - - - - - - - - - - - -
		(
			o_module,
			attributes,
			idx_to_ref,
			key_to_ref,
			proto_parent,
			proto_children,
			value,
		) = o.services.Store.read(id)

		cls = eval(o_module)
		cls.__id__             = id
		cls.__o_module__       = o_module,
		cls.__idx_to_ref__     = idx_to_ref,
		cls.__key_to_ref__     = key_to_ref,
		cls.__proto_parent__   = proto_parent,
		cls.__proto_children__ = proto_children,
		cls.__value__          = value,

	o.__instances_by_id__[id] = instance

	return instance
