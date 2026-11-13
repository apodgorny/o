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

	# Capture the exact order of Sync calls.
	# ----------------------------------------------------------------------
	@classmethod
	def _observe(cls):
		events = []
		o.services.Memory.sync = SimpleNamespace(
			register_change  = lambda txn, owner_id: events.append(('register_change', owner_id)),
			register_change_commit = lambda txn: events.append(('register_change_commit', None)),
			register_abort = lambda txn: None,
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
			assert memory.zone('garbage/items/').owner_id is None

			events = cls._observe()
			schema.set('field.type', 123)

			assert events == [
				('register_change', class_id),
				('register_change_commit', None),
			]
		finally:
			o.services.Memory.sync = o.services.Sync
			cls._restore_runtime(state)

	# register_change happens during the transaction; register_change_commit after commit.
	# ----------------------------------------------------------------------
	@classmethod
	def test_precedes_commit_and_confirms_afterward(cls):
		state = cls._patch_runtime()

		try:
			memory   = o.services.Memory
			key      = 'o.T.WriteBoundary._1.value'
			owner_id = o.services.Id.hash('o.T.WriteBoundary._1')
			events   = []

			def register_change(txn, entity_id):
				with memory.env.begin() as tx:
					assert tx.get(memory._key(key)) is None

				events.append(('register_change', entity_id))

			def register_change_commit(txn):
				assert memory._write is None

				with memory.env.begin() as tx:
					assert memory.from_bytes(tx.get(memory._key(key))) == 17

				events.append(('register_change_commit', None))

			memory.sync = SimpleNamespace(
				register_change  = register_change,
				register_change_commit = register_change_commit,
				register_abort = lambda txn: None,
			)
			memory.set(key, 17, owner_id)

			assert events == [
				('register_change', owner_id),
				('register_change_commit', None),
			]
			assert list(memory.keys('changes/')) == []
		finally:
			o.services.Memory.sync = o.services.Sync
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
			assert ('register_change', item.id) in events
			assert events[-1] == ('register_change_commit', None)

			events.clear()
			del item.value
			assert ('register_change', item.id) in events
			assert events[-1] == ('register_change_commit', None)
			assert item.value == 0
		finally:
			o.services.Memory.sync = o.services.Sync
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

			written = {owner for name, owner in events if name == 'register_change'}

			assert items.id in written
			assert mapping.id in written
			assert list(items) == [3, 4]
			assert dict(mapping.items()) == {'a': 2}
		finally:
			o.services.Memory.sync = o.services.Sync
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
			born   = {owner for name, owner in events if name == 'register_change'}

			assert {item.id, Model.id} <= born

			events.clear()
			item.drop()
			dropped = {owner for name, owner in events if name == 'register_change'}

			assert {item.id, Model.id} <= dropped
		finally:
			o.services.Memory.sync = o.services.Sync
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
			born   = {owner for name, owner in events if name == 'register_change'}

			assert {Child.id, Base.id} <= born

			events.clear()
			Child.drop()
			dropped = {owner for name, owner in events if name == 'register_change'}

			assert {Child.id, Base.id} <= dropped
		finally:
			o.services.Memory.sync = o.services.Sync
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

				assert events == [('register_change', zone.owner_id)]

				with memory.write() as inner:
					assert inner is outer
					zone.set('right', 2)
					zone.set('left', 3)

				assert events == [('register_change', zone.owner_id)] * 3

			assert events == [
				('register_change', zone.owner_id),
				('register_change', zone.owner_id),
				('register_change', zone.owner_id),
				('register_change_commit', None),
			]
			assert memory.get('o.T.WriteNested._1.left') == 3
			assert memory.get('o.T.WriteNested._1.right') == 2
		finally:
			o.services.Memory.sync = o.services.Sync
			cls._restore_runtime(state)

	# Rollback leaves pre-invalidation for Sync timeout but no confirmation.
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
			assert events == [('register_change', o.services.Id.hash('o.T.WriteRollback._1'))]
			assert memory.get('o.T.WriteRollback._1.value') is o.Undefined

			memory.set('o.T.WriteRollback._2.value', 8, o.services.Id.hash('o.T.WriteRollback._2'))
			assert events[-2:] == [
				('register_change', o.services.Id.hash('o.T.WriteRollback._2')),
				('register_change_commit', None),
			]
		finally:
			o.services.Memory.sync = o.services.Sync
			cls._restore_runtime(state)

	# A Sync notification error rolls back the uncommitted data.
	# ----------------------------------------------------------------------
	@classmethod
	def test_failed_register_change_prevents_commit(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			calls  = []

			def fail(txn, owner_id):
				calls.append('register_change')
				raise RuntimeError('Sync disconnected')

			memory.sync = SimpleNamespace(
				register_change  = fail,
				register_change_commit = lambda txn: calls.append('register_change_commit'),
				register_abort = lambda txn: None,
			)

			failed = False

			try:
				memory.set('o.T.WriteFailure._1.value', 3, o.services.Id.hash('o.T.WriteFailure._1'))
			except RuntimeError:
				failed = True

			assert failed
			assert calls == ['register_change']
			assert memory.get('o.T.WriteFailure._1.value') is o.Undefined
		finally:
			o.services.Memory.sync = o.services.Sync
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

			assert events == [('register_change', 0), ('register_change_commit', None)]

			events.clear()
			memory.set('ids/12345', 'o.T.Unknown', 12345)
			memory.set('garbage/items/23456', 'o.T.Old', 23456)
			memory.set('routes/example', {'id': 34567}, (memory.root_id, 34567))
			memory.set('tree/parents/45678', 56789, (45678, 56789))

			written = {owner for name, owner in events if name == 'register_change'}
			assert {12345, 23456, 34567, 45678, 56789, memory.root_id} <= written
		finally:
			o.services.Memory.sync = o.services.Sync
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
				('register_change', id),
				('register_change_commit', None),
			]

			events.clear()
			o.services.Route.set('write_mapping_route', {'id': id})

			assert events == [
				('register_change', memory.root_id),
				('register_change', id),
				('register_change_commit', None),
			]
		finally:
			o.services.Memory.sync = o.services.Sync
			cls._restore_runtime(state)

	# Auth writes notify the root instance and their target node.
	# ----------------------------------------------------------------------
	@classmethod
	def test_auth_owner_notifications(cls):
		state    = cls._patch_runtime()
		old_mode = o.TREE_MODE
		o.TREE_MODE = True

		try:
			node   = o.T()
			events = cls._observe()
			o.services.Auth.set(node, 7, 'rw')

			assert events == [
				('register_change', o.V.id),
				('register_change', node.id),
				('register_change_commit', None),
			]
		finally:
			o.TREE_MODE = old_mode
			o.services.Memory.sync = o.services.Sync
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
				('register_change', zone.owner_id),
				('register_change_commit', None),
			]
			assert memory.get('o.T.WriteClear._1.a') is o.Undefined
		finally:
			o.services.Memory.sync = o.services.Sync
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

			written = {owner for name, owner in events if name == 'register_change'}
			assert o.services.Id.hash('o.T.WriteMixed._1') in written
			assert o.services.Id.hash('o.T.WriteMixed._2') in written
			assert events[-1] == ('register_change_commit', None)
		finally:
			o.services.Memory.sync = o.services.Sync
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

			written = {owner for name, owner in events if name == 'register_change'}
			assert zone.owner_id in written
			assert 12345 in written
		finally:
			o.services.Memory.sync = o.services.Sync
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
				('register_change', 13579),
				('register_change_commit', None),
			]
		finally:
			o.services.Memory.sync = o.services.Sync
			cls._restore_runtime(state)

	# Direct memory writes require an ID even when Sync is disconnected.
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
			o.services.Memory.sync = o.services.Sync
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
			o.services.Memory.sync = o.services.Sync
			cls._restore_runtime(state)

	# Disconnected Sync does not change the explicit owner-ID contract.
	# ----------------------------------------------------------------------
	@classmethod
	def test_writes_with_native_sync(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			assert memory.sync is o.services.Sync
			memory.set('o.T.WriteStandalone._1.value', 10, o.services.Id.hash('o.T.WriteStandalone._1'))

			assert memory.get('o.T.WriteStandalone._1.value') == 10
			assert list(memory.keys('changes/')) == []
		finally:
			o.services.Memory.sync = o.services.Sync
			cls._restore_runtime(state)



	# A failed nested notification poisons the outer transaction even if caught.
	# ----------------------------------------------------------------------
	@classmethod
	def test_failed_nested_notification_aborts_outer_batch(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			zone   = memory.zone('o.T.WriteNestedFailure._1.')
			events = []

			def register_change(txn, owner_id):
				events.append(('register_change', owner_id))
				if len(events) == 2:
					raise ValueError('Sync refused change')

			memory.sync = SimpleNamespace(
				register_change  = register_change,
				register_change_commit = lambda txn: events.append(('register_change_commit', None)),
				register_abort = lambda txn: None,
			)
			aborted = False

			try:
				with memory.write():
					zone.set('first', 1)

					try:
						with memory.write():
							zone.set('second', 2)
					except ValueError:
						assert zone.get('first') == 1

					assert zone.get('second') == 2
			except RuntimeError as error:
				aborted = str(error) == 'Transaction aborted after an earlier failure'

			assert aborted
			assert events == [
				('register_change', zone.owner_id),
				('register_change', zone.owner_id),
			]
			assert zone.get('first') is o.Undefined
			assert zone.get('second') is o.Undefined
			assert memory.get('o.T.WriteNestedFailure._1.first') is o.Undefined
		finally:
			o.services.Memory.sync = o.services.Sync
			cls._restore_runtime(state)

	# The zone cache reflects committed LMDB after rollback of mixed operations.
	# ----------------------------------------------------------------------
	@classmethod
	def test_rolled_back_zone_set_unset_clear_reloads_cache(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			zone   = memory.zone('o.T.WriteZoneRollback._1.')
			zone.set('first', 1)
			zone.set('second', 2)
			rolled_back = False

			try:
				with memory.write():
					zone.set('first', 3)
					zone.unset('second')
					zone.set('temporary', 9)
					zone.clear()
					assert zone.get('first') is o.Undefined
					raise ValueError('cancel outer batch')
			except ValueError:
				rolled_back = True

			assert rolled_back
			assert zone.get('first') == 1
			assert zone.get('second') == 2
			assert zone.get('temporary') is o.Undefined
			assert memory.get('o.T.WriteZoneRollback._1.first') == 1
		finally:
			cls._restore_runtime(state)

	# A Sync error after commit reports committed data without a write rollback.
	# ----------------------------------------------------------------------
	@classmethod
	def test_failed_commit_confirmation_reports_committed_write(cls):
		state = cls._patch_runtime()

		try:
			memory   = o.services.Memory
			key      = 'o.T.WriteCommitError._1.value'
			owner_id = o.services.Id.hash('o.T.WriteCommitError._1')
			events   = []

			def fail(txn):
				events.append('register_change_commit')
				raise ValueError('transport failed after commit')

			memory.sync = SimpleNamespace(
				register_change  = lambda txn, id: events.append(('register_change', id)),
				register_change_commit = fail,
				register_abort = lambda txn: None,
			)
			committed = False

			try:
				memory.set(key, 7, owner_id)
			except RuntimeError as error:
				committed = (
					str(error) == 'LMDB committed; Sync confirmation failed'
					and isinstance(error.__cause__, ValueError)
				)

			assert committed
			assert events == [('register_change', owner_id), 'register_change_commit']
			assert memory._write is None
			assert memory.get(key) == 7
		finally:
			o.services.Memory.sync = o.services.Sync
			cls._restore_runtime(state)

	# A caught nested body failure still forces the outer batch to roll back.
	# ----------------------------------------------------------------------
	@classmethod
	def test_caught_nested_body_failure_aborts_outer_batch(cls):
		state = cls._patch_runtime()

		try:
			memory  = o.services.Memory
			zone    = memory.zone('o.T.WriteNestedBody._1.')
			aborted = False

			try:
				with memory.write():
					zone.set('first', 1)

					try:
						with memory.write():
							zone.set('second', 2)
							raise ValueError('caught by caller')
					except ValueError:
						assert zone.get('second') == 2
			except RuntimeError as error:
				aborted = str(error) == 'Transaction aborted after an earlier failure'

			assert aborted
			assert zone.get('first') is o.Undefined
			assert zone.get('second') is o.Undefined
		finally:
			cls._restore_runtime(state)



	# Reads inside an outer write batch must observe the staged LMDB state.
	# ----------------------------------------------------------------------
	@classmethod
	def test_pending_write_is_visible_to_memory_reads(cls):
		state = cls._patch_runtime()

		try:
			memory = o.services.Memory
			key    = 'o.T.WriteReadYourWrites._1.value'

			with memory.write():
				memory.set(key, 11, 0)
				assert memory.get(key) == 11
				assert memory.has(key)
				assert list(memory.items(key)) == [(key, 11)]
				assert list(memory.keys(key)) == [key]

				memory.unset(key, 0)
				assert memory.get(key) is o.Undefined
				assert not memory.has(key)
				assert list(memory.items(key)) == []
		finally:
			cls._restore_runtime(state)

if __name__ == '__main__':
	TestWriteTracking.run()
