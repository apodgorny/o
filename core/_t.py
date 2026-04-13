import os

import o


class T(o.Module, metaclass=o.TMeta):

	# # Create new instance
	# # ----------------------------------------------------------------------
	# def __new__(cls, *args, **kwargs):
	# 	value      = o.undefined
	# 	annotation = getattr(cls, '__annotation__', None)

	# 	# Inheritable – single unnamed arg only
	# 	# - - - - - - - - - - - - - - - - - -
	# 	if len(args) == 1:
	# 		value = args[0]
	# 	elif len(args) > 1:
	# 		raise TypeError(f'Too many positional arguments for `{cls.__o_module__}`')
	# 	elif kwargs:
	# 		value = kwargs

	# 	if value is o.undefined:
	# 		raise TypeError(f'`{cls.__proto__}` requires one value')

	# 	# Not inheritable – o.T only
	# 	# - - - - - - - - - - - - - - - - - -
	# 	if cls is o.T:
	# 		self = o.T.__embody__(value)
		
	# 	# Inheritable – Subclasses of o.T
	# 	# - - - - - - - - - - - - - - - - - -
	# 	else:
	# 		if annotation is not None and not isinstance(value, annotation.origin):
	# 			raise TypeError(
	# 				f'`{cls.__proto__}` expects `{annotation.origin}`, got `{type(value)}`'
	# 			)
		
	# 		self          = object.__new__(cls)
	# 		disk_instance = cls.__disk_class__.instances.create(annotation)
	# 		version       = os.path.basename(disk_instance.path)

	# 		object.__setattr__(self, '__disk_instance__', disk_instance)
	# 		object.__setattr__(self, '__version__', version)
	# 		object.__setattr__(self, '__proto__', f'{cls.__proto__}.{version}')

	# 		for name in cls.__disk_class__.fields.items:
	# 			default = getattr(cls, name, o.undefined)
	# 			if name not in kwargs and default is o.undefined:
	# 				raise TypeError(f'Missing required field `{name}` for `{cls.__proto__}`')

	# 		for name, value in kwargs.items():
	# 			setattr(self, name, value)

	# 	return self

	def __new__(cls, *args, **kwargs):
		value      = o.undefined
		annotation = getattr(cls, '__annotation__', None)

		# Root embodiment
		# - - - - - - - - - - - - - - - - - -
		if cls is o.T:
			if len(args) == 1:
				value = args[0]
			elif len(args) > 1:
				raise TypeError(f'Too many positional arguments for `{cls.__o_module__}`')
			elif kwargs:
				value = kwargs

			return o.T.__embody__(value)

		# No mixed constructor modes
		# - - - - - - - - - - - - - - - - - -
		if args and kwargs:
			raise TypeError(
				f'`{cls.__proto__}` does not allow mixing positional value and named fields'
			)

		self          = object.__new__(cls)
		disk_instance = cls.__disk_class__.instances.create(annotation)
		version       = os.path.basename(disk_instance.path)

		object.__setattr__(self, '__disk_instance__', disk_instance)
		object.__setattr__(self, '__version__', version)
		object.__setattr__(self, '__proto__', f'{cls.__proto__}.{version}')

		# Positional value mode
		# - - - - - - - - - - - - - - - - - -
		if args:
			if len(args) > 1:
				raise TypeError(f'Too many positional arguments for `{cls.__o_module__}`')

			value = args[0]

			if annotation is None:
				raise TypeError(f'`{cls.__proto__}` does not accept positional value')

			if not isinstance(value, annotation.origin):
				raise TypeError(
					f'`{cls.__proto__}` expects `{annotation.origin}`, got `{type(value)}`'
				)

		# Named field mode
		# - - - - - - - - - - - - - - - - - -
		else:
			for name in cls.__disk_class__.fields.items:
				default = getattr(cls, name, o.undefined)

				if name not in kwargs and default is o.undefined:
					raise TypeError(f'Missing required field `{name}` for `{cls.__proto__}`')

			for name, item in kwargs.items():
				setattr(self, name, item)

		return self

	# Set attribute
	# ----------------------------------------------------------------------
	def __setattr__(self, name, value):
		cls = self.__class__

		if name.startswith('_'):
			raise AttributeError(f'Invalid name `{name}`: attribute can not start with "_"')

		if not cls.__disk_class__.fields.has(name):
			raise TypeError(f'Unexpected field name `{name}` for `{cls.__proto__}`')

		value_instance = o.T(value)
		self.__disk_instance__.attributes.set(name, value_instance.id)
		object.__setattr__(self, name, value)

	# Embody data tree
	# ----------------------------------------------------------------------
	@classmethod
	def __embody__(cls, value):
		if value is o.undefined:
			raise TypeError('o.T(value) requires one root value')

		value_type = type(value)
		instance   = value

		if not isinstance(value, o.T):
			if value_type in o.__cast_map__:
				value_cls = o.__cast_map__[value_type]
				instance  = value_cls(value)
			else:
				raise TypeError(f'Cannot cast `{value_type}` into `o.T`')

		return instance

	# Embody data tree
	# ----------------------------------------------------------------------
	@property
	def id(self):
		return self.__disk_instance__.id

	# Embody data tree
	# ----------------------------------------------------------------------
	@property
	def proto(self):
		return self.__proto__

	# def __new__(cls, *args, **kwargs):
		# value = o.undefined

		# # Single value o.MyType(foo)
		# # - - - - - - - - - - - - - - - - - -
		# if len(args) == 1:
		# 	value = args[0]
		# elif len(args) > 1:
		# 	raise TypeError(f'Too many positional arguments for `{cls.__o_module__}`')

		# # In base class o.T
		# # - - - - - - - - - - - - - - - - - -
		# if cls is o.T:
		# 	if kwargs:
		# 		value = kwargs

		# 	if value is o.undefined:
		# 		raise TypeError('o.T(value) requires one root value')

		# 	value_type = type(value)

		# 	if isinstance(value, o.T):
		# 		instance = value
		# 	else:
		# 		if value_type in o.__cast_map__:
		# 			value_cls = o.__cast_map__[value_type]
		# 			instance  = object.__new__(value_cls)
		# 		else:
		# 			raise TypeError(
		# 				f'Cannot cast `{value_type}` into `o.T`'
		# 			)
		# # Subclasses construct normally
		# # - - - - - - - - - - - - - - - - - -
		# else:
		# 	instance = object.__new__(cls)

		# if not hasattr(instance, '__id__'):
		# 	instance.__id__ = o.services.Store.create()
		# 	o.__instances_by_id__[instance.__id__] = instance

		# return instance

	# Cast external data into internal state and write to disk
	# ----------------------------------------------------------------------
	# def __cast_in__(self, data):
	# 	raise NotImplementedError

	# # Cast internal state into python object
	# # ----------------------------------------------------------------------
	# def __cast_out__(self):
	# 	raise NotImplementedError

# 	# Define
# 	# ----------------------------------------------------------------------
# 	@classmethod
# 	def define(cls, type_name, annotation=None, **fields):
# 		o.Timer.start('o.T.define')

# 		if o[type_name] is not None:
# 			raise TypeError(f'Namespace `o.{type_name}` is occupied or type with this name exists')
			
# 		has_annotation = annotation is not None
# 		has_fields     = len(fields) > 0
		
# 		# Either annotation or fields, not both
# 		# - - - - - - - - - - - - - - - - - - - -
# 		if has_annotation == has_fields:
# 			raise ValueError(f'Either named fields or annotation can/must be provided')

# 		# Fields – o.Object
# 		# - - - - - - - - - - - - - - - - - - - -
# 		if has_fields:
# 			bases     = (o.Object,)
# 			namespace = {}

# 			for fname, f in fields.items():
# 				if isinstance(f, o.F):
# 					f.name = fname
# 					namespace[fname] = f
# 				else:
# 					namespace[fname] = o.F(
# 						name        = fname,
# 						type        = f,
# 						description = None,
# 						default     = o.undefined
# 					)

# 		# Annotation – not o.Object
# 		# - - - - - - - - - - - - - - - - - - - -
# 		else:
# 			bases      = (T, annotation)
# 			namespace  = { '__annotation__': o.Annotation(annotation) }

# 		# Create type
# 		# - - - - - - - - - - - - - - - - - - - -
# 		new_type = types.new_class(
# 			type_name,
# 			bases,
# 			{},
# 			lambda ns: ns.update(namespace),
# 		)

# 		o.Timer.stop('o.T.define')
# 		return new_type
