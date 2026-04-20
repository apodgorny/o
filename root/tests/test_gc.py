import gc
import os
import shutil
import struct
import tempfile

import o


class TestGc(o.Test):

	# ----------------------------------------------------------------------
	@classmethod
	def _patch_registry(cls):
		services = o.services
		registry = type('RegistryState', (), {})()
		capacity = 1024
		slot_size = 256
		id_size = 8
		state    = {
			'services'     : services,
			'had_registry' : 'Registry' in services.__dict__,
			'registry'     : services.__dict__.get('Registry'),
			'paths'        : {},
		}

		def add(id, path):
			offset = (id % capacity) * slot_size

			state['paths'][id] = path
			registry._view[offset : offset + id_size] = struct.pack('<Q', id)

		def remove(id):
			offset = (id % capacity) * slot_size

			if id in state['paths']:
				del state['paths'][id]

			registry._view[offset : offset + id_size] = b'\x00' * id_size

		def get(id):
			return state['paths'].get(id, o.Undefined)

		registry.add    = add
		registry.remove = remove
		registry.get    = get
		registry.CAPACITY  = capacity
		registry.SLOT_SIZE = slot_size
		registry.ID_SIZE   = id_size
		registry._view     = bytearray(capacity * slot_size)

		services.Registry = registry

		return state

	# ----------------------------------------------------------------------
	@classmethod
	def _restore_registry(cls, state):
		services = state['services']

		if state['had_registry']:
			services.Registry = state['registry']
		else:
			del services.Registry

	# ----------------------------------------------------------------------
	@classmethod
	def _patch_runtime(cls):
		temp_root      = os.path.join(o.__path__, '__tmp__')
		registry_state = cls._patch_registry()

		os.makedirs(temp_root, exist_ok=True)

		root = tempfile.mkdtemp(prefix='o_gc_', dir=temp_root)

		state = {
			'root'      : root,
			'temp_root' : temp_root,
			'registry'  : registry_state,
			'data_dir'  : o.DATA_DIR,
			'entities'  : dict(o.__entities__),
			'disk_classes' : dict(o.__disk_classes__),
			'cast_map'  : dict(o.__cast_map__),
			'value'     : o.__dict__.get('V', o.Undefined),
		}

		o.DATA_DIR = os.path.join('__tmp__', os.path.basename(root))

		return state

	# ----------------------------------------------------------------------
	@classmethod
	def _restore_runtime(cls, state):
		o.DATA_DIR = state['data_dir']

		o.__entities__.clear()
		o.__entities__.update(state['entities'])

		o.__disk_classes__.clear()
		o.__disk_classes__.update(state['disk_classes'])

		o.__cast_map__.clear()
		o.__cast_map__.update(state['cast_map'])

		if state['value'] is o.Undefined:
			if 'V' in o.__dict__:
				del o.__dict__['V']
		else:
			o.__dict__['V'] = state['value']

		cls._restore_registry(state['registry'])

		if os.path.exists(state['root']):
			shutil.rmtree(state['root'])

		if os.path.isdir(state['temp_root']):
			shutil.rmtree(state['temp_root'])

	# ----------------------------------------------------------------------
	@classmethod
	def _drop_loaded(cls, id):
		if id in o.__entities__:
			del o.__entities__[id]

	# ----------------------------------------------------------------------
	@classmethod
	def _assert_alive(cls, id):
		path = o.id_to_path(id)

		assert path is not o.Undefined
		assert os.path.exists(path) == True

	# ----------------------------------------------------------------------
	@classmethod
	def _assert_released(cls, id):
		assert o.id_to_path(id) is o.Undefined

	# ----------------------------------------------------------------------
	@classmethod
	def test_python_gc_does_not_delete_disk_entity(cls):
		state = cls._patch_runtime()

		try:
			GCProbe = o.T.extend('GCProbe', foo=str)

			x    = GCProbe(foo='hello')
			id   = x.id
			path = x.__disk_instance__.path

			assert id in o.__entities__
			assert os.path.exists(path) == True

			del x
			gc.collect()

			assert os.path.exists(path) == True
			assert o.get(id).id == id
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_ensure_value_returns_singleton_root_instance(cls):
		first  = o.ensure_value()
		second = o.ensure_value()

		assert first is second
		assert isinstance(first, o.T.V)
		assert o.id_to_path(first.id) is not o.Undefined

	# ----------------------------------------------------------------------
	@classmethod
	def test_startup_sweep_releases_orphan_and_keeps_value_attached_child(cls):
		root      = o.ensure_value()
		orphan    = o.T('orphan')
		attached  = o.T('attached')
		orphan_id = orphan.id
		attached_id = attached.id

		try:
			root.keepgcprobe = attached

			o.services.GC.sweep()

			cls._assert_released(orphan_id)
			cls._assert_alive(attached_id)
			assert root.keepgcprobe == 'attached'
		finally:
			if hasattr(root, 'keepgcprobe'):
				del root.keepgcprobe

	# ----------------------------------------------------------------------
	@classmethod
	def test_value_attached_instance_restores_form_and_values_after_reload(cls):
		state = cls._patch_runtime()

		try:
			root = o.ensure_value()
			name = 'rootreloadgcprobe'
			ValueAttachedListPath = o.T.extend('ValueAttachedListPath', list[int])
			ValueAttachedDictPath = o.T.extend('ValueAttachedDictPath', dict[str, str])
			ValueAttachedInstanceRestoresFormAndValuesAfterReload = o.T.extend(
				'ValueAttachedInstanceRestoresFormAndValuesAfterReload',
				name=str,
			)

			x       = ValueAttachedInstanceRestoresFormAndValuesAfterReload(name='alex')
			x.items = ValueAttachedListPath([1, 2])
			x.meta  = ValueAttachedDictPath({'lang': 'uk'})

			setattr(root, name, x)

			class_id     = ValueAttachedInstanceRestoresFormAndValuesAfterReload.id
			id           = x.id
			proto        = x.__proto__
			version      = x.__version__
			list_id      = x.__disk_instance__.attributes.get('items')
			dict_id      = x.__disk_instance__.attributes.get('meta')
			list_version = o.get(list_id).__version__
			dict_version = o.get(dict_id).__version__

			if name in root.__dict__:
				del root.__dict__[name]

			for entity_id in [class_id, id, list_id, dict_id]:
				cls._drop_loaded(entity_id)

			reopened_by_id    = o.get(id)
			reopened_by_proto = o.get(proto)
			reopened_by_tree  = getattr(o.T.ValueAttachedInstanceRestoresFormAndValuesAfterReload, version)
			reopened_by_root  = getattr(root, name)
			reopened_list     = getattr(ValueAttachedListPath, list_version)
			reopened_dict     = getattr(ValueAttachedDictPath, dict_version)

			assert reopened_by_id.__class__.__proto__ == 'o.T.ValueAttachedInstanceRestoresFormAndValuesAfterReload'
			assert reopened_by_id.id == id
			assert reopened_by_id.name == 'alex'
			assert list(reopened_by_id.items) == [1, 2]
			assert dict(reopened_by_id.meta.items()) == {'lang': 'uk'}

			assert reopened_by_proto.id == id
			assert reopened_by_proto.__proto__ == proto

			assert reopened_by_tree.id == id
			assert reopened_by_tree.__version__ == version

			assert reopened_by_root.id == id
			assert reopened_by_root.name == 'alex'
			assert list(reopened_by_root.items) == [1, 2]
			assert dict(reopened_by_root.meta.items()) == {'lang': 'uk'}

			assert reopened_list.id == list_id
			assert reopened_list.__proto__ == f'{ValueAttachedListPath.__proto__}.{list_version}'
			assert list(reopened_list) == [1, 2]

			assert reopened_dict.id == dict_id
			assert reopened_dict.__proto__ == f'{ValueAttachedDictPath.__proto__}.{dict_version}'
			assert dict(reopened_dict.items()) == {'lang': 'uk'}
		finally:
			if 'root' in locals() and root.__disk_instance__.attributes.has(name):
				delattr(root, name)
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_unattached_instance_is_gone_after_startup_sweep(cls):
		state = cls._patch_runtime()

		try:
			UnattachedInstanceIsGoneAfterStartupSweep = o.T.extend(
				'UnattachedInstanceIsGoneAfterStartupSweep',
				name=str,
			)

			x       = UnattachedInstanceIsGoneAfterStartupSweep(name='orphan')
			x.items = [1, 2]
			x.meta  = {'lang': 'uk'}

			id      = x.id
			proto   = x.__proto__
			list_id = x.__disk_instance__.attributes.get('items')
			dict_id = x.__disk_instance__.attributes.get('meta')

			for entity_id in [id, list_id, dict_id]:
				cls._drop_loaded(entity_id)

			o.services.GC.sweep()

			cls._assert_released(id)
			cls._assert_released(list_id)
			cls._assert_released(dict_id)
			assert o.exists(proto) == False
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_value_delete_releases_attached_leaf(cls):
		root     = o.ensure_value()
		name     = 'rootleafgcprobe'
		child    = o.T('leaf')
		child_id = child.id

		try:
			setattr(root, name, child)

			cls._assert_alive(child_id)
			assert o.services.GC.get(child_id) == 1

			delattr(root, name)

			cls._assert_released(child_id)
		finally:
			if root.__disk_instance__.attributes.has(name):
				delattr(root, name)

	# ----------------------------------------------------------------------
	@classmethod
	def test_value_delete_releases_attached_subtree(cls):
		root      = o.ensure_value()
		name      = 'rootsubtreegcprobe'
		child     = o.List([1, 2])
		child_id  = child.id
		item_0_id = child.__disk_instance__.list.get(0)
		item_1_id = child.__disk_instance__.list.get(1)

		try:
			setattr(root, name, child)

			delattr(root, name)

			cls._assert_released(child_id)
			cls._assert_released(item_0_id)
			cls._assert_released(item_1_id)
		finally:
			if root.__disk_instance__.attributes.has(name):
				delattr(root, name)

	# ----------------------------------------------------------------------
	@classmethod
	def test_value_overwrite_transfers_ownership(cls):
		root        = o.ensure_value()
		name        = 'rootoverwritegcprobe'
		old_child   = o.List([1, 2])
		new_child   = o.List([3])
		old_child_id = old_child.id
		old_item_0   = old_child.__disk_instance__.list.get(0)
		old_item_1   = old_child.__disk_instance__.list.get(1)
		new_child_id = new_child.id
		new_item_0   = new_child.__disk_instance__.list.get(0)

		try:
			setattr(root, name, old_child)
			setattr(root, name, new_child)

			cls._assert_released(old_child_id)
			cls._assert_released(old_item_0)
			cls._assert_released(old_item_1)
			cls._assert_alive(new_child_id)
			cls._assert_alive(new_item_0)
		finally:
			if root.__disk_instance__.attributes.has(name):
				delattr(root, name)

	# ----------------------------------------------------------------------
	@classmethod
	def test_value_shared_child_survives_until_last_binding_removed(cls):
		root     = o.ensure_value()
		name_a   = 'rootsharedagcprobe'
		name_b   = 'rootsharedbgcprobe'
		child    = o.T('shared')
		child_id = child.id

		try:
			setattr(root, name_a, child)
			setattr(root, name_b, child)

			assert o.services.GC.get(child_id) == 2

			delattr(root, name_a)

			cls._assert_alive(child_id)
			assert o.services.GC.get(child_id) == 1

			delattr(root, name_b)

			cls._assert_released(child_id)
		finally:
			if root.__disk_instance__.attributes.has(name_a):
				delattr(root, name_a)

			if root.__disk_instance__.attributes.has(name_b):
				delattr(root, name_b)

	# ----------------------------------------------------------------------
	@classmethod
	def test_attr_mutation_persists_refcount_files(cls):
		state = cls._patch_runtime()

		try:
			AttrRefcountProbe = o.T.extend('AttrRefcountProbe', foo=str)
			x                 = AttrRefcountProbe(foo='hello')
			first_id          = x.__disk_instance__.attributes.get('foo')

			assert o.services.GC.get(first_id) == 1

			x.foo = 'world'

			second_id   = x.__disk_instance__.attributes.get('foo')

			assert first_id != second_id
			assert o.services.GC.get(first_id) == 0
			assert o.services.GC.get(second_id) == 1

			del x.foo

			assert o.services.GC.get(second_id) == 0
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_mutation_persists_refcount_files(cls):
		state = cls._patch_runtime()

		try:
			x         = o.List([1, 2])
			first_id  = x.__disk_instance__.list.get(0)
			second_id = x.__disk_instance__.list.get(1)

			assert o.services.GC.get(first_id) == 1
			assert o.services.GC.get(second_id) == 1

			x[1] = 'b'

			third_id = x.__disk_instance__.list.get(1)

			assert third_id != second_id
			assert o.services.GC.get(second_id) == 0
			assert o.services.GC.get(third_id) == 1

			del x[0]

			assert o.services.GC.get(first_id) == 0
			assert o.services.GC.get(third_id) == 1
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_attr_delete_releases_leaf_child_room(cls):
		state = cls._patch_runtime()

		try:
			LeafReleaseProbe = o.T.extend('LeafReleaseProbe', foo=str)
			x                = LeafReleaseProbe(foo='hello')
			child_id         = x.__disk_instance__.attributes.get('foo')
			child_path       = o.id_to_path(child_id)

			assert os.path.exists(child_path) == True
			assert child_id in o.__entities__

			del x.foo

			assert o.id_to_path(child_id) is o.Undefined
			assert os.path.exists(child_path) == False
			assert child_id not in o.__entities__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_attr_delete_releases_nested_list_cascade(cls):
		state = cls._patch_runtime()

		try:
			CascadeReleaseProbe = o.T.extend('CascadeReleaseProbe', items=list)
			x                   = CascadeReleaseProbe(items=[1, 2])
			list_id             = x.__disk_instance__.attributes.get('items')
			list_path           = o.id_to_path(list_id)
			first_item_id       = o.get(list_id).__disk_instance__.list.get(0)
			second_item_id      = o.get(list_id).__disk_instance__.list.get(1)
			first_item_path     = o.id_to_path(first_item_id)
			second_item_path    = o.id_to_path(second_item_id)

			assert os.path.exists(list_path) == True
			assert os.path.exists(first_item_path) == True
			assert os.path.exists(second_item_path) == True

			del x.items

			assert o.id_to_path(list_id) is o.Undefined
			assert o.id_to_path(first_item_id) is o.Undefined
			assert o.id_to_path(second_item_id) is o.Undefined
			assert os.path.exists(list_path) == False
			assert os.path.exists(first_item_path) == False
			assert os.path.exists(second_item_path) == False
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_attr_delete_releases_nested_dict_cascade(cls):
		state = cls._patch_runtime()

		try:
			CascadeDictReleaseProbe = o.T.extend('CascadeDictReleaseProbe', items=dict)
			x                       = CascadeDictReleaseProbe(items={'x': 'y'})
			dict_id                 = x.__disk_instance__.attributes.get('items')
			dict_path               = o.id_to_path(dict_id)
			dict_items              = o.get(dict_id).__disk_instance__.dict.items
			key_id                  = next(iter(dict_items.keys()))
			value_id                = dict_items[key_id]
			key_path                = o.id_to_path(key_id)
			value_path              = o.id_to_path(value_id)

			assert os.path.exists(dict_path) == True
			assert os.path.exists(key_path) == True
			assert os.path.exists(value_path) == True

			del x.items

			assert o.id_to_path(dict_id) is o.Undefined
			assert o.id_to_path(key_id) is o.Undefined
			assert o.id_to_path(value_id) is o.Undefined
			assert os.path.exists(dict_path) == False
			assert os.path.exists(key_path) == False
			assert os.path.exists(value_path) == False
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_get_children_reads_direct_room_refs(cls):
		state = cls._patch_runtime()

		try:
			root    = o.T({})
			root.foo = 'hello'
			root.bar = [1, 2]
			root.baz = {'x': 'y'}

			foo_id      = root.__disk_instance__.attributes.get('foo')
			bar_id      = root.__disk_instance__.attributes.get('bar')
			baz_id      = root.__disk_instance__.attributes.get('baz')
			bar_item_0  = o.get(bar_id).__disk_instance__.list.get(0)
			bar_item_1  = o.get(bar_id).__disk_instance__.list.get(1)
			baz_items   = o.get(baz_id).__disk_instance__.dict.items
			baz_key_id  = next(iter(baz_items.keys()))
			baz_value_id = baz_items[baz_key_id]

			assert sorted(o.services.GC.get_children(root.id)) == sorted([foo_id, bar_id, baz_id])
			assert sorted(o.services.GC.get_children(bar_id)) == sorted([bar_item_0, bar_item_1])
			assert sorted(o.services.GC.get_children(baz_id)) == sorted([baz_key_id, baz_value_id])
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_attr_overwrite_atomic_releases_old_child_and_keeps_new_alive(cls):
		state = cls._patch_runtime()

		try:
			AttrOverwriteAtomicProbe = o.T.extend('AttrOverwriteAtomicProbe', foo=str)
			x                        = AttrOverwriteAtomicProbe(foo='one')
			old_id                   = x.__disk_instance__.attributes.get('foo')

			x.foo = 'two'

			new_id = x.__disk_instance__.attributes.get('foo')

			cls._assert_released(old_id)
			cls._assert_alive(new_id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_attr_overwrite_list_releases_old_subtree_and_keeps_new_alive(cls):
		state = cls._patch_runtime()

		try:
			AttrOverwriteListProbe = o.T.extend('AttrOverwriteListProbe', items=list)
			x                      = AttrOverwriteListProbe(items=[1, 2])
			old_list_id            = x.__disk_instance__.attributes.get('items')
			old_item_0             = o.get(old_list_id).__disk_instance__.list.get(0)
			old_item_1             = o.get(old_list_id).__disk_instance__.list.get(1)

			x.items = [3]

			new_list_id = x.__disk_instance__.attributes.get('items')
			new_item_0  = o.get(new_list_id).__disk_instance__.list.get(0)

			cls._assert_released(old_list_id)
			cls._assert_released(old_item_0)
			cls._assert_released(old_item_1)
			cls._assert_alive(new_list_id)
			cls._assert_alive(new_item_0)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_attr_overwrite_dict_releases_old_subtree_and_keeps_new_alive(cls):
		state = cls._patch_runtime()

		try:
			AttrOverwriteDictProbe = o.T.extend('AttrOverwriteDictProbe', items=dict)
			x                      = AttrOverwriteDictProbe(items={'a': 'b'})
			old_dict_id            = x.__disk_instance__.attributes.get('items')
			old_items              = o.get(old_dict_id).__disk_instance__.dict.items
			old_key_id             = next(iter(old_items.keys()))
			old_value_id           = old_items[old_key_id]

			x.items = {'c': 'd'}

			new_dict_id  = x.__disk_instance__.attributes.get('items')
			new_items    = o.get(new_dict_id).__disk_instance__.dict.items
			new_key_id   = next(iter(new_items.keys()))
			new_value_id = new_items[new_key_id]

			cls._assert_released(old_dict_id)
			cls._assert_released(old_key_id)
			cls._assert_released(old_value_id)
			cls._assert_alive(new_dict_id)
			cls._assert_alive(new_key_id)
			cls._assert_alive(new_value_id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_item_overwrite_atomic_releases_old_child_and_keeps_new_alive(cls):
		state = cls._patch_runtime()

		try:
			x      = o.List([1])
			old_id = x.__disk_instance__.list.get(0)

			x[0] = 2

			new_id = x.__disk_instance__.list.get(0)

			cls._assert_released(old_id)
			cls._assert_alive(new_id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_item_overwrite_list_releases_old_subtree_and_keeps_new_alive(cls):
		state = cls._patch_runtime()

		try:
			x           = o.List([[1, 2]])
			old_list_id = x.__disk_instance__.list.get(0)
			old_item_0  = o.get(old_list_id).__disk_instance__.list.get(0)
			old_item_1  = o.get(old_list_id).__disk_instance__.list.get(1)

			x[0] = [3]

			new_list_id = x.__disk_instance__.list.get(0)
			new_item_0  = o.get(new_list_id).__disk_instance__.list.get(0)

			cls._assert_released(old_list_id)
			cls._assert_released(old_item_0)
			cls._assert_released(old_item_1)
			cls._assert_alive(new_list_id)
			cls._assert_alive(new_item_0)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_value_overwrite_atomic_keeps_key_and_releases_old_value(cls):
		state = cls._patch_runtime()

		try:
			x            = o.Dict({'a': 'x'})
			items        = x.__disk_instance__.dict.items
			key_id       = next(iter(items.keys()))
			old_value_id = items[key_id]

			x['a'] = 'y'

			new_value_id = x.__disk_instance__.dict.get('a')

			cls._assert_alive(key_id)
			cls._assert_released(old_value_id)
			cls._assert_alive(new_value_id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_value_overwrite_list_keeps_key_and_releases_old_subtree(cls):
		state = cls._patch_runtime()

		try:
			x            = o.Dict({'a': [1, 2]})
			items        = x.__disk_instance__.dict.items
			key_id       = next(iter(items.keys()))
			old_list_id  = items[key_id]
			old_item_0   = o.get(old_list_id).__disk_instance__.list.get(0)
			old_item_1   = o.get(old_list_id).__disk_instance__.list.get(1)

			x['a'] = [3]

			new_list_id = x.__disk_instance__.dict.get('a')
			new_item_0  = o.get(new_list_id).__disk_instance__.list.get(0)

			cls._assert_alive(key_id)
			cls._assert_released(old_list_id)
			cls._assert_released(old_item_0)
			cls._assert_released(old_item_1)
			cls._assert_alive(new_list_id)
			cls._assert_alive(new_item_0)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_value_overwrite_same_entity_keeps_refcount_stable(cls):
		state = cls._patch_runtime()

		try:
			child = o.T('x')
			x     = o.Dict({'a': child})

			assert o.services.GC.get(child.id) == 1

			x['a'] = child

			assert o.services.GC.get(child.id) == 1
			cls._assert_alive(child.id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_same_child_referenced_by_two_attrs_survives_until_last_delete(cls):
		state = cls._patch_runtime()

		try:
			x     = o.T({})
			child = o.T('x')

			x.a = child
			x.b = child

			assert o.services.GC.get(child.id) == 2

			del x.a

			assert o.services.GC.get(child.id) == 1
			cls._assert_alive(child.id)

			del x.b

			cls._assert_released(child.id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_same_child_in_two_list_positions_counts_and_releases_correctly(cls):
		state = cls._patch_runtime()

		try:
			child = o.T('x')
			x     = o.List([child, child])

			assert o.services.GC.get(child.id) == 2

			del x[0]

			assert o.services.GC.get(child.id) == 1
			cls._assert_alive(child.id)

			del x[0]

			cls._assert_released(child.id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_same_child_as_two_dict_values_survives_until_last_delete(cls):
		state = cls._patch_runtime()

		try:
			child = o.T('x')
			x     = o.Dict({'a': child, 'b': child})

			assert o.services.GC.get(child.id) == 2

			del x['a']

			assert o.services.GC.get(child.id) == 1
			cls._assert_alive(child.id)

			del x['b']

			cls._assert_released(child.id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_same_child_shared_between_attr_and_list_survives_until_last_owner_removed(cls):
		state = cls._patch_runtime()

		try:
			root  = o.T({})
			child = o.T('x')

			root.a    = child
			root.items = [child]

			assert o.services.GC.get(child.id) == 2

			del root.a

			assert o.services.GC.get(child.id) == 1
			cls._assert_alive(child.id)

			del root.items

			cls._assert_released(child.id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_shared_subtree_releases_only_after_last_owner_removed(cls):
		state = cls._patch_runtime()

		try:
			root      = o.T({})
			subtree   = o.List([1, 2])
			subtree_id = subtree.id
			item_0    = subtree.__disk_instance__.list.get(0)
			item_1    = subtree.__disk_instance__.list.get(1)

			root.a = subtree
			root.b = subtree

			del root.a

			cls._assert_alive(subtree_id)
			cls._assert_alive(item_0)
			cls._assert_alive(item_1)

			del root.b

			cls._assert_released(subtree_id)
			cls._assert_released(item_0)
			cls._assert_released(item_1)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_same_value_reused_across_different_keys_counts_correctly(cls):
		state = cls._patch_runtime()

		try:
			child = o.T('x')
			x     = o.Dict({'a': child, 'b': child})

			assert o.services.GC.get(child.id) == 2
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_items_rewrite_releases_removed_and_keeps_unchanged_stable(cls):
		state = cls._patch_runtime()

		try:
			keep = o.T('keep')
			drop = o.T('drop')
			new  = o.T('new')
			x    = o.List([])

			x.__disk_instance__.list.items = [keep.id, drop.id]
			x.__disk_instance__.list.items = [keep.id, new.id]

			assert o.services.GC.get(keep.id) == 1
			assert o.services.GC.get(new.id) == 1
			cls._assert_alive(keep.id)
			cls._assert_alive(new.id)
			cls._assert_released(drop.id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_items_rewrite_releases_removed_and_keeps_unchanged_stable(cls):
		state = cls._patch_runtime()

		try:
			keep_key   = o.T('keep')
			keep_value = o.T('value')
			drop_key   = o.T('drop')
			drop_value = o.T('old')
			new_key    = o.T('new')
			new_value  = o.T('fresh')
			x          = o.Dict({})

			x.__disk_instance__.dict.items = {
				keep_key.id : keep_value.id,
				drop_key.id : drop_value.id,
			}

			x.__disk_instance__.dict.items = {
				keep_key.id : keep_value.id,
				new_key.id  : new_value.id,
			}

			assert o.services.GC.get(keep_key.id) == 1
			assert o.services.GC.get(keep_value.id) == 1
			assert o.services.GC.get(new_key.id) == 1
			assert o.services.GC.get(new_value.id) == 1
			cls._assert_released(drop_key.id)
			cls._assert_released(drop_value.id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_items_set_empty_releases_all_children(cls):
		state = cls._patch_runtime()

		try:
			x      = o.List([1, 2])
			id_0   = x.__disk_instance__.list.get(0)
			id_1   = x.__disk_instance__.list.get(1)

			x.__disk_instance__.list.items = []

			cls._assert_released(id_0)
			cls._assert_released(id_1)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_items_set_empty_releases_all_children(cls):
		state = cls._patch_runtime()

		try:
			x         = o.Dict({'a': 'b'})
			items     = x.__disk_instance__.dict.items
			key_id    = next(iter(items.keys()))
			value_id  = items[key_id]

			x.__disk_instance__.dict.items = {}

			cls._assert_released(key_id)
			cls._assert_released(value_id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_released_instance_disappears_from_registry_and_index(cls):
		state = cls._patch_runtime()

		try:
			ReleaseIndexProbe = o.T.extend('ReleaseIndexProbe', foo=str, bar=str)
			x                 = ReleaseIndexProbe(foo='a', bar='b')
			foo               = o.get(x.__disk_instance__.attributes.get('foo'))
			bar               = o.get(x.__disk_instance__.attributes.get('bar'))
			foo_version       = int(foo.__version__[1:])
			bar_version       = int(bar.__version__[1:])
			foo_class         = foo.__class__.__disk_class__
			order             = foo_class.instances.order

			assert foo_version in order
			assert bar_version in order

			del x.foo

			order = o.disk.Instances(foo_class.path).order

			assert o.id_to_path(foo.id) is o.Undefined
			assert foo_version not in order
			assert bar_version in order
			assert o.get(foo.id) is o.Undefined
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_released_child_room_disappears(cls):
		state = cls._patch_runtime()

		try:
			RefcountRoomProbe = o.T.extend('RefcountRoomProbe', foo=str)
			x                 = RefcountRoomProbe(foo='a')
			child_id          = x.__disk_instance__.attributes.get('foo')
			child_path        = o.id_to_path(child_id)

			assert os.path.exists(child_path) == True

			del x.foo

			assert os.path.exists(child_path) == False
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_assigning_same_attr_entity_again_does_not_change_refcount(cls):
		state = cls._patch_runtime()

		try:
			x     = o.T({})
			child = o.T('x')

			x.a = child

			assert o.services.GC.get(child.id) == 1

			x.a = child

			assert o.services.GC.get(child.id) == 1
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_assigning_same_list_entity_again_does_not_change_refcount(cls):
		state = cls._patch_runtime()

		try:
			child = o.T('x')
			x     = o.List([child])

			assert o.services.GC.get(child.id) == 1

			x[0] = child

			assert o.services.GC.get(child.id) == 1
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_assigning_same_dict_value_again_does_not_change_refcount(cls):
		state = cls._patch_runtime()

		try:
			child = o.T('x')
			x     = o.Dict({'a': child})

			assert o.services.GC.get(child.id) == 1

			x['a'] = child

			assert o.services.GC.get(child.id) == 1
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_deleting_absent_attr_raises(cls):
		state = cls._patch_runtime()

		try:
			x      = o.T({})
			raised = False

			try:
				del x.missing
			except AttributeError:
				raised = True

			assert raised == True
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_deleting_absent_dict_key_raises(cls):
		state = cls._patch_runtime()

		try:
			x      = o.Dict({})
			raised = False

			try:
				del x['missing']
			except KeyError:
				raised = True

			assert raised == True
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_attr_list_dict_atom_cascade_shape(cls):
		state = cls._patch_runtime()

		try:
			root        = o.T({})
			root.items  = [{'a': 'b'}]
			list_id     = root.__disk_instance__.attributes.get('items')
			dict_id     = o.get(list_id).__disk_instance__.list.get(0)
			dict_items  = o.get(dict_id).__disk_instance__.dict.items
			key_id      = next(iter(dict_items.keys()))
			value_id    = dict_items[key_id]

			del root.items

			cls._assert_released(list_id)
			cls._assert_released(dict_id)
			cls._assert_released(key_id)
			cls._assert_released(value_id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_attr_dict_list_atom_cascade_shape(cls):
		state = cls._patch_runtime()

		try:
			root        = o.T({})
			root.items  = {'a': [1]}
			dict_id     = root.__disk_instance__.attributes.get('items')
			dict_items  = o.get(dict_id).__disk_instance__.dict.items
			key_id      = next(iter(dict_items.keys()))
			list_id     = dict_items[key_id]
			item_id     = o.get(list_id).__disk_instance__.list.get(0)

			del root.items

			cls._assert_released(dict_id)
			cls._assert_released(key_id)
			cls._assert_released(list_id)
			cls._assert_released(item_id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_dict_list_cascade_shape(cls):
		state = cls._patch_runtime()

		try:
			x          = o.List([{'a': [1]}])
			dict_id    = x.__disk_instance__.list.get(0)
			dict_items = o.get(dict_id).__disk_instance__.dict.items
			key_id     = next(iter(dict_items.keys()))
			list_id    = dict_items[key_id]
			item_id    = o.get(list_id).__disk_instance__.list.get(0)

			del x[0]

			cls._assert_released(dict_id)
			cls._assert_released(key_id)
			cls._assert_released(list_id)
			cls._assert_released(item_id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_value_object_attrs_cascade_shape(cls):
		state = cls._patch_runtime()

		try:
			child      = o.T({})
			child.foo  = 'bar'
			foo_id     = child.__disk_instance__.attributes.get('foo')
			x          = o.Dict({'a': child})
			value_id   = x.__disk_instance__.dict.get('a')

			del x['a']

			cls._assert_released(value_id)
			cls._assert_released(foo_id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_key_non_atomic_entity_releases_correctly(cls):
		state = cls._patch_runtime()

		try:
			key       = o.T({})
			key.label = 'k'
			label_id  = key.__disk_instance__.attributes.get('label')
			root      = o.T({})
			root.items = {key: 'v'}
			dict_id   = root.__disk_instance__.attributes.get('items')
			dict_room = o.get(dict_id).__disk_instance__.dict.items
			key_id    = next(iter(dict_room.keys()))
			value_id  = dict_room[key_id]

			del root.items

			cls._assert_released(dict_id)
			cls._assert_released(key_id)
			cls._assert_released(label_id)
			cls._assert_released(value_id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_cascade_release_works_for_unloaded_children(cls):
		state = cls._patch_runtime()

		try:
			Probe        = o.T.extend('UnloadCascadeProbe', items=list)
			x            = Probe(items=[1, 2])
			list_id      = x.__disk_instance__.attributes.get('items')
			item_0       = o.get(list_id).__disk_instance__.list.get(0)
			item_1       = o.get(list_id).__disk_instance__.list.get(1)

			cls._drop_loaded(list_id)
			cls._drop_loaded(item_0)
			cls._drop_loaded(item_1)

			del x.items

			cls._assert_released(list_id)
			cls._assert_released(item_0)
			cls._assert_released(item_1)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_get_children_matches_for_loaded_and_unloaded_entity(cls):
		state = cls._patch_runtime()

		try:
			root       = o.T({})
			root.items = [1, 2]
			list_id    = root.__disk_instance__.attributes.get('items')
			loaded     = sorted(o.services.GC.get_children(list_id))

			cls._drop_loaded(list_id)
			cls._drop_loaded(loaded[0])
			cls._drop_loaded(loaded[1])

			unloaded = sorted(o.services.GC.get_children(list_id))

			assert loaded == unloaded
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_child_release_is_driven_by_edge_removal_not_wrapper_lifetime(cls):
		state = cls._patch_runtime()

		try:
			child = o.T('x')
			id    = child.id
			path  = o.id_to_path(id)

			del child
			gc.collect()

			assert os.path.exists(path) == True
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_temporary_disk_wrapper_does_not_change_registry_or_refcount(cls):
		state = cls._patch_runtime()

		try:
			x        = o.T({})
			x.foo    = 'bar'
			child_id = x.__disk_instance__.attributes.get('foo')
			path     = o.id_to_path(child_id)

			assert o.services.GC.get(child_id) == 1

			entity = o.disk.Entity.load(child_id)

			del entity
			gc.collect()

			assert o.id_to_path(child_id) == path
			assert o.services.GC.get(child_id) == 1
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_decrement_below_zero_for_real_room_raises(cls):
		state = cls._patch_runtime()

		try:
			child  = o.T('x')
			raised = False

			try:
				o.services.GC.dec(child.id)
			except ValueError:
				raised = True

			assert raised == True
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_raw_ids_without_room_path_are_ignored_safely(cls):
		state = cls._patch_runtime()

		try:
			o.services.GC.inc(999999999999999)
			o.services.GC.dec(999999999999999)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_cycle_survives_pure_refcount_collection(cls):
		state = cls._patch_runtime()

		try:
			root   = o.T({})
			left   = o.T({})
			right  = o.T({})

			root.left   = left
			root.right  = right
			left.peer   = right
			right.peer  = left

			left_id  = left.id
			right_id = right.id

			del root.left
			del root.right

			cls._assert_alive(left_id)
			cls._assert_alive(right_id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_self_reference_survives_without_crash(cls):
		state = cls._patch_runtime()

		try:
			root  = o.T({})
			child = o.T({})

			root.item = child
			child.me  = child

			child_id = child.id

			del root.item

			cls._assert_alive(child_id)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_mutual_cycle_across_two_containers_survives(cls):
		state = cls._patch_runtime()

		try:
			root   = o.T({})
			items  = o.List([])
			mapping = o.Dict({})

			root.items   = items
			root.mapping = mapping
			items.append(mapping)
			mapping['back'] = items

			items_id   = items.id
			mapping_id = mapping.id

			del root.items
			del root.mapping

			cls._assert_alive(items_id)
			cls._assert_alive(mapping_id)
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestGc.run()
