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

		o.Timer.stop('o.TMeta.__new__')
		return cls
