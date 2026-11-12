# ==============================================================================
# TEST WRITE INVALIDATION
# ==============================================================================
# Send every owner immediately; confirm once after successful LMDB commit.
# ==============================================================================

from types import SimpleNamespace

import o


class TestWriteTracking(o.Tester):
	RUNTIME_PREFIX = 'o_write_tracking_'

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Capture the exact order of IPL calls.
	# ----------------------------------------------------------------------
	@classmethod
	def _observe(cls):
		events = []
		o.services.Memory.ipl = SimpleNamespace(
			pre_invalidate = lambda owner_id: events.append(('pre_invalidate', owner_id)),
			invalidate     = lambda: events.append(('invalidate', None)),
		)

		return events

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Schema, fields and instance zones retain their correct owner IDs.
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
			assert memory.zone('garbage/items/').owner_id == 0

			events = cls._observe()
			schema.set('field.type', 123)

			assert events == [
				('pre_invalidate', class_id),
				('invalidate', None),
			]
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# pre_invalidate happens during the transaction; invalidate after commit.
	# ----------------------------------------------------------------------
	@classmethod
	def test_precedes_commit_and_confirms_afterward(cls):
		state = cls._patch_runtime()

		try:
			memory   = o.services.Memory
			key      = 'o.T.WriteBoundary._1.value'
			owner_id = o.services.Id.hash('o.T.WriteBoundary._1')
			events   = []

			def pre_invalidate(entity_id):
				with memory.env.begin() as tx:
					assert tx.get(memory._key(key)) is None

				events.append(('pre_invalidate', entity_id))

			def invalidate():
				assert memory._write is None

				with memory.env.begin() as tx:
					assert memory.from_bytes(tx.get(memory._key(key))) == 17

				events.append(('invalidate', None))

			memory.ipl = SimpleNamespace(pre_invalidate=pre_invalidate, invalidate=invalidate)
			memory.set(key, 17, owner_id)

			assert events == [
				('pre_invalidate', owner_id),
				('invalidate', None),
			]
			assert list(memory.keys('changes/')) == []
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Each mutation sends one immediate ID and one commit confirmation.
	# ----------------------------------------------------------------------
	@classmethod
	def test_field_writes_and_deletion(cls):
		state = cls._patch_runtime()

		try:
			Model  = o.T.extend('WriteField', value=o.F(int, default=0))
			item   = Model(value=1)
			events = cls._observe()

			item.value = 2
			assert ('pre_invalidate', item.id) in events
			assert events[-1] == ('invalidate', None)

			events.clear()
			del item.value
			assert ('pre_invalidate', item.id) in events
			assert events[-1] == ('invalidate', None)
			assert item.value == 0
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Collection changes report their collection identity.
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

			written = {owner for name, owner in events if name == 'pre_invalidate'}

			assert items.id in written
			assert mapping.id in written
			assert list(items) == [3, 4]
			assert dict(mapping.items()) == {'a': 2}
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Instance creation and deletion also report parent-class membership.
	# ----------------------------------------------------------------------
	@classmethod
	def test_instance_birth_and_death(cls):
		state = cls._patch_runtime()

		try:
			Model  = o.T.extend('WriteLifecycle', value=int)
			events = cls._observe()
			item   = Model(value=5)
			born   = {owner for name, owner in events if name == 'pre_invalidate'}

			assert {item.id, Model.id} <= born

			events.clear()
			item.drop()
			dropped = {owner for name, owner in events if name == 'pre_invalidate'}

			assert {item.id, Model.id} <= dropped
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Class creation and deletion also report the parent-class ID.
	# ----------------------------------------------------------------------
	@classmethod
	def test_class_birth_and_death(cls):
		state = cls._patch_runtime()

		try:
			Base   = o.T.extend('WriteClassBase')
			events = cls._observe()
			Child  = Base.extend('WriteClassChild')
			born   = {owner for name, owner in events if name == 'pre_invalidate'}

			assert {Child.id, Base.id} <= born

			events.clear()
			Child.drop()
			dropped = {owner for name, owner in events if name == 'pre_invalidate'}

			assert {Child.id, Base.id} <= dropped
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Nested writes send immediately, including duplicates, but commit once.
	# ----------------------------------------------------------------------
	@classmethod
	def test_nested_commit_and_no_deduplication(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			zone   = memory.zone('o.T.WriteNested._1.')
			events = cls._observe()

			with memory.write() as outer:
				zone.set('left', 1)

				assert events == [('pre_invalidate', zone.owner_id)]

				with memory.write() as inner:
					assert inner is outer
					zone.set('right', 2)
					zone.set('left', 3)

				assert events == [('pre_invalidate', zone.owner_id)] * 3

			assert events == [
				('pre_invalidate', zone.owner_id),
				('pre_invalidate', zone.owner_id),
				('pre_invalidate', zone.owner_id),
				('invalidate', None),
			]
			assert memory.get('o.T.WriteNested._1.left') == 3
			assert memory.get('o.T.WriteNested._1.right') == 2
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Rollback leaves pre-invalidation for IPL timeout but no confirmation.
	# ----------------------------------------------------------------------
	@classmethod
	def test_rollback_does_not_confirm(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			events = cls._observe()
			failed = False

			try:
				with memory.write():
					memory.set('o.T.WriteRollback._1.value', 7, o.services.Id.hash('o.T.WriteRollback._1'))
					raise ValueError('rollback')
			except ValueError:
				failed = True

			assert failed
			assert events == [('pre_invalidate', o.services.Id.hash('o.T.WriteRollback._1'))]
			assert memory.get('o.T.WriteRollback._1.value') is o.Undefined

			memory.set('o.T.WriteRollback._2.value', 8, o.services.Id.hash('o.T.WriteRollback._2'))
			assert events[-2:] == [
				('pre_invalidate', o.services.Id.hash('o.T.WriteRollback._2')),
				('invalidate', None),
			]
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# An IPL pre-invalidation error rolls back the uncommitted data.
	# ----------------------------------------------------------------------
	@classmethod
	def test_failed_pre_invalidate_prevents_commit(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			calls  = []

			def fail(owner_id):
				calls.append('pre_invalidate')
				raise RuntimeError('IPL disconnected')

			memory.ipl = SimpleNamespace(
				pre_invalidate = fail,
				invalidate     = lambda: calls.append('invalidate'),
			)

			failed = False

			try:
				memory.set('o.T.WriteFailure._1.value', 3, o.services.Id.hash('o.T.WriteFailure._1'))
			except RuntimeError:
				failed = True

			assert failed
			assert calls == ['pre_invalidate']
			assert memory.get('o.T.WriteFailure._1.value') is o.Undefined
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Every administrative change explicitly supplies its affected IDs.
	# ----------------------------------------------------------------------
	@classmethod
	def test_unknown_and_administrative_keys(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			events = cls._observe()
			memory.set('custom/unknown', 1, 0)

			assert events == [('pre_invalidate', 0), ('invalidate', None)]

			events.clear()
			memory.set('ids/12345', 'o.T.Unknown', 12345)
			memory.set('garbage/items/23456', 'o.T.Old', 23456)
			memory.set('routes/example', {'id': 34567}, (memory.root_id, 34567))
			memory.set('tree/parents/45678', 56789, (45678, 56789))

			written = {owner for name, owner in events if name == 'pre_invalidate'}
			assert {12345, 23456, 34567, 45678, 56789, memory.root_id} <= written
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Services propagate known IDs without interpreting storage keys.
	# ----------------------------------------------------------------------
	@classmethod
	def test_service_owner_notifications(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			events = cls._observe()
			proto  = 'o.T.WriteMapping'
			id     = o.services.Id.hash(proto)

			o.services.Id.set(proto)

			assert events == [
				('pre_invalidate', id),
				('invalidate', None),
			]

			events.clear()
			o.services.Route.set('write_mapping_route', {'id': id})

			assert events == [
				('pre_invalidate', memory.root_id),
				('pre_invalidate', id),
				('invalidate', None),
			]
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Clear reports owner once for an instance zone.
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
				('pre_invalidate', zone.owner_id),
				('invalidate', None),
			]
			assert memory.get('o.T.WriteClear._1.a') is o.Undefined
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Mixed-owner prefix removal uses caller-provided IDs, not key parsing.
	# ----------------------------------------------------------------------
	@classmethod
	def test_mixed_owner_prefix_deletion(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			memory.set('o.T.WriteMixed._1.left', 1, o.services.Id.hash('o.T.WriteMixed._1'))
			memory.set('o.T.WriteMixed._2.right', 2, o.services.Id.hash('o.T.WriteMixed._2'))
			events = cls._observe()

			memory.unset_all('o.T.WriteMixed.', (
				o.services.Id.hash('o.T.WriteMixed._1'),
				o.services.Id.hash('o.T.WriteMixed._2'),
			))

			written = {owner for name, owner in events if name == 'pre_invalidate'}
			assert o.services.Id.hash('o.T.WriteMixed._1') in written
			assert o.services.Id.hash('o.T.WriteMixed._2') in written
			assert events[-1] == ('invalidate', None)
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Bulk deletion can explicitly notify the owner and referenced targets.
	# ----------------------------------------------------------------------
	@classmethod
	def test_root_zone_auth_target_deletion(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			zone   = memory.zone('o.T.V._99.')
			zone.set('__auth__/12345', {5: 'rw'})
			events = cls._observe()

			zone.clear((zone.owner_id, 12345))

			written = {owner for name, owner in events if name == 'pre_invalidate'}
			assert zone.owner_id in written
			assert 12345 in written
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Provided owner IDs are sent directly, without hashing or parsing.
	# ----------------------------------------------------------------------
	@classmethod
	def test_explicit_owner_for_direct_memory_writes(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			events = cls._observe()

			memory.set('custom/opaque', 'updated', owner_id=13579)

			assert events == [
				('pre_invalidate', 13579),
				('invalidate', None),
			]
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Direct memory writes require an ID even when IPL is disconnected.
	# ----------------------------------------------------------------------
	@classmethod
	def test_owner_id_is_required(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			failed = False

			try:
				memory.set('custom/no_owner', 3)
			except TypeError:
				failed = True

			assert failed
			assert memory.get('custom/no_owner') is o.Undefined
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Neither missing deletes nor empty write batches emit notifications.
	# ----------------------------------------------------------------------
	@classmethod
	def test_reads_and_missing_deletions(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			events = cls._observe()

			assert memory.get('o.T.Absent') is o.Undefined
			memory.unset('o.T.Absent', 0)

			with memory.write():
				pass

			assert events == []
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)

	# Disconnected IPL does not change the explicit owner-ID contract.
	# ----------------------------------------------------------------------
	@classmethod
	def test_writes_without_ipl(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			assert memory.ipl is None
			memory.set('o.T.WriteStandalone._1.value', 10, o.services.Id.hash('o.T.WriteStandalone._1'))

			assert memory.get('o.T.WriteStandalone._1.value') == 10
			assert list(memory.keys('changes/')) == []
		finally:
			o.services.Memory.ipl = None
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestWriteTracking.run()
