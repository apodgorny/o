import gc

import o


class TestGc(o.Test):

	@classmethod
	def _ensure_int_storage(cls):
		o.services.One.define(
			o.Int.__o_module__,
			o.Int.__type_id__,
			'q'
		)

	@classmethod
	def _read_int(cls, instance_id):
		return o.services.One.read(o.Int.__type_id__, instance_id)

	@classmethod
	def _assert_inactive_int(cls, instance_id):
		try:
			cls._read_int(instance_id)
			assert False
		except ValueError:
			pass

	@classmethod
	def test_wrapper_gc_deletes_record(cls):
		cls._ensure_int_storage()

		obj = o.Int(5)
		instance_id = obj.__id__

		assert cls._read_int(instance_id) == 5

		del obj
		gc.collect()

		cls._assert_inactive_int(instance_id)

	@classmethod
	def test_multiple_wrappers_delete_idempotent(cls):
		cls._ensure_int_storage()

		a = o.Int(1)
		instance_id = a.__id__
		type_id = o.Int.__type_id__
		before_count = o.services.One.free[type_id].count(instance_id)

		b = o.Int.instantiate(instance_id)

		del a
		gc.collect()

		del b
		gc.collect()

		after_count = o.services.One.free[type_id].count(instance_id)
		assert after_count == before_count + 1
		cls._assert_inactive_int(instance_id)

	@classmethod
	def test_container_keeps_record_alive(cls):
		cls._ensure_int_storage()

		x = o.Int(42)
		instance_id = x.__id__

		l = o.List([])
		l.append(x)

		del x
		gc.collect()

		assert cls._read_int(instance_id) == 42
		assert l[0] == 42

	@classmethod
	def test_container_remove_triggers_delete(cls):
		cls._ensure_int_storage()

		l = o.List([1, 2, 3])
		type_id, instance_id = l.__items__[1]

		assert o.services.One.read(type_id, instance_id) == 2

		del l[1]
		gc.collect()

		try:
			o.services.One.read(type_id, instance_id)
			assert False
		except ValueError:
			pass

	@classmethod
	def test_bind_snapshot_survives_gc(cls):
		l1 = o.List([1, 2, 3])
		container_id = l1.__id__

		l2 = o.List.instantiate(container_id)

		del l1
		gc.collect()

		try:
			l2.__cast_out__()
			assert False
		except ValueError:
			pass

	@classmethod
	def test_free_heap_has_no_duplicates(cls):
		cls._ensure_int_storage()

		count = 100
		type_id = o.Int.__type_id__

		objs = [o.Int(i) for i in range(count)]
		ids = [obj.__id__ for obj in objs]

		assert len(ids) == len(set(ids))

		heap_mid = list(o.services.One.free[type_id])

		del objs
		gc.collect()

		heap_after = list(o.services.One.free[type_id])

		assert len(heap_after) == len(set(heap_after))
		assert len(heap_after) == len(heap_mid) + count

		for instance_id in ids:
			assert heap_after.count(instance_id) == heap_mid.count(instance_id) + 1

	@classmethod
	def test_slot_reuse_after_delete(cls):
		cls._ensure_int_storage()

		a = o.Int(1)
		id1 = a.__id__

		del a
		gc.collect()

		b = o.Int(2)
		id2 = b.__id__

		assert id2 == id1
		assert int(b) == 2
		assert cls._read_int(id2) == 2
