import o

UNDEFINED = o.Undefined


class JsonSchema(o.Module):

	ATOMIC_TYPES = {
		str        : 'string',
		int        : 'integer',
		float      : 'number',
		bool       : 'boolean',
		type(None) : 'null',
	}

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Build schema on call
	# ----------------------------------------------------------------------
	def __new__(cls, t_cls):
		return cls.build(t_cls)

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Build root schema
	# ----------------------------------------------------------------------
	@classmethod
	def _get_root_schema(cls, t_cls, defs, stack):
		annotation = getattr(t_cls, '__annotation__', UNDEFINED)
		schema     = None

		if annotation is UNDEFINED:
			schema = cls._get_object_schema(t_cls, defs, stack)
		else:
			schema = cls._get_annotation_schema(annotation, defs, stack)

		return schema

	# Build nested class schema
	# ----------------------------------------------------------------------
	@classmethod
	def _get_class_schema(cls, t_cls, defs, stack):
		annotation = getattr(t_cls, '__annotation__', UNDEFINED)

		if annotation is UNDEFINED:
			name = cls._get_def_name(t_cls)

			if name not in stack and name not in defs:
				defs[name] = cls._get_object_schema(t_cls, defs, stack + (name,))

			schema = { '$ref' : f'#/$defs/{name}' }
		else:
			schema = cls._get_annotation_schema(annotation, defs, stack)

		return schema

	# Build schema from annotation
	# ----------------------------------------------------------------------
	@classmethod
	def _get_annotation_schema(cls, annotation, defs, stack):
		if not isinstance(annotation, o.Annotation):
			annotation = o.Annotation(annotation)

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

			if key is str:
				value = {}

				if annotation.value is not None:
					value = cls._get_annotation_schema(annotation.value, defs, stack)

				schema = {
					'type'                 : 'object',
					'additionalProperties' : value,
				}
			else:
				raise TypeError(f'JSON schema requires string dict keys, got `{annotation}`')
		else:
			json_type = cls.ATOMIC_TYPES.get(annotation.origin, UNDEFINED)

			if json_type is not UNDEFINED:
				schema = { 'type' : json_type }
			else:
				raise TypeError(f'Unsupported JSON schema annotation: `{annotation}`')

		return schema

	# Build object schema
	# ----------------------------------------------------------------------
	@classmethod
	def _get_object_schema(cls, t_cls, defs, stack):
		properties = {}
		required   = []

		with o.services.Memory.read():
			for name, field in cls._get_fields(t_cls).items():
				field_schema, is_required = cls._get_field_schema(field, defs, stack)
				properties[name]          = field_schema

				if is_required:
					required.append(name)

		schema = {
			'type'                 : 'object',
			'properties'           : properties,
			'additionalProperties' : False,
		}

		if required:
			schema['required'] = required

		return schema

	# Build field schema and requiredness together
	# ----------------------------------------------------------------------
	@classmethod
	def _get_field_schema(cls, field, defs, stack):
		field_cls  = field.type
		field_type = getattr(field_cls, '__annotation__', UNDEFINED)

		if field_type is UNDEFINED:
			schema   = cls._get_class_schema(field_cls, defs, stack)
			nullable = False
		else:
			if isinstance(field_type, o.Annotation):
				annotation = field_type
			else:
				annotation = o.Annotation(field_type)

			schema   = cls._get_annotation_schema(annotation, defs, stack)
			nullable = annotation.is_optional

		default  = getattr(field, 'default', UNDEFINED)
		nullable = nullable or default is None

		if nullable:
			schema = cls._make_nullable(schema)

		required = default is UNDEFINED and not nullable

		return schema, required

	# Merge inherited field view
	# ----------------------------------------------------------------------
	@classmethod
	def _get_fields(cls, t_cls):
		fields = {}

		for base in reversed(t_cls.__mro__):
			namespace = base.__dict__.get('_')

			if namespace is not None:
				fields.update(namespace.items())

		return fields

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
		schema_type = schema.get('type', UNDEFINED)

		if schema_type is not UNDEFINED:
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

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Build class schema
	# ----------------------------------------------------------------------
	@classmethod
	def build(cls, t_cls):
		if t_cls is not o.T:
			defs   = {}
			schema = cls._get_root_schema(t_cls, defs, ())

			if defs:
				schema = {**schema, '$defs' : defs}
		else:
			raise TypeError('`o.T` has no single JSON schema')

		return schema
