import os
import shutil
import tempfile

import lmdb
import o

UNDEFINED = o.Undefined
Tester    = o.Tester


# Patch registry for source-backed classes
# ----------------------------------------------------------------------
@classmethod
def _patch_registry(cls):
	services = o.services
	registry = type('RegistryState', (), {})()
	state    = {
		'services'     : services,
		'had_registry' : 'Registry' in services.__dict__,
		'registry'     : services.__dict__.get('Registry'),
		'paths'        : {},
	}

	def add(id, path):
		state['paths'][id] = path

	def remove(id):
		if id in state['paths']:
			del state['paths'][id]

	def get(id):
		return state['paths'].get(id, UNDEFINED)

	registry.add    = add
	registry.remove = remove
	registry.get    = get

	services.Registry = registry

	return state


# Restore original registry
# ----------------------------------------------------------------------
@classmethod
def _restore_registry(cls, state):
	services = state['services']

	if state['had_registry']:
		services.Registry = state['registry']
	else:
		del services.Registry


# Switch existing runtime memory store
# ----------------------------------------------------------------------
@classmethod
def _switch_store(cls, data_dir):
	memory = o.services.Memory
	path   = os.path.realpath(os.path.join(o.__path__, data_dir))

	if 'env' in memory.__dict__:
		memory.env.close()

	os.makedirs(os.path.dirname(path), exist_ok=True)

	o.DATA_DIR    = data_dir
	memory.path   = path
	memory.size   = o.MEMORY_SIZE
	memory.env    = lmdb.open(path, create=True, lock=True, map_size=memory.size, max_dbs=1, subdir=True)
	memory._read  = None
	memory._write = None

	for entity in o.__entities__.values():
		if '__zone__' in entity.__dict__:
			entity.__zone__.cache.clear()


# Switch runtime memory to isolated cloned store
# ----------------------------------------------------------------------
@classmethod
def _patch_store(cls, prefix):
	temp_root = os.path.join(o.__path__, '__tmp__')
	root      = None
	data_dir  = None
	dst_path  = None
	old_path  = getattr(o.services.Memory, 'path', UNDEFINED)
	state     = {
		'data_dir'   : o.DATA_DIR,
		'initialize' : o.__dict__.get('initialize', UNDEFINED),
		'temp_root'  : temp_root,
		'root'       : UNDEFINED,
	}

	os.makedirs(temp_root, exist_ok=True)

	root                  = tempfile.mkdtemp(prefix=prefix, dir=temp_root)
	data_dir              = os.path.join('__tmp__', os.path.basename(root))
	dst_path              = os.path.realpath(os.path.join(o.__path__, data_dir))
	state['root']         = root
	state['data_dir_new'] = data_dir

	if old_path is not UNDEFINED and os.path.isdir(old_path):
		shutil.rmtree(root)
		shutil.copytree(old_path, dst_path)

	cls._switch_store(data_dir)
	o.__dict__['initialize'] = o.ensure_value

	return state


# Restore original runtime memory
# ----------------------------------------------------------------------
@classmethod
def _restore_store(cls, state):
	if state['initialize'] is UNDEFINED:
		if 'initialize' in o.__dict__:
			del o.__dict__['initialize']
	else:
		o.__dict__['initialize'] = state['initialize']

	cls._switch_store(state['data_dir'])

	if os.path.isdir(state['root']):
		shutil.rmtree(state['root'])

	temp_root = state['temp_root']

	if os.path.isdir(temp_root) and not os.listdir(temp_root):
		os.rmdir(temp_root)


# Patch isolated runtime
# ----------------------------------------------------------------------
@classmethod
def _patch_runtime(cls):
	runtime_state  = cls._patch_store(cls.RUNTIME_PREFIX)
	registry_state = cls._patch_registry()
	state          = {
		'root'     : runtime_state['root'],
		'temp_root': runtime_state['temp_root'],
		'registry' : registry_state,
		'runtime'  : runtime_state,
		'entities' : dict(o.__entities__),
		'cast_map' : dict(o.__cast_map__),
		'value'    : o.__dict__.get('V', UNDEFINED),
	}

	return state


# Restore isolated runtime
# ----------------------------------------------------------------------
@classmethod
def _restore_runtime(cls, state):
	o.__entities__.clear()
	o.__entities__.update(state['entities'])

	o.__cast_map__.clear()
	o.__cast_map__.update(state['cast_map'])

	if state['value'] is UNDEFINED:
		if 'V' in o.__dict__:
			del o.__dict__['V']
	else:
		o.__dict__['V'] = state['value']

	cls._restore_store(state['runtime'])
	cls._restore_registry(state['registry'])


Tester.RUNTIME_PREFIX    = 'o_test_'
Tester._patch_registry   = _patch_registry
Tester._restore_registry = _restore_registry
Tester._switch_store     = _switch_store
Tester._patch_store      = _patch_store
Tester._restore_store    = _restore_store
Tester._patch_runtime    = _patch_runtime
Tester._restore_runtime  = _restore_runtime
