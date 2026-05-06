import os

import o

UNDEFINED = o.Undefined


class TestInstance(o.Tester):
	RUNTIME_PREFIX = 'o_instance_'

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
	def test_root_rejects_unknown_python_object(cls):
		state = cls._patch_runtime()

		try:
			class UnknownObject:
				pass

			try:
				o.T(UnknownObject())
				assert False
			except TypeError as e:
				assert 'Cannot cast' in str(e)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_rejects_unknown_python_class(cls):
		state = cls._patch_runtime()

		try:
			class UnknownClass:
				pass

			try:
				o.T(UnknownClass)
				assert False
			except TypeError as e:
				assert 'Cannot cast' in str(e)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_rejects_nested_unknown_object_in_list(cls):
		state = cls._patch_runtime()

		try:
			class UnknownObject:
				pass

			try:
				o.T([1, UnknownObject()])
				assert False
			except TypeError as e:
				assert 'Cannot cast' in str(e)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_rejects_nested_unknown_object_in_dict(cls):
		state = cls._patch_runtime()

		try:
			class UnknownObject:
				pass

			try:
				o.T({'a': UnknownObject()})
				assert False
			except TypeError as e:
				assert 'Cannot cast' in str(e)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_rejects_builtin_subclass_without_annotation(cls):
		state = cls._patch_runtime()

		try:
			class CustomList(list):
				pass

			try:
				o.T(CustomList([1, 2]))
				assert False
			except TypeError as e:
				assert 'Cannot cast' in str(e)
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

			try:
				ObjectInit(foo='x', baz=1)
				assert False
			except AttributeError as e:
				assert 'Field `baz` is not defined' in str(e)
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
	def test_root_plain_object_rejects_undeclared_attrs(cls):
		state = cls._patch_runtime()

		try:
			try:
				o.T(name='alex')
				assert False
			except AttributeError as e:
				assert 'Field `name` is not defined' in str(e)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_value_rejects_undeclared_attrs(cls):
		state = cls._patch_runtime()

		try:
			try:
				o.T('alex', lang='en')
				assert False
			except AttributeError as e:
				assert 'Field `lang` is not defined' in str(e)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_list_rejects_undeclared_attrs(cls):
		state = cls._patch_runtime()

		try:
			try:
				o.T([1, 2, 3], title='numbers')
				assert False
			except AttributeError as e:
				assert 'Field `title` is not defined' in str(e)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_dict_rejects_undeclared_attrs(cls):
		state = cls._patch_runtime()

		try:
			try:
				o.T({'a': 1, 'b': 2}, title='scores')
				assert False
			except AttributeError as e:
				assert 'Field `title` is not defined' in str(e)
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
	def test_class_on_change_receives_attr_transitions(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			events    = []
			OnChange  = o.T.extend(f'OnChange_{root_name}', foo=str)

			def on_change(instance):
				events.append(instance)

			OnChange.__on_change__ = on_change

			x = OnChange(foo='a')
			events.clear()

			x.foo = 'b'

			del x.foo

			assert len(events) == 2
			assert events[0] is x
			assert events[1] is x
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
	def test_dependants_yield_field_key_n_proto_and_child(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Child     = o.T.extend(f'DependantsFieldChild_{root_name}', name=str)
			Parent    = o.T.extend(f'DependantsFieldParent_{root_name}', child=Child)
			child     = Child(name='alex')
			parent    = Parent(child=child)
			items     = list(parent.__dependants__())

			assert items == [('child', f'{parent.__proto__}.child', child)]
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
			assert reopened.__zone__.prefix == f'{proto}.'
			assert reopened.foo == 'hello'
			assert reopened.__zone__.get('foo') == o.services.Memory.get(f'{proto}.foo')
			assert o.services.Memory.get(f'{GetReconstructsObjectInstanceOnCacheMiss.__proto__}.__version__') == count
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestInstance.run()
