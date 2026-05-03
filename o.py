import re

from a import A

UNDEFINED = A.Undefined


class O(A, plugins=['Py']):

	DATA_DIR    = '__memory__'
	MEMORY_SIZE = 1073741824

	__entities__ = {}  # id => entity strong reference
	__cast_map__ = {}  # Annotation => o.T subclass

	# Initialize library
	# ----------------------------------------------------------------------
	def initialize(o):
		for item in o:
			if not item.is_directory:
				item.load()

		o.services.Memory.initialize()

	# Get entity by id or proto
	# ----------------------------------------------------------------------
	def get(o, id_or_proto):
		entity = UNDEFINED
		proto  = UNDEFINED

		if isinstance(id_or_proto, int):
			entity = o.__entities__.get(id_or_proto, UNDEFINED)
			if entity is UNDEFINED:
				proto = o.id_to_proto(id_or_proto)

		elif isinstance(id_or_proto, str):
			proto = id_or_proto

		if proto is not UNDEFINED:
			entity = eval(proto)

		return entity

	# Get Python-visible value by id
	# ----------------------------------------------------------------------
	def value(o, id):
		entity = o.get(id)
		value  = entity

		if entity is not UNDEFINED:
			if entity.__class__.__is_atom__:
				value = entity.__value__

		return value

	# Check instance version token
	# ----------------------------------------------------------------------
	def is_instance_version(o, s):
		return re.fullmatch(r'_[0-9]+', s) is not None

	# Check class name token
	# ----------------------------------------------------------------------
	def is_class_name(o, s):
		return re.fullmatch(r'([A-Z][A-Za-z0-9_]*|__temp_[0-9a-f]+)', s) is not None

	# Check temp class name token
	# ----------------------------------------------------------------------
	def is_temp_class_name(o, s):
		return re.fullmatch(r'__temp_[0-9a-f]+', s) is not None

	# Hash proto into id
	# ----------------------------------------------------------------------
	def proto_to_id(o, proto):
		return o.String.hash(proto, 15)

	# Resolve proto by id
	# ----------------------------------------------------------------------
	def id_to_proto(o, id):
		return o.services.Memory.get(str(id), UNDEFINED)

	# Check whether proto exists in memory
	# ----------------------------------------------------------------------
	def exists(o, proto_or_id):
		result = False
		proto  = proto_or_id

		if isinstance(proto_or_id, int):
			proto = o.id_to_proto(proto_or_id)

		if proto is not UNDEFINED:
			result = o.services.Memory.has(proto)

		return result

	# Register loaded entity
	# ----------------------------------------------------------------------
	def register_entity(o, entity):
		if entity.id not in o.__entities__:
			if isinstance(entity, type):
				if '__annotation__' in entity.__dict__:
					annotation = entity.__annotation__.annotation
					if annotation not in o.__cast_map__:
						o.__cast_map__[annotation] = entity
					else:
						other_proto = o.__cast_map__[annotation].__proto__
						raise TypeError(f'Annotation `{annotation}` is already defined in `{other_proto}`')

			o.__entities__[entity.id] = entity

	# Unregister loaded entity
	# ----------------------------------------------------------------------
	def unregister_entity(o, entity):
		if entity.id in o.__entities__:
			if isinstance(entity, type):
				if '__annotation__' in entity.__dict__:
					annotation = entity.__annotation__.annotation

					if annotation in o.__cast_map__:
						if o.__cast_map__[annotation].id == entity.id:
							del o.__cast_map__[annotation]

			del o.__entities__[entity.id]

	# Ensure singleton root value
	# ----------------------------------------------------------------------
	def ensure_value(o):
		value = o.__dict__.get('V', UNDEFINED)

		if not isinstance(value, o.T.V):
			value = o.T.V()
			o.__dict__['V'] = value

		return value

	# Resolve source route metadata
	# ----------------------------------------------------------------------
	def get_route(o, route, default=None):
		return o.services.Memory.get(route, default)

	# Resolve source route by proto
	# ----------------------------------------------------------------------
	def proto_to_route(o, proto):
		route = o.services.Memory.get(f'{proto}.__route__', UNDEFINED)

		return route

	# Check source route metadata
	# ----------------------------------------------------------------------
	def has_route(o, route):
		return o.services.Memory.has(route)


o.initialize()
