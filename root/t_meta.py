import uuid

import o

UNDEFINED = o.Undefined


class TMeta(type(o.Module)):

	# ======================================================================
	# METACLASS METHODS
	# ======================================================================

	# Create new type
	# ----------------------------------------------------------------------
	def __new__(mcls, name, bases, namespace, **kwargs):
		o.Timer.start('o.TMeta.__new__')

		is_runtime_defined   = namespace.get('__is_runtime_defined__', False)
		has_own_module       = False if is_runtime_defined else mcls.has_own_module(namespace)
		is_root_t            = name == 'T' and len(bases) == 1 and bases[0] is o.Module
		is_runtime_class_def = not is_runtime_defined and not has_own_module
		is_temp              = o.is_temp_class_name(name)

		# Prevent class definitions in runtime
		# - - - - - - - - - - - - - - - - - - - - - - - - -
		if is_runtime_class_def:
			raise TypeError(
				'Class definitions can only be loaded from o.Module. Use o.T.extend() instead.'
			)

		# Class naming convention
		# - - - - - - - - - - - - - - - - - - - - - - - - -
		if not name[0].isupper() and not name.startswith('__temp_'):
			raise NameError(f'Class name must start with uppercase letter: `{name}`')

		# Temp classes can not become public form parents
		# - - - - - - - - - - - - - - - - - - - - - - - - -
		for base_cls in bases:
			if isinstance(base_cls, type) and getattr(base_cls, '__is_temp__', False):
				raise TypeError(f'Temp class `{base_cls.__proto__}` can not be subclassed')

		# Support annotation definition only for o.T base
		# - - - - - - - - - - - - - - - - - - - - - - - - -
		if len(bases) > 1:
			if bases[0] is o.T:
				orig_bases = namespace.get('__orig_bases__', bases)
				annotation = orig_bases[1]
				bases      = (mcls.__embody__(annotation),)
			else:
				raise TypeError('Only o.T can accept annotation as second base class')

		# Process fields
		# - - - - - - - - - - - - - - - - - - - - - - - - -
		fields, namespace = mcls.__define__(namespace)
		cls = super().__new__(mcls, name, bases, namespace)

		# Resolve proto
		# - - - - - - - - - - - - - - - - - - - - - - - - -
		proto = 'o.T' if is_root_t else f'{cls.__parent__.__proto__}.{name}'
		zone  = o.services.Memory.zone(f'{proto}.')

		with o.services.Memory.read() as memory:
			version = zone.get('__version__', 0)

		cls.__module__         = 'o'
		cls.__has_own_module__ = has_own_module
		cls.__proto__          = proto
		cls.__is_temp__        = is_temp
		cls.__version__        = version
		cls.id                 = o.proto_to_id(proto)
		cls.__zone__           = zone
		cls._                  = o.Accessor(cls, ['_'])

		if not has_own_module:
			cls.__route__ = UNDEFINED
			cls.__mtime__ = UNDEFINED

		# Write class facts
		# - - - - - - - - - - - - - - - - - - - - - - - - -

		mcls.__bind_annotation__(cls)
		mcls.__write__(cls, fields)

		cls.__class__.__publish__(cls)

		o.register_entity(cls)

		if is_temp:
			o.services.Garbage.on_class_create(cls)

		o.Timer.stop('o.TMeta.__new__')
		return cls

	# Call type
	# ----------------------------------------------------------------------
	def __call__(cls, __value__=UNDEFINED, **kwargs):
		self = cls.__new__(cls, __value__, **kwargs)

		if self is not __value__:
			if __value__ is UNDEFINED:
				super().__call__(**kwargs)
			else:
				self.__init__(__value__)

		return self

	# Load and return subclasses
	# ----------------------------------------------------------------------
	def __subclasses__(cls):
		result = type.__subclasses__(cls)

		if hasattr(cls, '__proto__'):
			names = set()

			for key in cls.__zone__.keys():
				name = key.split('.')[0]

				if o.is_class_name(name):
					names.add(name)

			for name in names:
				getattr(cls, name)

			result = type.__subclasses__(cls)

		return result

	# Resolve nearest public parent
	# ----------------------------------------------------------------------
	@property
	def __parent__(cls):
		parent = None

		for base_cls in cls.__mro__[1:]:
			if '__proto__' in base_cls.__dict__:
				parent = base_cls
				break

		return parent

	# Set Python class definition from field declarations
	# ----------------------------------------------------------------------
	@classmethod
	def __define__(mcls, namespace):
		annotations = namespace.get('__annotations__', {})
		fields      = {}

		# Collect fields from annotation
		# - - - - - - - - - - - - - - - - - - - -
		if annotations:
			del namespace['__annotations__']
			for name, annotation in annotations.items():
				type_id = mcls.__embody__(annotation).id
				default = namespace.get(name, UNDEFINED)

				fields[name] = {
					'type'    : type_id,
					'default' : default,
				}

				if name in namespace:
					del namespace[name]

		# Collect fields from namespace
		# - - - - - - - - - - - - - - - - - - - -
		for name, field in list(namespace.items()):
			if not name.startswith('_'):

				# Add fields declared as o.F
				# - - - - - - - - - - - - - - - - - - - -
				if isinstance(field, o.F):
					type_id = mcls.__embody__(field.type).id

					fields[name] = {
						'type'    : type_id,
						'default' : field.default,
						**field.props,
					}

					del namespace[name]

				# Add fields declared as 'key = int' in extend
				# - - - - - - - - - - - - - - - - - - - -
				elif o.Annotation.is_annotation(field):
					type_id = mcls.__embody__(field).id

					fields[name] = {
						'type'    : type_id,
						'default' : UNDEFINED,
					}

					del namespace[name]

		return fields, namespace

	# ======================================================================
	# CLASS METHODS
	# ======================================================================

	# Create classes for nested annotation
	# ----------------------------------------------------------------------
	@classmethod
	def __embody__(mcls, annotation):
		if isinstance(annotation, type) and issubclass(annotation, o.T):
			cls = annotation
		else:
			annotation = o.Annotation(annotation)
			cls        = o.__cast_map__.get(annotation.annotation)

			if cls is None:
				base_cls     = o.__cast_map__[annotation.origin]
				visible_args = []

				if not annotation.args:
					cls = base_cls
				else:
					for arg in annotation.args:
						arg_cls        = mcls.__embody__(arg)
						arg_annotation = getattr(arg_cls, '__annotation__', UNDEFINED)
						visible_arg    = arg_cls

						if arg_annotation is not UNDEFINED and arg_annotation.is_simple:
							visible_arg = arg_annotation.annotation

						visible_args.append(visible_arg)

					namespace = {
						'__annotation__': annotation.origin[*visible_args],
						'__is_runtime_defined__': True,
					}

					cls = mcls.__new__(mcls, f'Generic_{hash(annotation)}', (base_cls,), namespace)

				o.__cast_map__[annotation.annotation] = cls

		return cls

	# Read class from memory by name
	# ----------------------------------------------------------------------
	@classmethod
	def __read__(mcls, cls, name):
		entity = None
		proto  = f'{cls.__proto__}.{name}'
		route  = o.proto_to_route(proto)

		if route is not UNDEFINED:
			entity = eval(route)
		else:
			entity = mcls.__new__(
				mcls,
				name,
				(cls,),
				{'__is_runtime_defined__': True},
			)

		return entity

	# Write class field facts into memory
	# ----------------------------------------------------------------------
	@classmethod
	def __write__(mcls, cls, fields):
		o.Timer.start('o.TMeta.__write__')

		proto      = cls.__proto__
		annotation = cls.__dict__.get('__annotation__', UNDEFINED)
		cls_id     = cls.id

		with o.services.Memory.write() as memory:
			memory.set(proto, True)
			memory.set(str(cls_id), proto)
			cls.__zone__.set('__version__', cls.__version__)

			if annotation is not UNDEFINED:
				cls.__zone__.set('__annotation__', str(annotation.annotation))

			if cls.__has_own_module__ and proto != 'o.T':
				route = cls.__route__
				memory.set(route, {
					'id'    : cls_id,
					'proto' : proto,
					'mtime' : cls.__mtime__,
				})
				cls.__zone__.set('__route__', route)

			for name, props in fields.items():
				field_key = f'_.{name}'
				for prop_name, prop_value in props.items():
					prop_key = f'{field_key}.{prop_name}'

					if prop_name == 'default' and prop_value is UNDEFINED:
						cls.__zone__.unset(prop_key)
					else:
						cls.__zone__.set(prop_key, prop_value)

		o.Timer.stop('o.TMeta.__write__')

	# Publish field view on Python class
	# ----------------------------------------------------------------------
	def __publish__(cls):
		o.Timer.start('o.TMeta.__publish__')
		annotations = {}

		with o.services.Memory.read():
			for name, field in cls._.items():
				type_cls   = field.type
				annotation = getattr(type_cls, '__annotation__', type_cls)
				default    = getattr(field,    'default',        UNDEFINED)

				annotations[name] = annotation

				if default is not UNDEFINED:
					setattr(cls, name, default)

		if annotations:
			cls.__annotations__ = annotations

		o.Timer.stop('o.TMeta.__publish__')

	# Bind class annotation
	# ----------------------------------------------------------------------
	@classmethod
	def __bind_annotation__(mcls, cls):
		annotation = cls.__dict__.get('__annotation__', UNDEFINED)

		if annotation is UNDEFINED:
			annotation = cls.__zone__.get('__annotation__', UNDEFINED)

		if annotation is not UNDEFINED:
			annotation = o.Annotation(annotation)
			cls.__annotation__ = annotation

	# Proto chain lookup
	# ----------------------------------------------------------------------
	def __getattr__(cls, name):
		entity     = None
		base_proto = getattr(cls, '__proto__', 'o.T')
		proto      = f'{base_proto}.{name}'
		entity_id  = o.proto_to_id(proto)
		entity     = o.__entities__.get(entity_id, None)

		if entity is None and o.services.Memory.has(proto):
			if o.is_class_name(name):
				entity = cls.__class__.__read__(cls, name)
				entity.__class__.__publish__(entity)
			elif o.is_instance_version(name):
				entity = cls.__read__(name)

		if entity is None:
			raise AttributeError(name)

		return entity
	
	# Increment class version and return issued value
	# ----------------------------------------------------------------------
	def __inc_version__(cls):
		version = cls.__version__
		cls.__version__ += 1
		cls.__zone__.set('__version__', cls.__version__)
		return version

	# Instance change hook
	# ----------------------------------------------------------------------
	def __on_change__(cls, instance): pass

	# ======================================================================
	# PUBLIC CLASS METHODS
	# ======================================================================

	# Export strict JSON schema
	# ----------------------------------------------------------------------
	def to_json_schema(cls):
		return o.JsonSchema(cls)

	# Export JSON prompt example
	# ----------------------------------------------------------------------
	def to_prompt(cls):
		return o.JsonPrompt(cls)

	# Extend
	# ----------------------------------------------------------------------
	def extend(cls, __class_name__=None, __annotation__=None, **fields):
		if __class_name__ is None:
			__class_name__ = f'__temp_{uuid.uuid4().hex}'
		elif hasattr(cls, __class_name__):
			raise TypeError(f'`{cls.__proto__}.{__class_name__}` already exists')

		has_annotation = __annotation__ is not None
		namespace      = { **fields, '__is_runtime_defined__' : True }
		bases          = (cls, __annotation__) if has_annotation else (cls, )
		new_cls        = cls.__class__.__new__(cls.__class__, __class_name__, bases, namespace)

		return new_cls

	# Delete class from memory and cache
	# ----------------------------------------------------------------------
	def delete(cls):
		proto = cls.__proto__
		route = cls.__zone__.get('__route__', UNDEFINED)

		with o.services.Memory.write() as memory:
			cls.__zone__.clear()
			memory.unset(proto)
			if route is not UNDEFINED:
				memory.unset(route)

		if cls.id in o.__entities__:
			o.unregister_entity(cls)
