import o


class Field(o.Module):

	READ_ONLY = ('type', 'annotation', 'default', 'is_optional')
	ATOMIC    = (int, bool, float, str, type(None))

	def __init__(self, owner, name):
		self.__owner__      = owner
		self.__name__       = name
		self.__disk_field__ = owner.__disk_class__.fields.set(name)

	# Derived optionality
	# ----------------------------------------------------------------------
	@property
	def is_optional(self):
		owner      = self.__owner__
		field_name = self.__name__
		default    = getattr(owner, field_name, o.Undefined)

		return self.annotation.is_optional or (default is not o.Undefined)

	# Read field prop
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		if name == 'annotation':
			value = self.type.__annotation__
		else:
			owner      = self.__owner__
			field_name = self.__name__
			disk_field = self.__disk_field__
			slot_name  = f'__field__{field_name}__{name}__'
			value      = getattr(owner, slot_name, o.Undefined)

			# If owner has no slot yet, load own value from disk
			# - - - - - - - - - - - - - - - - - - - - - - - - -
			if value is o.Undefined:
				if disk_field.has(name):
					value = disk_field.get(name)
					setattr(owner, slot_name, value)

			if value is o.Undefined:
				raise AttributeError(name)

			if name == 'type':
				value = o.get(value)

		return value

	# Set field prop
	# ----------------------------------------------------------------------
	def __setattr__(self, name, value):
		if name.startswith('__'):
			object.__setattr__(self, name, value)
		else:
			if name in self.READ_ONLY:
				raise AttributeError(f'Field prop `{name}` is read-only')

			if not isinstance(value, self.ATOMIC):
				raise ValueError('Value must be atomic')

			# Live field props live on owner class
			# - - - - - - - - - - - - - - - - - - - - - - - - -
			owner      = self.__owner__
			field_name = self.__name__
			disk_field = self.__disk_field__
			slot_name  = f'__field__{field_name}__{name}__'

			setattr(owner, slot_name, value)
			disk_field.set(name, value)

	# Create and populate field room on disk
	# ----------------------------------------------------------------------
	def __write__(self, props):
		disk_field = self.__disk_field__

		for prop_name, prop_value in props.items():
			if prop_name == 'default':
				if prop_value is not o.Undefined:
					disk_field.set(prop_name, prop_value)
			else:
				disk_field.set(prop_name, prop_value)

	# Read existing field values from disk
	# ----------------------------------------------------------------------
	def __read__(self):
		return {
			prop_name: prop_value
			for prop_name, prop_value
			in self.__disk_field__.properties
		}

	# Populate owner field slots
	# ----------------------------------------------------------------------
	def __publish__(self, props):
		owner       = self.__owner__
		name        = self.__name__
		annotations = getattr(owner, '__annotations__', None)

		if annotations is None:
			annotations = {}
			setattr(owner, '__annotations__', annotations)

		if 'type' in props:
			field_cls = o.get(props['type'])
			annotations[name] = getattr(field_cls, '__annotation__', field_cls)

		for prop_name, prop_value in props.items():
			if prop_name == 'default':
				if prop_value is not o.Undefined:
					setattr(owner, name, prop_value)
			else:
				setattr(owner, f'__field__{name}__{prop_name}__', prop_value)
