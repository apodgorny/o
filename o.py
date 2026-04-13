import sys, os, re

from weakref       import WeakValueDictionary as weakdict
from collections   import defaultdict

from whitelabel.wl import WL


def initialize(o):
	os.makedirs(os.path.join(o.core_path, o.DATA_DIR), exist_ok=True)
	o.F
	for module in o:
		if not module.name.startswith('_'):
			module.load()

def get(o, id_or_proto):
	entity = o.undefined
	proto  = o.undefined

	if isinstance(id_or_proto, int):
		entity = o.__entities__.get(id_or_proto, o.undefined)
		if entity is o.undefined:
			proto = o.id_to_proto(id_or_proto)

	elif isinstance(id_or_proto, str):
		proto = id_or_proto

	if proto is not o.undefined:
		entity = eval(proto)

	return entity

def is_instance_version(o, s):
	return re.fullmatch(r'_[0-9]+', s) is not None

def is_class_name(o, s):
	return re.fullmatch(r'[A-Z][A-Za-z0-9_]*', s) is not None

def is_atomic(o, id):
	proto     = o.id_to_proto(id)
	is_atomic = False

	if proto is not o.undefined:
		is_atomic = proto.startswith('o.T.Atom')

	return is_atomic

def id_to_path(o, id):
	return o.services.Registry.get(id)

def id_to_proto(o, id):
	path  = o.services.Registry.get(id)
	proto = o.undefined

	if path is not o.undefined:
		proto = o.path_to_proto(path)

	return proto

def proto_to_id(o, proto):
	return o.String.hash(proto, 15)

def exists(o, proto_or_id):
	if isinstance(proto_or_id, int):
		path = o.id_to_path(proto_or_id)
	else:
		path = o.proto_to_path(proto_or_id)

	return os.path.exists(path)

def proto_to_path(o, proto='o.T'):
	proto = proto.removeprefix('o.T')
	items = proto.split('.') if proto else []
	path  = os.path.join(o.core_path, o.DATA_DIR, 'T')

	for item in items:
		if   o.is_instance_version (item) : path += '/__instances__/'  + item
		elif o.is_class_name    (item) : path += '/__subclasses__/' + item

	return path

def path_to_proto(o, path):
	root  = os.path.join(o.core_path, o.DATA_DIR)
	path  = os.path.relpath(path, os.path.join(root, 'T'))
	items = [] if path == '.' else path.split('/')
	proto = 'o.T'

	if items:
		proto += '.' + '.'.join([
		item for item in items if not item.startswith('__')
		])

	return proto

def path_to_id(o, path):
	proto = o.path_to_proto(path)
	return o.proto_to_id(proto)

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


o = WL.define(
	'o',
	__file__,

	DATA_DIR = '_',

	# SOT – holds strong refernces
	# - - - - - - - - - - - - - - - - - -
	__entities__ = {},  # id => entity strong reference

	# SOT – rules of casting from python
	# - - - - - - - - - - - - - - - - - -
	__cast_map__ = {},  # Annotation => o.T subclass

	on_initialize    = initialize,

	get              = get,
	is_instance_version = is_instance_version,
	is_class_name    = is_class_name,
	is_atomic        = is_atomic,

	id_to_path       = id_to_path,
	id_to_proto      = id_to_proto,
	proto_to_id      = proto_to_id,
	exists           = exists,
	proto_to_path    = proto_to_path,
	path_to_proto    = path_to_proto,
	path_to_id       = path_to_id,

	register_entity  = register_entity,
)
