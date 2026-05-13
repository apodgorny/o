import o

UNDEFINED = o.Undefined


class Serializer(o.Module):

	CLASS_RESERVED    = ('__proto__', 'description')
	INSTANCE_RESERVED = ('__proto__', 'description', '__data__')

	# Serialize class or instance into spec
	# ----------------------------------------------------------------------
	@classmethod
	def serialize(cls, value):
		spec = None

		if isinstance(value, type) and issubclass(value, o.T):
			spec = {
				'class'     : cls._serialize_class(value),
				'instances' : [],
			}
		elif isinstance(value, o.T):
			spec = {
				'class'     : cls._serialize_class(value.__class__),
				'instances' : [cls._serialize_instance(value)],
			}
		else:
			raise TypeError(f'Cannot serialize `{type(value)}`')

		return spec

	# Deserialize spec into class or instance
	# ----------------------------------------------------------------------
	@classmethod
	def deserialize(cls, spec):
		result = None

		if cls._is_envelope_spec(spec):
			Class     = cls._deserialize_class(spec['class'])
			instances = []

			for instance_spec in spec['instances']:
				instances.append(cls._deserialize_instance(Class, instance_spec))

			if len(instances) == 0:
				result = Class
			elif len(instances) == 1:
				result = instances[0]
			else:
				result = instances
		elif cls._is_instance_spec(spec):
			Class  = cls._deserialize_class({ '__proto__' : spec['__proto__'] })
			result = cls._deserialize_instance(Class, spec)
		else:
			raise TypeError('Serializer spec must be instance or envelope shaped')

		return result

	# Serialize class definition
	# ----------------------------------------------------------------------
	@classmethod
	def _serialize_class(cls, t_cls):
		spec = {
			'__proto__'   : t_cls.__proto__,
			'description' : t_cls.description,
		}

		with o.services.Memory.read():
			for name, field in t_cls._.items():
				if name != 'description':
					spec[name] = cls._serialize_field(field)

		return spec

	# Serialize field definition
	# ----------------------------------------------------------------------
	@classmethod
	def _serialize_field(cls, field):
		spec = {}

		with o.services.Memory.read():
			for prop_name, prop_value in field.items():
				prop_name = prop_name.split('.')[-1]

				if prop_name == 'type':
					spec['type'] = cls._serialize_type(field.type)
				elif prop_name == 'default':
					spec['default'] = cls._serialize_plain_value(prop_value)
				elif prop_value is not UNDEFINED:
					spec[prop_name] = prop_value

		return spec

	# Serialize instance birth spec
	# ----------------------------------------------------------------------
	@classmethod
	def _serialize_instance(cls, instance, include_proto=False):
		spec   = {}
		fields = cls._get_fields(instance.__class__)

		if include_proto:
			spec['__proto__'] = instance.__class__.__proto__

		spec['description'] = instance.description

		for name in fields:
			value = UNDEFINED

			if name != 'description':
				try:
					value = getattr(instance, name)
				except AttributeError:
					value = UNDEFINED

				if value is not UNDEFINED:
					spec[name] = cls._serialize_field_value(fields[name], value)

		data = cls._serialize_data(instance)

		if data is not UNDEFINED:
			spec['__data__'] = data

		return spec

	# Serialize one instance field value according to declared field type
	# ----------------------------------------------------------------------
	@classmethod
	def _serialize_field_value(cls, field, value):
		annotation = getattr(field.type, '__annotation__', UNDEFINED)
		result     = value

		if annotation is not UNDEFINED:
			annotation = o.Annotation(annotation)

			if annotation.is_list or annotation.is_dict or annotation.is_atomic:
				result = cls._serialize_plain_value(value.__cast_out__() if isinstance(value, o.T) else value)
			else:
				result = cls._serialize_value(value)
		else:
			result = cls._serialize_value(value)

		return result

	# Serialize embodied payload
	# ----------------------------------------------------------------------
	@classmethod
	def _serialize_data(cls, instance):
		annotation = getattr(instance.__class__, '__annotation__', UNDEFINED)
		data       = UNDEFINED

		if annotation is not UNDEFINED:
			annotation = o.Annotation(annotation)

			if annotation.is_list:
				data = [cls._serialize_value(item) for item in instance]
			elif annotation.is_dict:
				data = {}

				for key, value in instance.items():
					if not isinstance(key, str):
						raise TypeError('Serializer requires `str` keys for dict data')

					data[key] = cls._serialize_value(value)
			else:
				data = cls._serialize_plain_value(instance.__cast_out__())

		return data

	# Serialize nested value
	# ----------------------------------------------------------------------
	@classmethod
	def _serialize_value(cls, value):
		result = value

		if isinstance(value, o.T):
			result = cls._serialize_instance(value, True)
		elif isinstance(value, list):
			result = [cls._serialize_value(item) for item in value]
		elif isinstance(value, dict):
			result = {}

			for key, item in value.items():
				result[key] = cls._serialize_value(item)

		return result

	# Serialize non-entity value
	# ----------------------------------------------------------------------
	@classmethod
	def _serialize_plain_value(cls, value):
		result = value

		if isinstance(value, list):
			result = [cls._serialize_plain_value(item) for item in value]
		elif isinstance(value, dict):
			result = {}

			for key, item in value.items():
				result[key] = cls._serialize_plain_value(item)

		return result

	# Serialize field type
	# ----------------------------------------------------------------------
	@classmethod
	def _serialize_type(cls, t_cls):
		annotation = t_cls.__dict__.get('__annotation__', UNDEFINED)
		result     = t_cls.__proto__

		if annotation is not UNDEFINED:
			result = str(annotation)

		return result

	# Deserialize class definition
	# ----------------------------------------------------------------------
	@classmethod
	def _deserialize_class(cls, spec):
		proto  = spec['__proto__']
		Class  = o.get(proto) if o.exists(proto) else UNDEFINED
		parent = UNDEFINED

		if Class is UNDEFINED:
			parent_proto, class_name = proto.rsplit('.', 1)
			parent                   = o.get(parent_proto)

			if parent is UNDEFINED:
				raise TypeError(f'Parent `{parent_proto}` is not found')

			Class = parent.extend(class_name)

		if 'description' in spec:
			cls._set_class_description(Class, spec['description'])

		for name, field_spec in spec.items():
			if name not in cls.CLASS_RESERVED:
				setattr(Class, name, cls._deserialize_field(field_spec, Class))

		return Class

	# Deserialize field definition
	# ----------------------------------------------------------------------
	@classmethod
	def _deserialize_field(cls, spec, Class):
		type_spec    = spec['type']
		description  = spec.get('description')
		default      = UNDEFINED
		field_type   = cls._deserialize_type(type_spec, Class)
		field_kwargs = {}

		if 'default' in spec:
			default = cls._deserialize_plain_value(spec['default'])

		for key, value in spec.items():
			if key not in ('type', 'default', 'description'):
				field_kwargs[key] = value

		return o.F(field_type, description=description, default=default, **field_kwargs)

	# Deserialize instance birth spec
	# ----------------------------------------------------------------------
	@classmethod
	def _deserialize_instance(cls, Class, spec):
		kwargs = {}
		data   = UNDEFINED
		result = None

		for key, value in spec.items():
			if key == '__data__':
				data = cls._deserialize_value(value)
			elif key not in cls.INSTANCE_RESERVED:
				kwargs[key] = cls._deserialize_value(value)

		if 'description' in spec:
			kwargs['description'] = spec['description']

		if data is UNDEFINED:
			result = Class(**kwargs)
		else:
			result = Class(data, **kwargs)

		return result

	# Deserialize nested value
	# ----------------------------------------------------------------------
	@classmethod
	def _deserialize_value(cls, value):
		result = value

		if cls._is_envelope_spec(value) or cls._is_instance_spec(value):
			result = cls.deserialize(value)
		elif isinstance(value, list):
			result = [cls._deserialize_value(item) for item in value]
		elif isinstance(value, dict):
			result = {}

			for key, item in value.items():
				result[key] = cls._deserialize_value(item)

		return result

	# Deserialize non-entity value
	# ----------------------------------------------------------------------
	@classmethod
	def _deserialize_plain_value(cls, value):
		result = value

		if isinstance(value, list):
			result = [cls._deserialize_plain_value(item) for item in value]
		elif isinstance(value, dict):
			result = {}

			for key, item in value.items():
				result[key] = cls._deserialize_plain_value(item)

		return result

	# Deserialize type from field spec
	# ----------------------------------------------------------------------
	@classmethod
	def _deserialize_type(cls, type_spec, Class):
		result = Class

		if type_spec != Class.__proto__:
			result = o.Annotation(type_spec).annotation

		return result

	# Set class description without touching inherited field assignment path
	# ----------------------------------------------------------------------
	@classmethod
	def _set_class_description(cls, Class, description):
		field = o.T._.description

		Class.__zone__.set('_.description.default', description)
		Class.__class__.__publish_field__(Class, 'description', {
			'type'    : field.type.id,
			'default' : description,
		})

	# Merge visible field view
	# ----------------------------------------------------------------------
	@classmethod
	def _get_fields(cls, t_cls):
		fields = {}

		for base in reversed(t_cls.__mro__):
			namespace = base.__dict__.get('_')

			if namespace is not None:
				for name, field in namespace.items():
					fields[name] = field

		return fields

	# Check full envelope shape
	# ----------------------------------------------------------------------
	@classmethod
	def _is_envelope_spec(cls, value):
		return isinstance(value, dict) and 'class' in value and 'instances' in value

	# Check compact existing-class instance shape
	# ----------------------------------------------------------------------
	@classmethod
	def _is_instance_spec(cls, value):
		return isinstance(value, dict) and '__proto__' in value
