import os

import o

UNDEFINED = o.Undefined


class T(o.Module, metaclass=o.TMeta):
	__is_atom__ = False
	description = o.F(str, default='')

	# Create new instance
	# ----------------------------------------------------------------------
	def __new__(cls, __value__=UNDEFINED, **kwargs):
		o.Timer.start('o.T.__new__')
		
		sub_cls = cls

		if isinstance(__value__, o.T):
			self = __value__
		else:
			if __value__ is not UNDEFINED:
				# o.T
				# - - - - - - - - - - - - - - - - - -
				if cls is o.T:
					value_type = type(__value__)
					sub_cls    = o.get_by_annotation(value_type)

					if sub_cls is UNDEFINED:
						raise TypeError(f'Cannot cast `{value_type}` into `o.T`')

				if not hasattr(sub_cls, '__annotation__'):
					raise TypeError(f'`{sub_cls.__proto__}` does not accept positional value')

			version = sub_cls.__write__(kwargs)
			self    = sub_cls.__read__(f'_{version}')
			
			o.services.Garbage.on_instance_create(self)
			self.__publish__(kwargs)

		o.Timer.stop('o.T.__new__')
		return self
	
	# Set object attribute
	# ----------------------------------------------------------------------
	def __setattr__(self, name, value):
		o.Timer.start('o.T.__setattr__')

		if name.startswith('_'):
			raise AttributeError(f'Invalid name `{name}`: attribute can not start with "_"')
		
		if not self.__class__.__has_field__(name):
			raise AttributeError(f'Field `{name}` is not defined on `{self.__class__.__proto__}`')
		
		with o.services.Memory.write():
			old_id   = self.__zone__.get(name, UNDEFINED)
			child    = value if isinstance(value, o.T) else o.T(value)
			child_id = child.id
			value    = o.value(child_id)

			if old_id != child_id:
				o.services.Garbage.on_instance_link(child)
				if old_id is not UNDEFINED:
					o.services.Garbage.on_instance_unlink(o.get(old_id))

			self.__zone__.set(name, child_id)

		object.__setattr__(self, name, value)

		if old_id != child_id:
			self.__class__.__on_change__(self)

		o.Timer.stop('o.T.__setattr__')

	# Get object attribute on cache miss
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		o.Timer.start('o.Object.__getattr__')

		if name.startswith('_'):
			raise AttributeError(name)
		
		with o.services.Memory.read():
			value = UNDEFINED

			if self.__zone__.has(name):
				value = o.value(self.__zone__.get(name))
				object.__setattr__(self, name, value)
			elif self.__class__.__has_field__(name):
				value = getattr(self.__class__, name, UNDEFINED)

				if value is UNDEFINED:
					raise AttributeError(name)
			else:
				value = self.__get_builtin_attr__(name)

				if value is UNDEFINED:
					raise AttributeError(name)
		
		o.Timer.stop('o.Object.__getattr__')
		return value
	
	# Get builtin-facing attribute
	# ----------------------------------------------------------------------
	def __get_builtin_attr__(self, name):
		try:
			builtin_value = self.__cast_out__()
		except (TypeError, NotImplementedError):
			builtin_value = UNDEFINED

		if builtin_value is not UNDEFINED and hasattr(builtin_value, name):
			attr = getattr(builtin_value, name)

			if callable(attr):
				method = attr
				def builtin_method(*args, **kwargs):
					result = method(*args, **kwargs)
					self.__cast_in__(builtin_value)

					return result

				attr = builtin_method
		else:
			attr = UNDEFINED

		return attr

	# Delete object attribute
	# ----------------------------------------------------------------------
	def __delattr__(self, name):
		if name.startswith('_'):
			raise AttributeError(name)

		if not self.__class__.__has_field__(name):
			raise AttributeError(f'Field `{name}` is not defined on `{self.__class__.__proto__}`')

		with o.services.Memory.write():
			child_id = self.__zone__.get(name, UNDEFINED)
			if child_id is UNDEFINED:
				raise AttributeError(name)
			o.services.Garbage.on_instance_unlink(o.get(child_id))
			self.__zone__.unset(name)

		if name in self.__dict__:
			object.__delattr__(self, name)

		self.__class__.__on_change__(self)

	# Read instance from memory based on class and version
	# ----------------------------------------------------------------------
	@classmethod
	def __read__(cls, version):
		self           = object.__new__(cls)
		proto          = f'{cls.__proto__}.{version}'
		id             = o.proto_to_id(proto)
		version_number = int(version[1:])

		object.__setattr__(self, 'id',          id             )
		object.__setattr__(self, '__version__', version_number )
		object.__setattr__(self, '__proto__',   proto          )
		object.__setattr__(self, '__zone__',    o.services.Memory.zone(f'{proto}.'))
		object.__setattr__(self, '__refcount__', 0             )

		o.register_entity(self)

		return self

	# Write born subclass instance
	# ----------------------------------------------------------------------
	@classmethod
	def __write__(cls, kwargs):
		o.Timer.start('o.T.__write__')

		with o.services.Memory.write() as memory:
			version = cls.__inc_version__()
			proto   = f'{cls.__proto__}._{version}'
			id      = o.services.Ids.set(proto)

			memory.set(proto, True)

		with o.services.Memory.read():
			for name, field in cls._.items():
				if name not in kwargs and not field.is_optional:
					raise TypeError(f'Missing required field `{name}` for `{cls.__proto__}`')

		o.Timer.stop('o.T.__write__')
		return version

	# Publish instance values
	# ----------------------------------------------------------------------
	def __publish__(self, kwargs):
		for name, value in kwargs.items():
			setattr(self, name, value)

	# Get retained dependants
	# ----------------------------------------------------------------------
	def __dependants__(self):
		with o.services.Memory.read():
			for name, child_id in self.__zone__.items():
				child = UNDEFINED

				if '.' not in name and not name.startswith('_'):
					child = o.get(child_id)
					yield name, f'{self.__proto__}.{name}', child

	# Delete instance from memory and cache
	# ----------------------------------------------------------------------
	def delete(self):
		with o.services.Memory.write() as memory:
			o.services.Garbage.on_instance_delete(self)
			self.__zone__.clear()
			memory.unset(self.__proto__)
			o.services.Ids.unset(self.id)

		o.unregister_entity(self)

	# Cast Python-visible value into entity
	# ----------------------------------------------------------------------
	def __cast_in__(self, value):
		raise TypeError(f'`{self.__class__.__proto__}` must implement `__cast_in__()`')

	# Cast out into Python-visible value
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		raise TypeError(f'`{self.__class__.__proto__}` must implement `__cast_out__()`')


o.TOperators.bind(T)
