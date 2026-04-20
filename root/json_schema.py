import o


class JsonSchema(o.Module):

	ATOMIC_TYPES = {
		str        : 'string',
		int        : 'integer',
		float      : 'number',
		bool       : 'boolean',
		type(None) : 'null',
	}

	# Build schema on call
	# ----------------------------------------------------------------------
	def __new__(cls, t_cls):
		return cls.build(t_cls)

	# Build class schema
	# ----------------------------------------------------------------------
	@classmethod
	def build(cls, t_cls):
		if t_cls is o.T:
			raise TypeError('`o.T` has no single JSON schema')

		defs   = {}
		schema = cls._get_root_schema(t_cls, defs, ())

		if defs:
			schema = {**schema, '$defs' : defs}

		return schema

	# Build root schema
	# ----------------------------------------------------------------------
	@classmethod
	def _get_root_schema(cls, t_cls, defs, stack):
		annotation = getattr(t_cls, '__annotation__', o.Undefined)
		schema     = None

		if annotation is o.Undefined:
			schema = cls._get_object_schema(t_cls, defs, stack)
		else:
			schema = cls._get_annotation_schema(annotation, defs, stack)

		return schema

	# Build nested class schema
	# ----------------------------------------------------------------------
	@classmethod
	def _get_class_schema(cls, t_cls, defs, stack):
		annotation = getattr(t_cls, '__annotation__', o.Undefined)
		schema     = None

		if annotation is o.Undefined:
			name = cls._get_def_name(t_cls)

			if name in stack:
				schema = { '$ref' : f'#/$defs/{name}' }
			else:
				if name not in defs:
					defs[name] = cls._get_object_schema(t_cls, defs, stack + (name,))

				schema = { '$ref' : f'#/$defs/{name}' }
		else:
			schema = cls._get_annotation_schema(annotation, defs, stack)

		return schema

	# Build schema from annotation
	# ----------------------------------------------------------------------
	@classmethod
	def _get_annotation_schema(cls, annotation, defs, stack):
		annotation = o.Annotation(annotation)
		schema     = None

		if annotation.is_union:
			schema = {
				'anyOf' : [
					cls._get_annotation_schema(option, defs, stack)
					for option in sorted(annotation.options, key=str)
				]
			}
		elif annotation.is_none:
			schema = { 'type' : 'null' }
		elif isinstance(annotation.annotation, type) and issubclass(annotation.annotation, o.T):
			schema = cls._get_class_schema(annotation.annotation, defs, stack)
		elif annotation.is_list:
			items = {}

			if annotation.value is not None:
				items = cls._get_annotation_schema(annotation.value, defs, stack)

			schema = {
				'type'  : 'array',
				'items' : items,
			}
		elif annotation.is_dict:
			key = annotation.key.annotation if annotation.key is not None else str

			if key is not str:
				raise TypeError(f'JSON schema requires string dict keys, got `{annotation}`')

			value = {}

			if annotation.value is not None:
				value = cls._get_annotation_schema(annotation.value, defs, stack)

			schema = {
				'type'                 : 'object',
				'additionalProperties' : value,
			}
		else:
			json_type = cls.ATOMIC_TYPES.get(annotation.origin, o.Undefined)

			if json_type is o.Undefined:
				raise TypeError(f'Unsupported JSON schema annotation: `{annotation}`')

			schema = { 'type' : json_type }

		return schema

	# Build object schema
	# ----------------------------------------------------------------------
	@classmethod
	def _get_object_schema(cls, t_cls, defs, stack):
		properties = {}
		required   = []

		for name, field in cls._get_fields(t_cls).items():
			properties[name] = cls._get_field_schema(field, defs, stack)

			if not cls._is_field_optional(field):
				required.append(name)

		schema = {
			'type'                 : 'object',
			'properties'           : properties,
			'additionalProperties' : False,
		}

		if required:
			schema['required'] = required

		return schema

	# Build field schema
	# ----------------------------------------------------------------------
	@classmethod
	def _get_field_schema(cls, field, defs, stack):
		field_cls      = field.type
		schema         = cls._get_class_schema(field_cls, defs, stack)
		nullable       = cls._is_field_nullable(field)

		if nullable:
			schema = cls._make_nullable(schema)

		return schema

	# Merge inherited field view
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

	# Check field optionality
	# ----------------------------------------------------------------------
	@classmethod
	def _is_field_optional(cls, field):
		default  = getattr(field, 'default', o.Undefined)
		optional = cls._is_field_nullable(field) or (default is not o.Undefined)

		return optional

	# Check field nullability
	# ----------------------------------------------------------------------
	@classmethod
	def _is_field_nullable(cls, field):
		field_cls      = field.type
		field_type     = getattr(field_cls, '__annotation__', o.Undefined)
		default        = getattr(field, 'default', o.Undefined)
		field_nullable = False

		if field_type is not o.Undefined:
			field_nullable = o.Annotation(field_type).is_optional

		return field_nullable or (default is None)

	# Get stable definition name
	# ----------------------------------------------------------------------
	@classmethod
	def _get_def_name(cls, t_cls):
		return t_cls.__proto__

	# Add null branch
	# ----------------------------------------------------------------------
	@classmethod
	def _make_nullable(cls, schema):
		schema      = dict(schema)
		schema_type = schema.get('type', o.Undefined)

		if schema_type is not o.Undefined:
			if isinstance(schema_type, str):
				if schema_type != 'null':
					schema['type'] = [schema_type, 'null']
			else:
				if 'null' not in schema_type:
					schema['type'] = [*schema_type, 'null']
		else:
			any_of   = list(schema.get('anyOf', ()))
			has_null = any(item.get('type') == 'null' for item in any_of)

			if not has_null:
				any_of.append({ 'type' : 'null' })
				schema['anyOf'] = any_of

		return schema
