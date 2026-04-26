import os, uuid
import operator, types

import o


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
		cls               = super().__new__(mcls, name, bases, namespace)

		# SOURCE-BASED
		# - - - - - - - - - - - - - - - - - - - - - - - - - 
		if has_own_module:
			if is_root_t:
				cls.__module__     = 'o'
				cls.__proto__      = 'o.T'
				cls.__disk_class__ = o.disk.Class.get('o.T')
				cls.id             = cls.__disk_class__.id
				cls.__disk_class__.route = cls.__route__

				mcls.__bind_annotation__(cls)
				fields.bind(cls)
				o.register_entity(cls)
			else:
				fields.bind_source(cls)

		# NOT SOURCE-BASED
		# - - - - - - - - - - - - - - - - - - - - - - - - - 
		else:
			proto              = f'{cls.__parent__.__proto__}.{name}'
			cls.__module__     = 'o'
			cls.__proto__      = proto
			cls.__disk_class__ = o.disk.Class.get(proto)
			cls.id             = cls.__disk_class__.id

			mcls.__bind_annotation__(cls)
			fields.bind(cls)
			o.register_entity(cls)

		o.Timer.stop('o.TMeta.__new__')
		return cls

	# Call type
	# ----------------------------------------------------------------------
	def __call__(cls, __value__=o.Undefined, **kwargs):
		self = cls.__new__(cls, __value__, **kwargs)

		if self is not __value__:
			if __value__ is o.Undefined:
				super().__call__(**kwargs)
			else:
				self.__init__(__value__)

		return self

	# Materialize and return subclasses
	# ----------------------------------------------------------------------
	def __subclasses__(cls):
		result = type.__subclasses__(cls)

		if hasattr(cls, '__disk_class__'):
			for name in cls.__disk_class__.subclasses.items:
				getattr(cls, name)

			result = type.__subclasses__(cls)

		return result

	# Create public shadow class from source class
	# ----------------------------------------------------------------------
	def __shadow__(cls):
		shadow_cls = o.__entities__.get(cls.__disk_class__.id, None)

		if shadow_cls is None:
			namespace  = {
				'__is_runtime_defined__' : True,
			}

			# Annotation must be own property
			# - - - - - - - - - - - - - - - - - - - - - - - - -
			if '__annotation__' in cls.__dict__:
				namespace['__annotation__'] = cls.__dict__['__annotation__']

			shadow_cls = cls.__class__.__new__(
				cls.__class__,
				cls.__name__,
				(cls,),
				namespace
			)

		shadow_cls.__has_own_module__ = True
		shadow_cls.__route__          = cls.__route__

		return shadow_cls

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

	# Bind class annotation
	# ----------------------------------------------------------------------
	@classmethod
	def __bind_annotation__(mcls, cls):
		annotation = cls.__dict__.get(
			'__annotation__',
			cls.__disk_class__.annotation
		)

		if annotation is not o.Undefined:
			cls.__annotation__ = o.Annotation(annotation)
			cls.__disk_class__.annotation = cls.__annotation__

	# Set Python class definition from field declarations
	# ----------------------------------------------------------------------
	@classmethod
	def __define__(mcls, namespace):
		annotations = namespace.get('__annotations__', {})
		fields      = o.Fields()

		# Collect fields from annotation
		# - - - - - - - - - - - - - - - - - - - -
		if annotations:
			del namespace['__annotations__']
			for name, annotation in annotations.items():
				type_id = mcls.__embody__(annotation).id
				default = namespace.get(name, o.Undefined)
				fields.add(name, type_id, default, {})

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
					fields.add(name, type_id, field.default, field.props)
					del namespace[name]

				# Add fields declared as 'key = int' in extend
				# - - - - - - - - - - - - - - - - - - - -
				elif o.Annotation.is_annotation(field):
					type_id = mcls.__embody__(field).id
					fields.add(name, type_id, o.Undefined, {})
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
						visible_arg    = arg_cls
						arg_annotation = getattr(arg_cls, '__annotation__', o.Undefined)

						if arg_annotation is not o.Undefined and arg_annotation.is_simple:
							visible_arg = arg_annotation.annotation

						visible_args.append(visible_arg)

					namespace = {
						'__annotation__': annotation.origin[*visible_args],
						'__is_runtime_defined__': True,
					}

					cls = mcls.__new__(mcls, f'Generic_{hash(annotation)}', (base_cls,), namespace)

				o.__cast_map__[annotation.annotation] = cls

		return cls

	# Proto chain lookup
	# ----------------------------------------------------------------------
	def __getattr__(cls, name):
		entity = None
		route  = o.Undefined

		base_proto =  getattr(cls, '__proto__', 'o.T')
		proto      = f'{base_proto}.{name}'
		entity_id  = o.proto_to_id(proto)
		entity     = o.__entities__.get(entity_id, None)

		if entity is None and o.exists(proto):
			if o.is_class_name(name):
				route = o.proto_to_route(proto)

				if route is not o.Undefined:
					entity = eval(route)

					# Route eval may return cached class object
					# ----------------------------------------------------------------------
					if isinstance(entity, type):
						o.register_entity(entity)
				else:
					entity = cls.__class__.__new__(
						cls.__class__, name, (cls,), {'__is_runtime_defined__': True}
					)
			elif o.is_instance_version(name):
				entity = cls.__materialize__(name)

		if entity is None:
			raise AttributeError(name)

		return entity

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
