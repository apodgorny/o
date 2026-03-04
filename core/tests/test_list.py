import o


class TestList(o.Test):

	@classmethod
	def test_basic_roundtrip(cls):
		l = o.List([1, 2, 3])
		assert l.__cast_out__() == [1, 2, 3]

	@classmethod
	def test_init_requires_list(cls):
		try:
			o.List((1, 2, 3))
			assert False
		except TypeError:
			pass

	@classmethod
	def test_empty_list(cls):
		l = o.List([])
		assert len(l) == 0
		assert l.__cast_out__() == []

	@classmethod
	def test_contains_len_iter(cls):
		l = o.List([1, 2, 3])
		assert (2 in l) == True
		assert (9 in l) == False
		assert len(l) == 3
		assert list(iter(l)) == [1, 2, 3]

	@classmethod
	def test_bool_conversion(cls):
		assert bool(o.List([])) == False
		assert bool(o.List([1])) == True

	@classmethod
	def test_getitem_positive(cls):
		l = o.List([10, 20, 30])
		assert l[1] == 20

	@classmethod
	def test_getitem_negative(cls):
		l = o.List([10, 20, 30])
		assert l[-1] == 30

	@classmethod
	def test_getitem_out_of_range(cls):
		l = o.List([1, 2, 3])
		try:
			_ = l[99]
			assert False
		except IndexError:
			pass

	@classmethod
	def test_getitem_non_int_typeerror(cls):
		l = o.List([1, 2, 3])
		try:
			_ = l['1']
			assert False
		except TypeError:
			pass

	@classmethod
	def test_setitem_basic(cls):
		l = o.List([1, 2, 3])
		l[1] = 99
		assert l.__cast_out__() == [1, 99, 3]

	@classmethod
	def test_setitem_negative(cls):
		l = o.List([1, 2, 3])
		l[-1] = 7
		assert l.__cast_out__() == [1, 2, 7]

	@classmethod
	def test_setitem_out_of_range(cls):
		l = o.List([1, 2, 3])
		try:
			l[5] = 1
			assert False
		except IndexError:
			pass

	@classmethod
	def test_setitem_non_int_typeerror(cls):
		l = o.List([1, 2, 3])
		try:
			l['1'] = 1
			assert False
		except TypeError:
			pass

	@classmethod
	def test_delitem_basic(cls):
		l = o.List([1, 2, 3])
		del l[1]
		assert l.__cast_out__() == [1, 3]

	@classmethod
	def test_delitem_negative(cls):
		l = o.List([1, 2, 3])
		del l[-1]
		assert l.__cast_out__() == [1, 2]

	@classmethod
	def test_delitem_out_of_range(cls):
		l = o.List([1, 2, 3])
		try:
			del l[10]
			assert False
		except IndexError:
			pass

	@classmethod
	def test_delitem_non_int_typeerror(cls):
		l = o.List([1, 2, 3])
		try:
			del l['1']
			assert False
		except TypeError:
			pass

	@classmethod
	def test_append_atomic_values(cls):
		l = o.List([])
		l.append(1)
		l.append('x')
		l.append(True)
		l.append(1.5)
		print(l.__cast_out__())
		print([type(x) for x in l.__cast_out__()])
		assert l.__cast_out__() == [1, 'x', True, 1.5]

	@classmethod
	def test_append_object_value(cls):
		l = o.List([])
		x = o.Int(7)
		l.append(x)
		assert l[0] == 7

	@classmethod
	def test_value_reference_is_live_object(cls):
		l = o.List([])
		x = o.Int(7)
		l.append(x)
		x.__write__(11)
		assert l[0] == 11

	@classmethod
	def test_append_unsupported_type_raises(cls):
		l = o.List([])
		try:
			l.append(object())
			assert False
		except TypeError:
			pass

	@classmethod
	def test_python_composite_items_are_supported(cls):

		for data in ([[1, 2]], [{'a': 1}]):

			l = o.List(data)

			assert len(l) == 1

			item = l[0]

			# Returned back as Python composite
			print('test_python_composite_items_are_supported', item, data[0])
			assert item == data[0]

			if isinstance(data[0], list):
				assert isinstance(item, list)

			elif isinstance(data[0], dict):
				assert isinstance(item, dict)

	@classmethod
	def test_wrapped_composite_items_roundtrip(cls):
		l = o.List([
			o.List([1, 2]),
			o.Dict({'a': 1}),
		])

		l0 = l[0]
		l1 = l[1]

		# Composite возвращаются как Python-структуры
		assert isinstance(l0, list)
		assert isinstance(l1, dict)

		assert l0 == [1, 2]
		assert l1 == {'a': 1}

	@classmethod
	def test_pop_default(cls):
		l = o.List([1, 2, 3])
		x = l.pop()
		assert x == 3
		assert l.__cast_out__() == [1, 2]

	@classmethod
	def test_pop_by_index(cls):
		l = o.List([1, 2, 3])
		x = l.pop(1)
		assert x == 2
		assert l.__cast_out__() == [1, 3]

	@classmethod
	def test_pop_negative_index(cls):
		l = o.List([1, 2, 3])
		x = l.pop(-2)
		assert x == 2
		assert l.__cast_out__() == [1, 3]

	@classmethod
	def test_pop_empty_indexerror(cls):
		l = o.List([])
		try:
			l.pop()
			assert False
		except IndexError:
			pass

	@classmethod
	def test_pop_out_of_range_indexerror(cls):
		l = o.List([1, 2, 3])
		try:
			l.pop(10)
			assert False
		except IndexError:
			pass

	@classmethod
	def test_overwrite_len_stability(cls):
		l = o.List([1, 2, 3])
		l[1] = 9
		assert len(l) == 3

	@classmethod
	def test_eq_ne_behavior(cls):
		l = o.List([1, 2, 3])
		assert (l == [1, 2, 3]) == True
		assert (l != [1, 2, 3]) == False
		assert (l == [1, 2]) == False

	@classmethod
	def test_add_returns_python_list_non_mutating(cls):
		l = o.List([1, 2])
		out = l + [3, 4]
		assert isinstance(out, list)
		assert out == [1, 2, 3, 4]
		assert l.__cast_out__() == [1, 2]

	@classmethod
	def test_mul_returns_python_list_non_mutating(cls):
		l = o.List([1, 2])
		out = l * 3
		assert isinstance(out, list)
		assert out == [1, 2, 1, 2, 1, 2]
		assert l.__cast_out__() == [1, 2]

	@classmethod
	def test_bind_snapshot_requires_reload(cls):
		l1 = o.List([1])
		l2 = o.List.bind(l1.__id__)

		l1.append(2)
		l2.__read__()
		assert l2.__cast_out__() == [1, 2]

		l2.append(3)
		l1.__read__()
		assert l1.__cast_out__() == [1, 2, 3]

	@classmethod
	def test_persistence_reopen_by_id(cls):
		l1 = o.List([1, 2, 3])
		l2 = o.List.bind(l1.__id__)
		assert l2.__cast_out__() == [1, 2, 3]

	@classmethod
	def test_commit_persistence(cls):
		l1 = o.List([1, 2, 3])
		o.services.Many.commit()
		l2 = o.List.bind(l1.__id__)
		assert l2.__cast_out__() == [1, 2, 3]

	@classmethod
	def test_isolation_between_lists(cls):
		l1 = o.List([1])
		l2 = o.List([2])
		l1.append(3)
		assert l1.__cast_out__() == [1, 3]
		assert l2.__cast_out__() == [2]

	@classmethod
	def test_delete_list_removes_storage(cls):
		l = o.List([1, 2])
		id_ = l.__id__
		l.__delete__()

		try:
			o.List.bind(id_)
			assert False
		except KeyError:
			pass

	@classmethod
	def test_magic_clear_empties_list(cls):
		l = o.List([1, 2, 3])
		l.__clear__()
		assert l.__cast_out__() == []
		assert len(l) == 0

	@classmethod
	def test_extend_insert_remove_via_getattr(cls):
		l = o.List([1, 3])

		l.extend([4, 5])
		assert l.__cast_out__() == [1, 3, 4, 5]

		l.insert(1, 2)
		assert l.__cast_out__() == [1, 2, 3, 4, 5]

		l.remove(3)
		assert l.__cast_out__() == [1, 2, 4, 5]

	@classmethod
	def test_clear_via_getattr_method(cls):
		l = o.List([1, 2, 3])
		l.clear()
		assert l.__cast_out__() == []

	@classmethod
	def test_sort_reverse_via_getattr(cls):
		l = o.List([3, 1, 2])
		l.sort()
		assert l.__cast_out__() == [1, 2, 3]

		l.reverse()
		assert l.__cast_out__() == [3, 2, 1]

	@classmethod
	def test_count_index_copy_via_getattr(cls):
		l = o.List([1, 2, 2, 3])
		assert l.count(2) == 2
		assert l.index(3) == 3

		c = l.copy()
		assert isinstance(c, list)
		assert c == [1, 2, 2, 3]
		assert l.__cast_out__() == [1, 2, 2, 3]
