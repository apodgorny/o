# ==============================================================================
# TEST WRITE INVALIDATION
# ==============================================================================
# Observe only the two IPL calls around committed LMDB writes.
# ==============================================================================

from types import SimpleNamespace

import o


class TestWriteTracking(o.Tester):
	RUNTIME_PREFIX = 'o_write_tracking_'

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Capture immutable ID snapshots from the two in-memory IPL calls.
	# ----------------------------------------------------------------------
	@classmethod
	def _observe(cls):
		events = []
		o.services.Memory.ipl = SimpleNamespace(
			pre_invalidate = lambda ids: events.append(('pre_invalidate', frozenset(ids))),
			invalidate     = lambda ids: events.append(('invalidate', frozenset(ids))),
		)

		return events

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# The schema and class zones have the same class owner.
	# ----------------------------------------------------------------------
	@classmethod
	def test_zone_owner_id_and_schema(cls):
		state = cls._patch_runtime()

		try:
			memory   = o.services.Memory
			class_id = o.services.Id.hash('o.T.WriteOwner')
			item_id  = o.services.Id.hash('o.T.WriteOwner._7')
			schema   = memory.zone('o.T.WriteOwner._.')
			fields   = memory.zone('o.T.WriteOwner.')
			instance = memory.zone('o.T.WriteOwner._7.')

			assert schema.owner_id == class_id
			assert fields.owner_id == class_id
			assert instance.owner_id == item_id
			assert memory.zone('garbage/items/').owner_id is None

			events = cls._observe()
			schema.set('field.type', 123)

			assert events == [
				('pre_invalidate', frozenset({class_id})),
				('invalidate', frozenset({class_id})),
			]
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Both calls occur after writes, around the actual commit.
	# ----------------------------------------------------------------------
	@classmethod
	def test_precedes_commit_and_confirms_afterward(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			key    = 'o.T.WriteBoundary._1.value'
			events = []

			def pre_invalidate(ids):
				with memory.env.begin() as tx:
					assert tx.get(memory._key(key)) is None

				events.append(('pre_invalidate', frozenset(ids)))

			def invalidate(ids):
				with memory.env.begin() as tx:
					assert memory.from_bytes(tx.get(memory._key(key))) == 17

				events.append(('invalidate', frozenset(ids)))

			memory.ipl = SimpleNamespace(pre_invalidate=pre_invalidate, invalidate=invalidate)
			memory.set(key, 17)

			owner_id = o.services.Id.hash('o.T.WriteBoundary._1')
			assert events == [
				('pre_invalidate', frozenset({owner_id})),
				('invalidate', frozenset({owner_id})),
			]
			assert list(memory.keys('changes/')) == []
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Ordinary field writes and deletion report their containing object.
	# ----------------------------------------------------------------------
	@classmethod
	def test_field_writes_and_deletion(cls):
		state = cls._patch_runtime()

		try:
			Model  = o.T.extend('WriteField', value=o.F(int, default=0))
			item   = Model(value=1)
			events = cls._observe()

			item.value = 2
			del item.value

			assert [name for name, _ in events] == [
				'pre_invalidate', 'invalidate', 'pre_invalidate', 'invalidate',
			]
			assert all(item.id in ids for _, ids in events)
			assert item.value == 0
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Collection writes report the collection identity.
	# ----------------------------------------------------------------------
	@classmethod
	def test_list_and_dict_writes(cls):
		state = cls._patch_runtime()

		try:
			items   = o.List([1, 2])
			mapping = o.Dict({'a': 1})
			events  = cls._observe()

			items[0] = 3
			items.append(4)
			del items[1]
			mapping['a'] = 2
			mapping['b'] = 3
			del mapping['b']

			written = set().union(*(ids for name, ids in events if name == 'invalidate'))

			assert items.id in written
			assert mapping.id in written
			assert list(items) == [3, 4]
			assert dict(mapping.items()) == {'a': 2}
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Creating and dropping instances invalidates the parent class.
	# ----------------------------------------------------------------------
	@classmethod
	def test_instance_birth_and_death(cls):
		state = cls._patch_runtime()

		try:
			Model  = o.T.extend('WriteLifecycle', value=int)
			events = cls._observe()
			item   = Model(value=5)
			born   = set().union(*(ids for name, ids in events if name == 'invalidate'))

			assert {item.id, Model.id} <= born

			events.clear()
			item.drop()
			dropped = set().union(*(ids for name, ids in events if name == 'invalidate'))

			assert {item.id, Model.id} <= dropped
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Creating and dropping subclasses invalidates the parent class.
	# ----------------------------------------------------------------------
	@classmethod
	def test_class_birth_and_death(cls):
		state = cls._patch_runtime()

		try:
			Base   = o.T.extend('WriteClassBase')
			events = cls._observe()
			Child  = Base.extend('WriteClassChild')
			born   = set().union(*(ids for name, ids in events if name == 'invalidate'))

			assert {Child.id, Base.id} <= born

			events.clear()
			Child.drop()
			dropped = set().union(*(ids for name, ids in events if name == 'invalidate'))

			assert {Child.id, Base.id} <= dropped
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Nested mutations emit exactly one pair of deduplicated notifications.
	# ----------------------------------------------------------------------
	@classmethod
	def test_nested_commit_and_deduplication(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			zone   = memory.zone('o.T.WriteNested._1.')
			events = cls._observe()

			with memory.write() as outer:
				zone.set('left', 1)

				with memory.write() as inner:
					assert inner is outer
					zone.set('right', 2)
					zone.set('left', 3)

				assert events == []

			assert events == [
				('pre_invalidate', frozenset({zone.owner_id})),
				('invalidate', frozenset({zone.owner_id})),
			]
			assert memory.get('o.T.WriteNested._1.left') == 3
			assert memory.get('o.T.WriteNested._1.right') == 2
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Rollback emits neither message, and a subsequent commit still works.
	# ----------------------------------------------------------------------
	@classmethod
	def test_rollback_does_not_notify(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			events = cls._observe()
			failed = False

			try:
				with memory.write():
					memory.set('o.T.WriteRollback._1.value', 7)
					raise ValueError('rollback')
			except ValueError:
				failed = True

			assert failed
			assert events == []
			assert memory.get('o.T.WriteRollback._1.value') is o.Undefined

			memory.set('o.T.WriteRollback._2.value', 8)
			assert len(events) == 2
			assert o.services.Id.hash('o.T.WriteRollback._2') in events[-1][1]
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Failure to send the warning prevents a commit; no confirmation follows.
	# ----------------------------------------------------------------------
	@classmethod
	def test_failed_pre_invalidate_prevents_commit(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			calls  = []

			def fail(ids):
				calls.append('pre_invalidate')
				raise RuntimeError('IPL disconnected')

			memory.ipl = SimpleNamespace(
				pre_invalidate = fail,
				invalidate     = lambda ids: calls.append('invalidate'),
			)

			failed = False

			try:
				memory.set('o.T.WriteFailure._1.value', 3)
			except RuntimeError:
				failed = True

			assert failed
			assert calls == ['pre_invalidate']
			assert memory.get('o.T.WriteFailure._1.value') is o.Undefined
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Unknown keys conservatively request a full invalidation via ID zero.
	# ----------------------------------------------------------------------
	@classmethod
	def test_unknown_and_administrative_keys(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			events = cls._observe()
			memory.set('custom/unknown', 1)

			assert events[-1] == ('invalidate', frozenset({0}))

			events.clear()
			memory.set('ids/12345', 'o.T.Unknown')
			memory.set('garbage/items/23456', 'o.T.Old')
			memory.set('routes/example', {'id': 34567})
			memory.set('tree/parents/45678', 56789)

			written = set().union(*(ids for name, ids in events if name == 'invalidate'))
			assert {12345, 23456, 34567, 45678, 56789, memory.root_id} <= written
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Clearing an instance zone reports only its known owner.
	# ----------------------------------------------------------------------
	@classmethod
	def test_instance_zone_clear(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			zone   = memory.zone('o.T.WriteClear._1.')
			zone.set('a', 1)
			zone.set('b', 2)
			events = cls._observe()

			zone.clear()

			assert events == [
				('pre_invalidate', frozenset({zone.owner_id})),
				('invalidate', frozenset({zone.owner_id})),
			]
			assert memory.get('o.T.WriteClear._1.a') is o.Undefined
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# A mixed-owner prefix includes every deleted object's identity.
	# ----------------------------------------------------------------------
	@classmethod
	def test_mixed_owner_prefix_deletion(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			memory.set('o.T.WriteMixed._1.left', 1)
			memory.set('o.T.WriteMixed._2.right', 2)
			events = cls._observe()

			memory.unset_all('o.T.WriteMixed.')

			assert o.services.Id.hash('o.T.WriteMixed._1') in events[-1][1]
			assert o.services.Id.hash('o.T.WriteMixed._2') in events[-1][1]
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Root-authorization changes include the referenced entity identity.
	# ----------------------------------------------------------------------
	@classmethod
	def test_root_zone_auth_target_deletion(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			zone   = memory.zone('o.T.V._99.')
			zone.set('__auth__/12345', {5: 'rw'})
			events = cls._observe()

			zone.clear()

			assert zone.owner_id in events[-1][1]
			assert 12345 in events[-1][1]
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Explicit IDs bypass key hashing for direct Memory operations.
	# ----------------------------------------------------------------------
	@classmethod
	def test_explicit_owner_for_direct_memory_writes(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			events = cls._observe()

			memory.set('custom/opaque', 'updated', owner_id=13579)

			assert events == [
				('pre_invalidate', frozenset({13579})),
				('invalidate', frozenset({13579})),
			]
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Missing deletes and empty write batches do not notify IPL.
	# ----------------------------------------------------------------------
	@classmethod
	def test_reads_and_missing_deletions(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			events = cls._observe()

			assert memory.get('o.T.Absent') is o.Undefined
			memory.unset('o.T.Absent')

			with memory.write():
				pass

			assert events == []
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Write tracking is optional until IPL is connected.
	# ----------------------------------------------------------------------
	@classmethod
	def test_writes_without_ipl(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			assert memory.ipl is None
			memory.set('o.T.WriteStandalone._1.value', 10)

			assert memory.get('o.T.WriteStandalone._1.value') == 10
			assert list(memory.keys('changes/')) == []
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestWriteTracking.run()
