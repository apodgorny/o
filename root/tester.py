import os
import shutil
import tempfile

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


# Switch runtime memory to isolated cloned store
# ----------------------------------------------------------------------
@classmethod
def _patch_store(cls, prefix):
	temp_root = os.path.join(o.__path__, '__tmp__')
	memory    = o.services.Memory
	root      = None
	data_dir  = None
	dst_path  = None
	state     = {
		'memory'    : memory,
		'data_dir'  : o.DATA_DIR,
		'old_path'  : getattr(memory, 'path', UNDEFINED),
		'old_size'  : getattr(memory, 'size', UNDEFINED),
		'temp_root' : temp_root,
		'root'      : UNDEFINED,
	}

	os.makedirs(temp_root, exist_ok=True)

	root                  = tempfile.mkdtemp(prefix=prefix, dir=temp_root)
	data_dir              = os.path.join('__tmp__', os.path.basename(root))
	dst_path              = os.path.realpath(os.path.join(o.__path__, data_dir))
	state['root']         = root
	state['data_dir_new'] = data_dir

	if 'env' in memory.__dict__:
		memory.env.close()

	if state['old_path'] is not UNDEFINED and os.path.isdir(state['old_path']):
		shutil.rmtree(root)
		shutil.copytree(state['old_path'], dst_path)

	o.DATA_DIR = data_dir
	memory.initialize()

	return state


# Restore original runtime memory
# ----------------------------------------------------------------------
@classmethod
def _restore_store(cls, state):
	memory = state['memory']

	if 'env' in memory.__dict__:
		memory.env.close()

	o.DATA_DIR = state['data_dir']

	if state['old_path'] is not UNDEFINED:
		memory.path = state['old_path']

	if state['old_size'] is not UNDEFINED:
		memory.size = state['old_size']

	memory.initialize()

	if os.path.isdir(state['root']):
		shutil.rmtree(state['root'])


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
Tester._patch_store      = _patch_store
Tester._restore_store    = _restore_store
Tester._patch_runtime    = _patch_runtime
Tester._restore_runtime  = _restore_runtime
