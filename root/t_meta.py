import uuid

import o

UNDEFINED  = o.Undefined
ROOT_PROTO = 'o.T'


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
		proto = ROOT_PROTO if is_root_t else f'{cls.__parent__.__proto__}.{name}'
		zone  = o.services.Memory.zone(f'{proto}.')

		with o.services.Memory.read():
			version = zone.get('__version__', 0)

		cls.__module__         = 'o'
		cls.__has_own_module__ = has_own_module
		cls.__proto__          = proto
		cls.__is_temp__        = is_temp
		cls.__version__        = version
		cls.id                 = o.proto_to_id(proto)
		cls.__zone__           = zone
		cls._                  = o.Accessor(cls, ['_'])

		if has_own_module:
			cls.__route__ = cls.__dict__.get('__route__', UNDEFINED)
			cls.__mtime__ = cls.__dict__.get('__mtime__', UNDEFINED)
		else:
			cls.__route__ = UNDEFINED
			cls.__mtime__ = UNDEFINED

		# Write class facts
		# - - - - - - - - - - - - - - - - - - - - - - - - -

		mcls.__bind_annotation__(cls)
		written_fields = mcls.__write__(cls, fields)

		if fields:
			cls.__class__.__publish__(cls, written_fields)
		else:
			fields = mcls.__read__(cls)
			cls.__class__.__publish__(cls, fields)


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
				default      = namespace.get(name, UNDEFINED)
				fields[name] = o.F(annotation, default=default)

				if name in namespace:
					del namespace[name]

		# Collect fields from namespace
		# - - - - - - - - - - - - - - - - - - - -
		for name, field in list(namespace.items()):
			if not name.startswith('_'):

				# Add fields declared as o.F
				# - - - - - - - - - - - - - - - - - - - -
				if isinstance(field, o.F):
					fields[name] = field
					del namespace[name]

				# Add fields declared as 'key = int' in extend
				# - - - - - - - - - - - - - - - - - - - -
				elif o.Annotation.is_annotation(field):
					fields[name] = o.F(field)
					del namespace[name]

		return fields, namespace

	# ======================================================================
	# CLASS METHODS
	# ======================================================================

	# Create classes for nested annotation
	# ----------------------------------------------------------------------
	@classmethod
	def __embody__(mcls, annotation):
		if isinstance(annotation, type) and '__proto__' in annotation.__dict__:
			cls = annotation
		else:
			annotation = o.Annotation(annotation)
			cls        = o.get_by_annotation(annotation.annotation)

			if cls is UNDEFINED:
				base_cls     = o.get_by_annotation(annotation.origin)
				visible_args = []

				if not annotation.args:
					cls = base_cls
				else:
					for arg in annotation.args:
						arg_cls        = mcls.__embody__(arg)
						own_annotation = arg_cls.__dict__.get('__annotation__', UNDEFINED)
						visible_arg    = arg_cls

						if own_annotation is not UNDEFINED:
							visible_arg = own_annotation.annotation

						visible_args.append(visible_arg)

					namespace = {
						'__annotation__': annotation.origin[*visible_args],
						'__is_runtime_defined__': True,
					}

					cls = mcls.__new__(mcls, f'Generic_{hash(annotation)}', (base_cls,), namespace)

		return cls
	
	# Read fields from disk
	# ----------------------------------------------------------------------
	@classmethod
	def __read__(mcls, cls):
		fields = {}

		with o.services.Memory.read():
			for key, value in cls.__zone__.items('_.'):
				parts = key.split('.')

				if len(parts) >= 3:
					name      = parts[1]
					prop_name = '.'.join(parts[2:])

					if name not in fields:
						fields[name] = {}

					fields[name][prop_name] = value

		return fields

	# Load class from disk by name
	# ----------------------------------------------------------------------
	@classmethod
	def __load__(mcls, cls, name):
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

	# Write class field facts onto disk
	# ----------------------------------------------------------------------
	@classmethod
	def __write__(mcls, cls, fields):
		o.Timer.start('o.TMeta.__write__')

		proto          = cls.__proto__
		annotation     = cls.__dict__.get('__annotation__', UNDEFINED)
		cls_id         = cls.id
		written_fields = {}

		with o.services.Memory.write() as memory:
			memory.set(proto, True)
			o.services.Ids.set(proto)
			cls.__zone__.set('__version__', cls.__version__)

			if annotation is not UNDEFINED:
				cls.__zone__.set('__annotation__', str(annotation.annotation))

			if cls.__has_own_module__ and proto != ROOT_PROTO:
				route = cls.__route__
				o.services.Routes.set(route, {
					'id'    : cls_id,
					'proto' : proto,
					'mtime' : cls.__mtime__,
				})
				cls.__zone__.set('__route__', route)

			for name, field in fields.items():
				written_fields[name] = cls.__write_field__(name, field)

		o.Timer.stop('o.TMeta.__write__')
		return written_fields

	# Write class field onto disk
	# ----------------------------------------------------------------------
	def __write_field__(cls, name, field):
		field_key = f'_.{name}.'
		props     = {}

		if not isinstance(field, o.F):
			raise TypeError(f'Expected o.F for `{cls.__proto__}._.{name}`')

		props['type']    = cls.__class__.__resolve_type_id__(cls, name, field.type)
		props['default'] = field.default

		props.update(field.props)

		for prop_name, prop_value in props.items():
			if prop_name == 'default' and prop_value is UNDEFINED:
				cls.__zone__.unset(field_key + prop_name)
			else:
				cls.__zone__.set(field_key + prop_name, prop_value)

		return props

	# Publish field view on Python class
	# ----------------------------------------------------------------------
	def __publish__(cls, fields):
		o.Timer.start('o.TMeta.__publish__')
		cls.__annotations__ = {}

		for name, field in fields.items():
			cls.__publish_field__(name, field)

		o.Timer.stop('o.TMeta.__publish__')

	# Publish field view on Python class
	# ----------------------------------------------------------------------
	def __publish_field__(cls, name, field):
		default = field.get('default', UNDEFINED)

		if cls.__proto__ != ROOT_PROTO:
			type_id  = field['type']
			type_cls = o.get(type_id)
			cls.__annotations__[name] = getattr(type_cls, '__annotation__', type_cls)

		if default is not UNDEFINED:
			type.__setattr__(cls, '_' + name, default)


	# Does class have field defined?
	# ----------------------------------------------------------------------
	def __has_field__(cls, name):
		result = False

		if name.startswith('_'):
			name = name[1:]

		for base_cls in cls.__mro__:
			if '__zone__' in base_cls.__dict__:
				if base_cls.__zone__.has(f'_.{name}.type'):
					result = True
					break

		return result
	
	# Set field
	# ----------------------------------------------------------------------
	def __set_field__(cls, name, field):
		if not isinstance(field, o.F):
			raise AttributeError(
				f'Expected o.F(...) when setting field `{cls.__proto__}.{name}`'
			)

		field = cls.__class__.__write_field__(cls, name, field)
		cls.__class__.__publish_field__(cls, name, field)

	# Resolve type id with bootstrapping
	# ----------------------------------------------------------------------
	@classmethod
	def __resolve_type_id__(mcls, cls, name, type_cls):
		root_t                = o.__dict__.get('T', UNDEFINED)
		is_root_bootstrapping = root_t is UNDEFINED
		is_root_class         = cls.__proto__ == ROOT_PROTO

		if is_root_bootstrapping and is_root_class:
			annotation = o.Annotation(type_cls).annotation
			proto      = o.__cast_map__.get(annotation, UNDEFINED)

			if proto is UNDEFINED:
				raise TypeError(f'`o.T.{name}` can not use bootstrap annotation `{annotation}`')

			return o.services.Ids.set(proto)

		return mcls.__embody__(type_cls).id
	
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

	# Load subclasses or _<num> instances
	# ----------------------------------------------------------------------
	def __getattr__(cls, name):
		entity      = None
		base_proto  = getattr(cls, '__proto__', ROOT_PROTO)
		proto       = f'{base_proto}.{name}'
		entity_id   = o.proto_to_id(proto)
		entity      = o.__entities__.get(entity_id, None)
		entity_kind = 'Field'

		if cls.__has_field__(name):
			return getattr(cls, f'_{name}')

		if name.startswith('_') and cls.__has_field__(name):
			field_name = name[1:]
			field      = getattr(cls._, field_name)
			default    = getattr(field, 'default', UNDEFINED)

			if default is UNDEFINED:
				raise AttributeError(name)

			return default

		if entity is None and o.services.Memory.has(proto):
			if o.is_class_name(name):
				entity_kind = 'Class'
				entity      = cls.__class__.__load__(cls, name)
				
			elif o.is_instance_version(name):
				entity_kind = 'Instance'
				entity      = cls.__read__(name)

		if entity is None:
			raise AttributeError(f'{entity_kind} `{name}` is not found on `{cls.__proto__}`')

		return entity
	
	# Add new field
	# ----------------------------------------------------------------------
	def __setattr__(cls, name, value):
		if name.startswith('_') or name == 'id':
			type.__setattr__(cls, name, value)
		else:
			if cls.__has_field__(name):
				field = getattr(cls._, name)
				field.default = value
				cls.__class__.__publish_field__(cls, name, {
					'type'    : field.type.id,
					'default' : value,
				})
			else:
				cls.__set_field__(name, value)
			
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
			o.services.Ids.unset(cls.id)
			if route is not UNDEFINED:
				o.services.Routes.unset(route)

		if cls.id in o.__entities__:
			o.unregister_entity(cls)
