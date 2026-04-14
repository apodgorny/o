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

		child = o.T(value)
		value = child

		if name.startswith('_'):
			raise AttributeError(f'Invalid name `{name}`: attribute can not start with "_"')

		if isinstance(child, o.Atom):
			value = child.__value__

		self.__disk_instance__.attributes.set(name, child.id)
		object.__setattr__(self, name, value)

		o.Timer.stop('o.Object.__setattr__')

	## Get builtin-facing attribute
	# ----------------------------------------------------------------------
	def _get_builtin_attr(self, name):
		try:
			builtin_value = self.__cast_out__()
		except (TypeError, NotImplementedError):
			builtin_value = o.undefined

		if builtin_value is not o.undefined and hasattr(builtin_value, name):
			attr = getattr(builtin_value, name)

			if callable(attr):
				method = attr
				def builtin_method(*args, **kwargs):
					result = method(*args, **kwargs)
					self.__cast_in__(builtin_value)

					return result

				attr = builtin_method
		else:
			attr = o.undefined

		return attr

	# Get object attribute on cache miss
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		o.Timer.start('o.Object.__getattr__')

		value = o.undefined

		try:
			if name.startswith('_'):
				raise AttributeError(name)

			disk_instance = object.__getattribute__(self, '__disk_instance__')

			if disk_instance.attributes.has(name):
				child = o.get(disk_instance.attributes.get(name))
				value = child

				if isinstance(child, o.Atom):
					value = child.__value__

				object.__setattr__(self, name, value)
			else:
				value = self._get_builtin_attr(name)

				if value is o.undefined:
					raise AttributeError(name)
		finally:
			o.Timer.stop('o.Object.__getattr__')

		return value

	# Delete object attribute
	# ----------------------------------------------------------------------
	def __delattr__(self, name):
		if name.startswith('_'):
			raise AttributeError(name)

		self.__disk_instance__.attributes.delete(name)

		if name in self.__dict__:
			object.__delattr__(self, name)

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

	# Cast Python-visible value into entity
	# ----------------------------------------------------------------------
	def __cast_in__(self, value):
		raise TypeError(f'`{self.__class__.__proto__}` must implement `__cast_in__()`')

	# Cast out into Python-visible value
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		raise TypeError(f'`{self.__class__.__proto__}` must implement `__cast_out__()`')


o.TOperators.bind(T)
