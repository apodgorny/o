import json, jsonschema

import o


UNDEFINED = o.Undefined
SCHEMA    = o.json.SerializerSchema


class Deserializer(o.Module):

	# Init 
	# ----------------------------------------------------------------------
	def __init__(self, spec):
		self._spec    = spec
		self.instance = UNDEFINED

		self._resolved_classes  = set()
		self._resolving_classes = set()

		self._resolve_classes()
		self._process_instances()

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Resolve
	# ----------------------------------------------------------------------
	def _resolve_classes(self):
		result = False
		for cls_proto in self._spec['classes']:
			if cls_proto not in self._resolved_classes:
				result = True if self._resolve_class(cls_proto) else result
		return result

	# Resolve
	# ----------------------------------------------------------------------
	def _resolve_class(self, cls_proto):
		result = False

		if cls_proto in self._resolved_classes:
			result = True
		elif cls_proto in self._resolving_classes:
			raise TypeError(f'Class dependency cycle at `{cls_proto}`')
		else:
			self._resolving_classes.add(cls_proto)
			if cls_proto not in self._spec['classes']:
				raise TypeError(f'Missing definition for `{cls_proto}`')
			
			if not o.exists(cls_proto):
				base_proto, cls_name = cls_proto.rsplit('.', 1)
				if not o.exists(base_proto):
					self._resolve_class(base_proto)

				cls_spec = self._spec['classes'][cls_proto]

				for field_name in cls_spec:
					type_proto = cls_spec[field_name]['type']
					if not o.exists(type_proto):
						self._resolve_class(type_proto)

				self._define_class(base_proto, cls_name, cls_spec)
			else:
				self.note(f'Class `{cls_proto}` already exists, skipping')

			self._resolving_classes.remove(cls_proto)
			self._resolved_classes.add(cls_proto)
			result = True

		return result

	# Define class
	# ----------------------------------------------------------------------
	def _define_class(self, base_proto, cls_name, spec):
		base_cls = o.get(base_proto)
		fields   = {}

		for field_name, field_props in spec.items():
			props = dict(field_props)

			props['type'] = o.get(props['type'])

			if 'default' not in props:
				props['default'] = None

			fields[field_name] = o.F(**props)

		base_cls.extend(cls_name, **fields)

	# Resolve
	# ----------------------------------------------------------------------
	def _process_instances(self):
		self.instance = self._define_instance(self._spec['instance'])

	# Resolve
	# ----------------------------------------------------------------------
		# Define instance
	# ----------------------------------------------------------------------
	def _define_instance(self, spec):
		result = spec

		if isinstance(spec, dict):
			if '__class__' in spec:
				cls    = o.get(spec['__class__'])
				value  = UNDEFINED
				kwargs = {}

				for name, item in spec.items():
					if name in ['__value__', '__items__']:
						value = self._define_instance(item)
					elif name != '__class__':
						kwargs[name] = self._define_instance(item)

				result = cls(**kwargs) if value is UNDEFINED else cls(value, **kwargs)
			else:
				result = {}
				for name, item in spec.items():
					result[name] = self._define_instance(item)

		elif isinstance(spec, list):
			result = []
			for item in spec:
				result.append(self._define_instance(item))

		return result

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Deserialize spec into class or instance
	# ----------------------------------------------------------------------
	@classmethod
	def deserialize(cls, spec):
		jsonschema.validate(spec, SCHEMA)
		return Deserializer(spec).instance