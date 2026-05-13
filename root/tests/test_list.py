import o


class TestList(o.Tester):
	RUNTIME_PREFIX = 'o_list_'

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_without_value_implies_empty_list(cls):
		state = cls._patch_runtime()

		try:
			x = o.List()

			assert isinstance(x, o.List)
			assert len(x) == 0
			assert list(x) == []
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_basic_surface(cls):
		state = cls._patch_runtime()

		try:
			x = o.List([1, 'a', None])
			items = o.services.Memory.get(f'{x.__proto__}.__items__')

			assert x.__zone__.prefix == f'{x.__proto__}.'
			assert x.__zone__.get('__items__') == items
			assert isinstance(items, bytes)
			assert len(items) == len(x) * 8
			assert len(x) == 3
			assert x[0] == 1
			assert x[1] == 'a'
			assert x[2] is None
			assert list(x) == [1, 'a', None]
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_setitem_append_and_delitem(cls):
		state = cls._patch_runtime()

		try:
			x        = o.List([1, 2])
			first_id = x.__items__[1]

			x[1] = 'b'
			x.append(3)
			del x[0]

			items = o.services.Memory.get(f'{x.__proto__}.__items__', b'')

			assert isinstance(items, bytes)
			assert len(items) == len(x) * 8
			assert x[0] == 'b'
			assert x[1] == 3
			assert len(x) == 2
			assert x.__items__[0] != first_id
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_non_atomic_child_surface(cls):
		state = cls._patch_runtime()

		try:
			Child = o.T.extend(name=str)
			x     = o.List([Child(name='alex')])

			assert isinstance(x[0], Child)
			assert x[0].name == 'alex'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_rejects_undeclared_object_attrs(cls):
		state = cls._patch_runtime()

		try:
			x = o.List([1, 2, 3])

			try:
				x.title = 'numbers'
				assert False
			except AttributeError as e:
				assert 'Field `title` is not defined' in str(e)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_get_reconstructs_list_instance_on_cache_miss(cls):
		state = cls._patch_runtime()

		try:
			ReconstructsListOnCacheMiss = o.T.extend('ReconstructsListOnCacheMiss', list)
			x                           = ReconstructsListOnCacheMiss([1, 2, 3])
			id    = x.id
			proto = x.__proto__

			del o.__entities__[id]

			reopened = o.get(id)

			assert isinstance(reopened, ReconstructsListOnCacheMiss)
			assert reopened.id == id
			assert reopened.__proto__ == proto
			assert list(reopened) == [1, 2, 3]
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_get_reconstructs_old_list_items_storage(cls):
		state = cls._patch_runtime()

		try:
			ReconstructsOldListItemsStorage = o.T.extend('ReconstructsOldListItemsStorage', list)
			x                               = ReconstructsOldListItemsStorage([1, 2, 3])
			id                              = x.id
			old_items                       = list(x.__items__)

			x.__zone__.set('__items__', old_items)

			del o.__entities__[id]

			reopened = o.get(id)

			assert isinstance(reopened, ReconstructsOldListItemsStorage)
			assert reopened.__items__ == old_items
			assert list(reopened) == [1, 2, 3]
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_get_resolves_list_n_proto_to_entity(cls):
		state = cls._patch_runtime()

		try:
			root_name                = state['root'].split('/')[-1]
			Child                    = o.T.extend(f'ListNProtoChild_{root_name}', name=str)
			ListNProtoResolvesEntity = o.T.extend(f'ListNProtoResolvesEntity_{root_name}', list)
			alex                     = Child(name='alex')
			bob                      = Child(name='bob')
			x                        = ListNProtoResolvesEntity([alex, bob])
			child                    = o.get(x.__items__[1])
			resolved                 = o.get(f'{x.__proto__}[1]')

			assert resolved is child
			assert isinstance(resolved, Child)
			assert resolved.name == 'bob'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dependants_yield_key_n_proto_and_child(cls):
		state = cls._patch_runtime()

		try:
			root_name = state['root'].split('/')[-1]
			Child     = o.T.extend(f'ListDependantsChild_{root_name}', name=str)
			ChildList = o.T.extend(f'ListDependants_{root_name}', list)
			alex      = Child(name='alex')
			bob       = Child(name='bob')
			x         = ChildList([alex, bob])
			items     = list(x.__dependants__())

			assert items[0][0] == 0
			assert items[0][1] == f'{x.__proto__}[0]'
			assert items[0][2] is alex
			assert items[1][0] == 1
			assert items[1][1] == f'{x.__proto__}[1]'
			assert items[1][2] is bob
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestList.run()
