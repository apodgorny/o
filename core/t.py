import os

import o


class T(o.Module, metaclass=o.TMeta):

	# Create new instance
	# ----------------------------------------------------------------------
	def __new__(cls, __value__=o.undefined, **kwargs):
		o.Timer.start('o.T.__new__')
		
		sub_cls = cls

		if isinstance(__value__, o.T):
			self = __value__
		else:
			if __value__ is not o.undefined:
				# o.T
				# - - - - - - - - - - - - - - - - - -
				if cls is o.T:
					value_type = type(__value__)
					sub_cls    = o.__cast_map__.get(value_type, None)

					if sub_cls is None:
						raise TypeError(f'Cannot cast `{value_type}` into `o.T`')

				if not hasattr(sub_cls, '__annotation__'):
					raise TypeError(f'`{sub_cls.__proto__}` does not accept positional value')

			self = object.__new__(sub_cls)
			self.__sync__(kwargs)
			o.register_entity(self)

		o.Timer.stop('o.T.__new__')
		return self

	# Set object attribute
	# ----------------------------------------------------------------------
	def __setattr__(self, name, value):
		o.Timer.start('o.Object.__setattr__')

		cls = self.__class__
		value_instance = o.T(value)
		value_visible  = value_instance

		if name.startswith('_'):
			raise AttributeError(f'Invalid name `{name}`: attribute can not start with "_"')
		
		# if not cls.__disk_class__.fields.has(name):
		# 	raise TypeError(f'Unexpected field name `{name}` for `{cls.__proto__}`')

		if isinstance(value_instance, o.Atom):
			value_visible = value_instance.__value__

		self.__disk_instance__.attributes.set(name, value_instance.id)
		# object.__setattr__(self, name, value_visible)

		o.Timer.stop('o.Object.__setattr__')

	# Get object attribute
	# ----------------------------------------------------------------------
	def __getattribute__(self, name):
		o.Timer.start('o.Object.__getattribute__')

		value = o.undefined

		try:
			if name.startswith('_'):
				value = object.__getattribute__(self, name)
			else:
				disk_instance = object.__getattribute__(self, '__disk_instance__')

				if disk_instance.attributes.has(name):
					id    = disk_instance.attributes.get(name)
					value = o.get(id)

					if isinstance(value, o.Atom):
						value = value.__value__

					object.__setattr__(self, name, value)
				else:
					value = object.__getattribute__(self, name)
		finally:
			o.Timer.stop('o.Object.__getattribute__')

		return value

	# Delete runtime instance
	# ----------------------------------------------------------------------
	def __del__(self):
		if hasattr(self, 'id'):
			entity = o.__entities__.get(self.id)

			if entity is self:
				del o.__entities__[self.id]

		if hasattr(self, '__disk_instance__'):
			self.__disk_instance__.delete()

	# # Get object attribute
	# # ----------------------------------------------------------------------
	# def __getattr__(self, name):
	# 	o.Timer.start('o.Object.__getattr__')

	# 	cls   = self.__class__
	# 	value = o.undefined

	# 	# if cls.__disk_class__.fields.has(name):
	# 	if self.__disk_instance__.attributes.has(name):
	# 		id    = self.__disk_instance__.attributes.get(name)
	# 		value = o.get(id)

	# 		if isinstance(value, o.Atom):
	# 			value = value.__value__

	# 		# object.__setattr__(self, name, value)

	# 	if value is o.undefined:
	# 		o.Timer.stop('o.Object.__getattr__')
	# 		raise AttributeError(name)

	# 	o.Timer.stop('o.Object.__getattr__')
	# 	return value

	# Setup born subclass instance
	# ----------------------------------------------------------------------
	def __sync__(self, kwargs):
		cls           = self.__class__
		annotation    = getattr(cls, '__annotation__', o.undefined)
		disk_instance = cls.__disk_class__.instances.create(annotation)

		for name, field in cls._.items():
			if name not in kwargs and not field.is_optional:
				raise TypeError(f'Missing required field `{name}` for `{cls.__proto__}`')

		version = os.path.basename(disk_instance.path)

		object.__setattr__(self, 'id', disk_instance.id)
		object.__setattr__(self, '__disk_instance__', disk_instance)
		object.__setattr__(self, '__version__', version)
		object.__setattr__(self, '__proto__', f'{cls.__proto__}.{version}')

		for name, value in kwargs.items():
			setattr(self, name, value)

	# Load instance from disk based on class and version id
	# ----------------------------------------------------------------------
	@classmethod
	def __materialize__(cls, version):
		disk_instance = cls.__disk_class__.instances.get(version)
		self          = object.__new__(cls)

		object.__setattr__(self, 'id', disk_instance.id)
		object.__setattr__(self, '__disk_instance__', disk_instance)
		object.__setattr__(self, '__version__', version)
		object.__setattr__(self, '__proto__', f'{cls.__proto__}.{version}')

		return self
