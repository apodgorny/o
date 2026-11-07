# ==============================================================================
# ENTITY SERVICE
# ==============================================================================
# Resolve persistent entities and convert them to Python-facing values.
# ==============================================================================

import o

UNDEFINED = o.Undefined


class Entity(o.Service):

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Resolve an entity by cached id or proto, loading it on a cache miss.
	# ----------------------------------------------------------------------
	def get(self, id_or_proto):
		entity = o.services.Cache.entities.get(id_or_proto, UNDEFINED)
		proto  = UNDEFINED

		if entity is UNDEFINED:
			if   isinstance(id_or_proto, int) : proto = o.services.Id.get(id_or_proto, UNDEFINED)
			elif isinstance(id_or_proto, str) : proto = id_or_proto

		if proto is not UNDEFINED:
			entity = eval(proto)

		return entity

	# Resolve an entity class associated with a Python type annotation.
	# ----------------------------------------------------------------------
	def get_by_annotation(self, annotation):
		entity = UNDEFINED
		proto  = o.services.Cache.cast_map.get(annotation, UNDEFINED)

		if proto is not UNDEFINED:
			entity = self.get(proto)

		return entity

	# Unwrap atomic entities while leaving non-atomic entities intact.
	# ----------------------------------------------------------------------
	def value(self, id):
		entity = self.get(id)
		value  = entity

		if entity is not UNDEFINED:
			if entity.__class__.__is_atom__:
				value = entity.__value__

		return value

	# Convert a Python value to the required ontology type.
	# ----------------------------------------------------------------------
	def cast(self, type_cls, value):
		annotation = getattr(type_cls, '__annotation__', UNDEFINED)
		result     = value

		if not isinstance(value, type_cls):
			if isinstance(value, o.T):
				value = value.to_data_shallow()

			if type_cls is o.T:
				result = o.T(value)
			elif annotation is UNDEFINED:
				if not isinstance(value, dict):
					raise TypeError(f'Cannot cast `{type(value)}` into `{type_cls.__proto__}`')

				result = type_cls(**value)
			else:
				if not isinstance(annotation, o.Annotation):
					annotation = o.Annotation(annotation)

				if annotation.is_atomic:
					value = annotation.cast(value)

				result = type_cls(value)

		return result

	# Check whether a class, instance or route exists in persistent storage.
	# ----------------------------------------------------------------------
	def exists(self, proto_or_route_or_id):
		does_exist = False
		proto      = proto_or_route_or_id

		if isinstance(proto_or_route_or_id, str):
			does_exist = o.services.Route.has(proto_or_route_or_id)

		if not does_exist:
			if isinstance(proto_or_route_or_id, int):
				proto = o.services.Id.get(proto_or_route_or_id, UNDEFINED)

			if proto is not UNDEFINED:
				does_exist = o.services.Memory.has(proto)

		return does_exist

	# Ensure that the root value is present without constructing it twice.
	# ----------------------------------------------------------------------
	def ensure_value(self):
		value = o.__dict__.get('V', UNDEFINED)

		if not isinstance(value, o.T.V):
			proto = f'{o.T.V.__proto__}._0'
			value = self.get(proto) if self.exists(proto) else o.T.V()
			o.__dict__['V'] = value

		return value
