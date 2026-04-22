import os, re

from llm import LLM


class O(LLM, plugins=['Py']):

	DATA_DIR = '_'

	__entities__     = {}  # id          =>  entity strong reference
	__disk_classes__ = {}  # id          =>  o.disk.Class
	__cast_map__     = {}  # Annotation  =>  o.T subclass

	# Initialize library
	# ----------------------------------------------------------------------
	def initialize(o):
		os.makedirs(os.path.join(o.__path__, o.DATA_DIR), exist_ok=True)

		for item in o:
			if not item.is_directory:
				item.load()

		o.ensure_value()
		o.services.GC.sweep()

	# Get entity by id or proto
	# ----------------------------------------------------------------------
	def get(o, id_or_proto):
		entity = o.Undefined
		proto  = o.Undefined

		if isinstance(id_or_proto, int):
			entity = o.__entities__.get(id_or_proto, o.Undefined)
			if entity is o.Undefined:
				proto = o.id_to_proto(id_or_proto)

		elif isinstance(id_or_proto, str):
			proto = id_or_proto

		if proto is not o.Undefined:
			entity = eval(proto)

		return entity

	# Check instance version token
	# ----------------------------------------------------------------------
	def is_instance_version(o, s):
		return re.fullmatch(r'_[0-9]+', s) is not None

	# Check class name token
	# ----------------------------------------------------------------------
	def is_class_name(o, s):
		return re.fullmatch(r'[A-Z][A-Za-z0-9_]*', s) is not None

	# Check whether entity is atomic
	# ----------------------------------------------------------------------
	def is_atomic(o, id):
		proto     = o.id_to_proto(id)
		is_atomic = False

		if proto is not o.Undefined:
			is_atomic = proto.startswith('o.T.Atom')

		return is_atomic

	# Resolve path by id
	# ----------------------------------------------------------------------
	def id_to_path(o, id):
		return o.services.Registry.get(id)

	# Resolve proto by id
	# ----------------------------------------------------------------------
	def id_to_proto(o, id):
		path  = o.services.Registry.get(id)
		proto = o.Undefined

		if path is not o.Undefined:
			proto = o.path_to_proto(path)

		return proto

	# Hash proto into id
	# ----------------------------------------------------------------------
	def proto_to_id(o, proto):
		return o.String.hash(proto, 15)

	# Check whether proto or id exists on disk
	# ----------------------------------------------------------------------
	def exists(o, proto_or_id):
		if isinstance(proto_or_id, int):
			path = o.id_to_path(proto_or_id)
		else:
			path = o.proto_to_path(proto_or_id)

		return os.path.exists(path)

	# Resolve proto into disk path
	# ----------------------------------------------------------------------
	def proto_to_path(o, proto='o.T'):
		proto = proto.removeprefix('o.T')
		items = proto.split('.') if proto else []
		path  = os.path.join(o.__path__, o.DATA_DIR, 'T')

		for item in items:
			if   o.is_instance_version (item) : path += '/__instances__/'  + item
			elif o.is_class_name       (item) : path += '/__subclasses__/' + item

		return path

	# Resolve route by proto
	# ----------------------------------------------------------------------
	def proto_to_route(o, proto):
		return o.disk.Class.get(proto).route

	# Resolve disk path into proto
	# ----------------------------------------------------------------------
	def path_to_proto(o, path):
		root  = os.path.join(o.__path__, o.DATA_DIR)
		path  = os.path.relpath(path, os.path.join(root, 'T'))
		items = [] if path == '.' else path.split('/')
		proto = 'o.T'

		if items:
			proto += '.' + '.'.join([
			item for item in items if not item.startswith('__')
			])

		return proto

	# Resolve disk path into id
	# ----------------------------------------------------------------------
	def path_to_id(o, path):
		proto = o.path_to_proto(path)
		return o.proto_to_id(proto)

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

	# Ensure root value instance exists
	# ----------------------------------------------------------------------
	def ensure_value(o):
		value       = o.__dict__.get('V', o.Undefined)
		value_path  = o.Undefined

		if value is o.Undefined:
			o.V

		value_proto = f'{o.T.V.__proto__}._0'

		if value is not o.Undefined:
			value_path = o.id_to_path(value.id)

		if value_path is o.Undefined:
			if o.exists(value_proto):
				value = o.get(value_proto)
			else:
				value = o.T.V()

			o.__dict__['V'] = value

		return value

o.initialize()
