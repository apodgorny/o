import o


UNDEFINED = o.Undefined


class Serializer(o.Module):

	# Serialize value
	# ----------------------------------------------------------------------
	@classmethod
	def serialize(cls, value):
		context = {
			'classes': {},
		}

		instance = cls._serialize_instance(value, context)

		return {
			'classes'  : context['classes'],
			'instance' : instance,
		}

	# Serialize instance
	# ----------------------------------------------------------------------
	@classmethod
	def _serialize_instance(cls, value, context):
		spec = {
			'__class__': value.__class__.__proto__,
		}

		cls._collect_class(value.__class__, context)

		if hasattr(value.__class__, '__annotation__'):
			spec['__items__'] = cls._serialize_value(value.__cast_out__(), context)

		for name, child_proto, child in value.__dependants__():
			if isinstance(name, str) and value.__class__.__has_field__(name):
				spec[name] = cls._serialize_value(child, context)

		return spec

	# Serialize value
	# ----------------------------------------------------------------------
	@classmethod
	def _serialize_value(cls, value, context):
		result = value

		if isinstance(value, o.T):
			result = cls._serialize_instance(value, context)
			annotation = getattr(value.__class__, '__annotation__', UNDEFINED)

			if annotation is not UNDEFINED and value.__class__.__name__.startswith('Generic_'):
				annotation = o.Annotation(annotation)

				if annotation.is_list or annotation.is_dict:
					result['__class__'] = o.get_by_annotation(annotation.origin).__proto__

		elif isinstance(value, dict):
			result = {}

			for key, item in value.items():
				result[key] = cls._serialize_value(item, context)

		elif isinstance(value, list):
			result = []

			for item in value:
				result.append(cls._serialize_value(item, context))

		return result

	# Collect class
	# ----------------------------------------------------------------------
	@classmethod
	def _collect_class(cls, target_cls, context):
		proto = target_cls.__proto__

		if proto not in context['classes']:
			spec = {}

			for name, field in target_cls._.items():
				type_cls = field.type

				if not isinstance(type_cls, type):
					type_cls = o.get(type_cls)

				field_spec = {
					'type': type_cls.__proto__,
				}

				default = getattr(field, 'default', UNDEFINED)

				if default is not UNDEFINED and default is not None:
					field_spec['default'] = cls._serialize_value(default, context)

				description = getattr(field, 'description', UNDEFINED)

				if isinstance(description, str):
					field_spec['description'] = description

				spec[name] = field_spec

			context['classes'][proto] = spec
