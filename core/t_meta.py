import os
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
		is_runtime_defined = namespace.get('__is_runtime_defined__', False)

		# Support annotation definition only for o.T base
		# - - - - - - - - - - - - - - - - - - - - - - - - - 
		if len(bases) > 1:
			if bases[0] is o.T:
				orig_bases = namespace.get('__orig_bases__', bases)
				annotation = orig_bases[1]
				bases      = (mcls.__embody__(annotation),)
			else:
				raise TypeError('Only o.T can accept annotation as second base class')

		# Create disk class
		# - - - - - - - - - - - - - - - - - - - - - - - - - 
		base_proto = getattr(bases[0], '__proto__', 'o')
		proto      = f'{base_proto}.{name}'
		disk_class = o.disk.Class(proto)
		o_module   = disk_class.o_module

		# Class does not have __o_module__ on disk
		# - - - - - - - - - - - - - - - - - - - - - - - - - 
		if o_module is o.undefined:
			fields, namespace = mcls.__define__(namespace)

			cls = super().__new__(mcls, name, bases, namespace)
			cls.__module__     = 'o'
			cls.__proto__      = proto
			cls.__disk_class__ = disk_class
			cls.id             = disk_class.id

			# Prevent class definitions in runtime
			# - - - - - - - - - - - - - - - - - - - - - - - - - 
			if not is_runtime_defined:
				if cls.__has_own_module__:
					disk_class.o_module = cls.__o_module__
					cls.__is_runtime_defined__ = False
				else:
					raise TypeError(
						f'Class definitions can only be loaded from o.Module. Use o.T.extend() instead.'
					)
				
			mcls.__bind_annotation__(cls)
			fields.bind(cls)

		# Class has __o_module__ on disk
		# - - - - - - - - - - - - - - - - - - - - - - - - - 
		else:
			cls = eval(o_module)

		o.register_entity(cls)

		o.Timer.stop('o.TMeta.__new__')
		return cls

	# Call type
	# ----------------------------------------------------------------------
	def __call__(cls, __value__=o.undefined, **kwargs):
		self = cls.__new__(cls, __value__, **kwargs)

		if self is not __value__:
			if __value__ is o.undefined:
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

	# Bind class annotation
	# ----------------------------------------------------------------------
	@classmethod
	def __bind_annotation__(mcls, cls):
		annotation = cls.__dict__.get(
			'__annotation__',
			cls.__disk_class__.annotation
		)

		if annotation is not o.undefined:
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
				default = namespace.get(name, o.undefined)
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
					fields.add(name, type_id, o.undefined, {})
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
						arg_annotation = arg_cls.__annotation__
						visible_arg    = arg_cls

						if arg_annotation.is_simple:
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

		base_proto =  getattr(cls, '__proto__', 'o.T')
		proto      = f'{base_proto}.{name}'
		entity_id  = o.proto_to_id(proto)
		entity     = o.__entities__.get(entity_id, None)

		if entity is None and o.exists(proto):
			if o.is_class_name(name):
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

	# Extend
	# ----------------------------------------------------------------------
	def extend(cls, __class_name__, __annotation__=None, **fields):
		if hasattr(cls, __class_name__):
			raise TypeError(f'`{cls.__proto__}.{__class_name__}` already exists')

		has_annotation = __annotation__ is not None
		namespace      = { **fields, '__is_runtime_defined__' : True }
		bases          = (cls, __annotation__) if has_annotation else (cls, )
		new_cls        = cls.__class__.__new__(cls.__class__, __class_name__, bases, namespace)

		return new_cls
