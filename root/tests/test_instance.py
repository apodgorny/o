import os
import shutil
import tempfile

import o

UNDEFINED = o.Undefined


class TestInstance(o.Tester):

	# ----------------------------------------------------------------------
	@classmethod
	def _patch_registry(cls):
		services = o.services
		registry = type('RegistryState', (), {})()
		state    = {
			'services'      : services,
			'had_registry'  : 'Registry' in services.__dict__,
			'registry'      : services.__dict__.get('Registry'),
			'paths'         : {},
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
		root           = None
		registry_state = cls._patch_registry()

		os.makedirs(temp_root, exist_ok=True)
		root = tempfile.mkdtemp(prefix='o_instance_', dir=temp_root)

		state = {
			'root'          : root,
			'temp_root'     : temp_root,
			'registry'      : registry_state,
			'data_dir'      : o.DATA_DIR,
			'entities'      : dict(o.__entities__),
			'cast_map'      : dict(o.__cast_map__),
		}

		o.DATA_DIR = os.path.join('__tmp__', os.path.basename(root))

		return state

	# ----------------------------------------------------------------------
	@classmethod
	def _restore_runtime(cls, state):
		o.DATA_DIR = state['data_dir']

		o.__entities__.clear()
		o.__entities__.update(state['entities'])

		o.__cast_map__.clear()
		o.__cast_map__.update(state['cast_map'])

		cls._restore_registry(state['registry'])

		if os.path.isdir(state['root']):
			shutil.rmtree(state['root'])

		if os.path.isdir(state['temp_root']):
			shutil.rmtree(state['temp_root'])

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_atomic_embodiment(cls):
		state = cls._patch_runtime()

		try:
			assert isinstance(o.T(1), o.Int)
			assert isinstance(o.T(1.5), o.Float)
			assert isinstance(o.T(True), o.Bool)
			assert isinstance(o.T('x'), o.Str)
			assert isinstance(o.T(None), o.Null)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_existing_instance_passthrough(cls):
		state = cls._patch_runtime()

		try:
			x = o.Str('abc')
			y = o.T(x)

			assert y is x
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_atomic_disk_payloads(cls):
		state = cls._patch_runtime()

		try:
			i = o.T(1)
			f = o.T(1.5)
			b = o.T(True)
			s = o.T('x')
			n = o.T(None)

			assert o.services.Memory.get(f'{i.__proto__}.__value__') == 1
			assert o.services.Memory.get(f'{f.__proto__}.__value__') == 1.5
			assert o.services.Memory.get(f'{b.__proto__}.__value__') == True
			assert o.services.Memory.get(f'{s.__proto__}.__value__') == 'x'
			assert o.services.Memory.get(f'{n.__proto__}.__value__') is None
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_get_resolves_loaded_class_and_instance(cls):
		state = cls._patch_runtime()

		try:
			root_name                        = os.path.basename(state['root'])
			GetResolvesLoadedClassAndInstance = o.T.extend(f'GetResolvesLoadedClassAndInstance_{root_name}', foo=str)

			t1 = GetResolvesLoadedClassAndInstance(foo='hello')

			assert o.get(GetResolvesLoadedClassAndInstance.id) is GetResolvesLoadedClassAndInstance
			assert o.get(t1.id) is t1
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_get_resolves_loaded_proto_class_and_instance(cls):
		state = cls._patch_runtime()

		try:
			root_name                             = os.path.basename(state['root'])
			GetResolvesLoadedProtoClassAndInstance = o.T.extend(f'GetResolvesLoadedProtoClassAndInstance_{root_name}', foo=str)
			t1                                     = GetResolvesLoadedProtoClassAndInstance(foo='hello')

			assert o.get(GetResolvesLoadedProtoClassAndInstance.__proto__) is GetResolvesLoadedProtoClassAndInstance
			assert o.get(t1.__proto__) is t1
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_object_init(cls):
		state = cls._patch_runtime()

		try:
			root_name  = os.path.basename(state['root'])
			ObjectInit = o.T.extend(
				f'ObjectInit_{root_name}',
				foo=str,
				bar=o.F(int, default=7)
			)

			t1 = ObjectInit(foo='hello')

			assert isinstance(t1.foo, str)
			assert t1.foo == 'hello'
			assert t1.bar == 7

			assert o.services.Memory.get(f'{t1.__proto__}.foo', UNDEFINED) is not UNDEFINED
			assert o.services.Memory.get(f'{t1.__proto__}.bar', UNDEFINED) is UNDEFINED

			assert isinstance(o.services.Memory.get(f'{t1.__proto__}.foo'), int)
			assert o.services.Memory.get(f'{t1.__proto__}.bar', UNDEFINED) is UNDEFINED

			t2 = ObjectInit(foo='world', bar=9)

			assert isinstance(t2.foo, str)
			assert t2.foo == 'world'
			assert isinstance(t2.bar, int)
			assert t2.bar == 9
			assert o.services.Memory.get(f'{t2.__proto__}.foo', UNDEFINED) is not UNDEFINED
			assert o.services.Memory.get(f'{t2.__proto__}.bar', UNDEFINED) is not UNDEFINED
			assert isinstance(o.services.Memory.get(f'{t2.__proto__}.foo'), int)
			assert isinstance(o.services.Memory.get(f'{t2.__proto__}.bar'), int)

			try:
				ObjectInit()
				assert False
			except TypeError:
				pass

			t3 = ObjectInit(foo='x', baz=1)

			assert isinstance(t3.foo, str)
			assert t3.foo == 'x'
			assert isinstance(t3.baz, int)
			assert t3.baz == 1
			assert o.services.Memory.get(f'{t3.__proto__}.baz', UNDEFINED) is not UNDEFINED
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_object_default_is_inherited_until_override(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			ObjectDefaultIsInheritedUntilOverride = o.T.extend(
				f'ObjectDefaultIsInheritedUntilOverride_{root_name}',
				foo=str,
				bar=o.F(int, default=7)
			)

			t1 = ObjectDefaultIsInheritedUntilOverride(foo='hello')

			assert t1.bar == 7
			assert 'bar' not in t1.__dict__
			assert o.services.Memory.get(f'{t1.__proto__}.bar', UNDEFINED) is UNDEFINED

			t2 = ObjectDefaultIsInheritedUntilOverride(foo='world', bar=9)
			bar_id = o.services.Memory.get(f'{t2.__proto__}.bar')

			assert isinstance(t2.bar, int)
			assert t2.bar == 9
			assert 'bar' in t2.__dict__
			assert o.services.Memory.get(f'{t2.__proto__}.bar', UNDEFINED) is not UNDEFINED
			assert isinstance(bar_id, int)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_getattr_reads_persisted_child_via_entities_registry(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			GetattrReadsPersistedChildViaEntitiesRegistry = o.T.extend(
				f'GetattrReadsPersistedChildViaEntitiesRegistry_{root_name}',
				foo=str,
			)

			t1     = GetattrReadsPersistedChildViaEntitiesRegistry(foo='hello')
			foo_id = o.services.Memory.get(f'{t1.__proto__}.foo')

			del t1.__dict__['foo']
			assert o.services.Memory.get(f'{t1.__proto__}.foo', UNDEFINED) is not UNDEFINED
			assert isinstance(foo_id, int)
			assert o.get(foo_id).__value__ == 'hello'
			assert t1.foo == 'hello'
			assert isinstance(t1.foo, str)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_delattr_removes_materialized_attr_from_disk_and_memory(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			DelattrRemovesMaterializedAttr = o.T.extend(
				f'DelattrRemovesMaterializedAttr_{root_name}',
				foo=str,
			)

			t1 = DelattrRemovesMaterializedAttr(foo='hello')

			assert t1.foo == 'hello'
			assert 'foo' in t1.__dict__
			assert o.services.Memory.get(f'{t1.__proto__}.foo', UNDEFINED) is not UNDEFINED

			del t1.foo

			assert 'foo' not in t1.__dict__
			assert o.services.Memory.get(f'{t1.__proto__}.foo', UNDEFINED) is UNDEFINED

			try:
				t1.foo
				assert False
			except AttributeError:
				pass
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_delattr_removes_attr_after_cache_slot_drop(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			DelattrRemovesAttrAfterCacheSlotDrop = o.T.extend(
				f'DelattrRemovesAttrAfterCacheSlotDrop_{root_name}',
				foo=str,
			)

			t1 = DelattrRemovesAttrAfterCacheSlotDrop(foo='hello')

			del t1.__dict__['foo']

			assert 'foo' not in t1.__dict__
			assert o.services.Memory.get(f'{t1.__proto__}.foo', UNDEFINED) is not UNDEFINED

			del t1.foo

			assert 'foo' not in t1.__dict__
			assert o.services.Memory.get(f'{t1.__proto__}.foo', UNDEFINED) is UNDEFINED

			try:
				t1.foo
				assert False
			except AttributeError:
				pass
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_non_atomic_child_returns_wrapper_via_entities_registry(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Child     = o.T.extend(f'Child_{root_name}', name=str)
			Parent    = o.T.extend(f'Parent_{root_name}', child=Child)

			child  = Child(name='alex')
			parent = Parent(child=child)

			assert 'child' in parent.__dict__
			assert o.services.Memory.get(f'{parent.__proto__}.child', UNDEFINED) is not UNDEFINED
			assert o.services.Memory.get(f'{parent.__proto__}.child') == child.id
			assert parent.child is child
			assert parent.child.name == 'alex'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_plain_object_birth(cls):
		state = cls._patch_runtime()

		try:
			t1 = o.T()

			assert isinstance(t1, o.T)
			assert t1.__class__ is o.T
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_plain_object_with_attrs(cls):
		state = cls._patch_runtime()

		try:
			t1 = o.T(name='alex')

			assert t1.name == 'alex'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_value_with_attrs(cls):
		state = cls._patch_runtime()

		try:
			t1 = o.T('alex', lang='en')

			assert isinstance(t1, o.Str)
			assert t1.__value__ == 'alex'
			assert t1.lang == 'en'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_list_with_attrs(cls):
		state = cls._patch_runtime()

		try:
			t1 = o.T([1, 2, 3], title='numbers')

			assert isinstance(t1, o.List)
			assert list(t1) == [1, 2, 3]
			assert t1.title == 'numbers'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_dict_with_attrs(cls):
		state = cls._patch_runtime()

		try:
			t1 = o.T({'a': 1, 'b': 2}, title='scores')

			assert isinstance(t1, o.Dict)
			assert dict(t1.items()) == {'a': 1, 'b': 2}
			assert t1.title == 'scores'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_attr_name_starting_with_underscore_raises(cls):
		state = cls._patch_runtime()

		try:
			t1 = o.T()

			try:
				t1._name = 'alex'
				assert False
			except AttributeError as e:
				assert 'can not start with "_"' in str(e)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_setattr_accepts_embodied_child(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Child     = o.T.extend(f'Child_{root_name}', name=str)
			Parent    = o.T.extend(f'Parent_{root_name}', child=Child)

			child  = Child(name='alex')
			parent = Parent(child=child)

			assert parent.child is child
			assert o.services.Memory.get(f'{parent.__proto__}.child') == child.id
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_field_overwrite_updates_persisted_child_id(cls):
		state = cls._patch_runtime()

		try:
			root_name                            = os.path.basename(state['root'])
			FieldOverwriteUpdatesPersistedChildId = o.T.extend(f'FieldOverwriteUpdatesPersistedChildId_{root_name}', foo=str)

			t1       = FieldOverwriteUpdatesPersistedChildId(foo='hello')
			first_id = o.services.Memory.get(f'{t1.__proto__}.foo')

			t1.foo = 'world'

			assert isinstance(t1.foo, str)
			assert t1.foo == 'world'
			assert o.services.Memory.get(f'{t1.__proto__}.foo') != first_id
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_non_atomic_child_returns_wrapper_via_entities_registry(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Child     = o.T.extend(f'Child_{root_name}', name=str)
			Parent    = o.T.extend(f'Parent_{root_name}', child=Child)

			child  = Child(name='alex')
			parent = Parent(child=child)

			assert 'child' in parent.__dict__
			assert o.services.Memory.get(f'{parent.__proto__}.child', UNDEFINED) is not UNDEFINED
			assert o.services.Memory.get(f'{parent.__proto__}.child') == child.id
			assert parent.child is child
			assert isinstance(parent.child, Child)
			assert parent.child.name == 'alex'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_child_instance_inherits_base_default(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Base      = o.T.extend(f'Base_{root_name}', foo=o.F(int, default=7))
			Child     = Base.extend(f'Child_{root_name}')

			obj = Child()

			assert obj.foo == 7
			assert 'foo' not in obj.__dict__
			assert o.services.Memory.get(f'{obj.__proto__}.foo', UNDEFINED) is UNDEFINED
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_instance_override_deletes_back_to_inherited_default(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			InstanceOverrideDeletesBackToInheritedDefault = o.T.extend(
				f'InstanceOverrideDeletesBackToInheritedDefault_{root_name}',
				foo=o.F(int, default=7)
			)

			obj = InstanceOverrideDeletesBackToInheritedDefault()

			assert obj.foo == 7
			assert 'foo' not in obj.__dict__
			assert o.services.Memory.get(f'{obj.__proto__}.foo', UNDEFINED) is UNDEFINED

			obj.foo = 9

			assert obj.foo == 9
			assert 'foo' in obj.__dict__
			assert o.services.Memory.get(f'{obj.__proto__}.foo', UNDEFINED) is not UNDEFINED

			del obj.foo

			assert obj.foo == 7
			assert 'foo' not in obj.__dict__
			assert o.services.Memory.get(f'{obj.__proto__}.foo', UNDEFINED) is UNDEFINED
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_exists_aligns_with_instance_room(cls):
		state = cls._patch_runtime()

		try:
			root_name                   = os.path.basename(state['root'])
			ExistsAlignsWithInstanceRoom = o.T.extend(f'ExistsAlignsWithInstanceRoom_{root_name}', foo=str)

			t1 = ExistsAlignsWithInstanceRoom(foo='hello')

			assert o.exists(t1.id) == True
			assert o.exists(t1.__proto__) == True
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_get_of_absent_id_returns_undefined(cls):
		state = cls._patch_runtime()

		try:
			assert o.get(999999) is UNDEFINED
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_get_reconstructs_object_instance_on_cache_miss(cls):
		state = cls._patch_runtime()

		try:
			root_name                               = os.path.basename(state['root'])
			GetReconstructsObjectInstanceOnCacheMiss = o.T.extend(f'GetReconstructsObjectInstanceOnCacheMiss_{root_name}', foo=str)

			t1       = GetReconstructsObjectInstanceOnCacheMiss(foo='hello')
			id       = t1.id
			proto    = t1.__proto__
			count    = o.services.Memory.get(f'{GetReconstructsObjectInstanceOnCacheMiss.__proto__}.__version__')

			del o.__entities__[id]

			reopened = o.get(id)

			assert reopened.id == id
			assert reopened.__proto__ == proto
			assert reopened.foo == 'hello'
			assert o.services.Memory.get(f'{GetReconstructsObjectInstanceOnCacheMiss.__proto__}.__version__') == count
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestInstance.run()
