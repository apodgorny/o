# ==============================================================================
# TEST TRANSACTIONAL WRITE TRACKING
# ==============================================================================
# Verify committed ID journals, structural writes, rollback, and key ownership.
# ==============================================================================

import os
import subprocess
import sys

import o


class TestWriteTracking(o.Tester):
	RUNTIME_PREFIX = 'o_write_tracking_'

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Collect the identities written after a committed storage revision.
	# ----------------------------------------------------------------------
	@classmethod
	def _changes(cls, revision):
		memory  = o.services.Memory
		records = list(memory.changes(revision))
		ids     = set()

		for transaction_id, changed_ids in records:
			assert transaction_id > revision
			ids.update(changed_ids)

		return records, ids

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# A zone's owner identity is derived from its proto only once.
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

			revision = memory.revision()
			schema.set('field.type', 123)
			_, changed = cls._changes(revision)

			assert class_id in changed
			assert o.services.Id.hash('o.T.WriteOwner._') not in changed
		finally:
			cls._restore_runtime(state)

	# Every successful field write and deletion is committed to the journal.
	# ----------------------------------------------------------------------
	@classmethod
	def test_field_writes_and_deletion(cls):
		state = cls._patch_runtime()

		try:
			Model    = o.T.extend('WriteField', value=o.F(int, default=0))
			item     = Model(value=1)
			memory   = o.services.Memory
			revision = memory.revision()

			item.value = 2
			del item.value

			records, changed = cls._changes(revision)

			assert len(records) >= 2
			assert item.id in changed
			assert item.value == 0
		finally:
			cls._restore_runtime(state)

	# Collection changes are attributed to the collection, not its values.
	# ----------------------------------------------------------------------
	@classmethod
	def test_list_and_dict_writes(cls):
		state = cls._patch_runtime()

		try:
			items    = o.List([1, 2])
			mapping  = o.Dict({'a': 1})
			memory   = o.services.Memory
			revision = memory.revision()

			items[0] = 3
			items.append(4)
			del items[1]
			mapping['a'] = 2
			mapping['b'] = 3
			del mapping['b']

			records, changed = cls._changes(revision)

			assert records
			assert items.id in changed
			assert mapping.id in changed
			assert list(items) == [3, 4]
			assert dict(mapping.items()) == {'a': 2}
		finally:
			cls._restore_runtime(state)

	# A new entity must also invalidate class membership enumeration.
	# ----------------------------------------------------------------------
	@classmethod
	def test_instance_birth_and_death(cls):
		state = cls._patch_runtime()

		try:
			Model    = o.T.extend('WriteLifecycle', value=int)
			memory   = o.services.Memory
			revision = memory.revision()
			item     = Model(value=5)
			_, born  = cls._changes(revision)

			assert item.id in born
			assert Model.id in born

			revision = memory.revision()
			item.drop()
			_, dropped = cls._changes(revision)

			assert item.id in dropped
			assert Model.id in dropped
		finally:
			cls._restore_runtime(state)

	# New child classes must invalidate their parent's subclass enumeration.
	# ----------------------------------------------------------------------
	@classmethod
	def test_class_birth_and_death(cls):
		state = cls._patch_runtime()

		try:
			Base     = o.T.extend('WriteClassBase')
			memory   = o.services.Memory
			revision = memory.revision()
			Child    = Base.extend('WriteClassChild')
			_, born  = cls._changes(revision)

			assert Child.id in born
			assert Base.id in born

			revision = memory.revision()
			Child.drop()
			_, dropped = cls._changes(revision)

			assert Child.id in dropped
			assert Base.id in dropped
		finally:
			cls._restore_runtime(state)

	# Nested mutations share one LMDB transaction and one deduplicated record.
	# ----------------------------------------------------------------------
	@classmethod
	def test_nested_commit_and_deduplication(cls):
		state = cls._patch_runtime()

		try:
			memory   = o.services.Memory
			zone     = memory.zone('o.T.WriteNested._1.')
			revision = memory.revision()

			with memory.write() as outer:
				zone.set('left', 1)

				with memory.write() as inner:
					assert inner is outer
					zone.set('right', 2)
					zone.set('left', 3)

				assert list(memory.changes(revision)) == []

			records, changed = cls._changes(revision)

			assert len(records) == 1
			assert changed == {zone.owner_id}
			assert memory.get('o.T.WriteNested._1.left') == 3
			assert memory.get('o.T.WriteNested._1.right') == 2
		finally:
			cls._restore_runtime(state)

	# A failed transaction must roll back both its data and its journal entry.
	# ----------------------------------------------------------------------
	@classmethod
	def test_rollback_discards_data_and_id_set(cls):
		state = cls._patch_runtime()

		try:
			memory   = o.services.Memory
			revision = memory.revision()
			failed   = False

			try:
				with memory.write():
					memory.set('o.T.WriteRollback._1.value', 7)
					raise ValueError('abort')
			except ValueError:
				failed = True

			assert failed
			assert memory.get('o.T.WriteRollback._1.value') is o.Undefined
			assert list(memory.changes(revision)) == []

			memory.set('o.T.WriteRollback._2.value', 8)
			_, changed = cls._changes(revision)

			assert o.services.Id.hash('o.T.WriteRollback._1') not in changed
			assert o.services.Id.hash('o.T.WriteRollback._2') in changed
		finally:
			cls._restore_runtime(state)

	# Unknown keys retain a conservative full-ontology invalidation marker.
	# ----------------------------------------------------------------------
	@classmethod
	def test_unknown_and_administrative_keys(cls):
		state = cls._patch_runtime()

		try:
			memory   = o.services.Memory
			revision = memory.revision()

			memory.set('custom/unknown', 1)
			_, unknown = cls._changes(revision)

			assert 0 in unknown

			revision = memory.revision()
			memory.set('ids/12345', 'o.T.Unknown')
			memory.set('garbage/items/23456', 'o.T.Old')
			memory.set('routes/example', {'id': 34567})
			memory.set('tree/parents/45678', 56789)
			_, changed = cls._changes(revision)

			assert {12345, 23456, 34567, 45678, 56789, memory.root_id} <= changed
		finally:
			cls._restore_runtime(state)

	# Clearing an instance zone should use its known owner instead of hashing.
	# ----------------------------------------------------------------------
	@classmethod
	def test_instance_zone_clear(cls):
		state = cls._patch_runtime()

		try:
			memory   = o.services.Memory
			zone     = memory.zone('o.T.WriteClear._1.')
			zone.set('a', 1)
			zone.set('b', 2)
			revision = memory.revision()

			zone.clear()
			records, changed = cls._changes(revision)

			assert len(records) == 1
			assert changed == {zone.owner_id}
			assert memory.get('o.T.WriteClear._1.a') is o.Undefined
		finally:
			cls._restore_runtime(state)

	# The journal must be readable by a separate process without an O runtime.
	# ----------------------------------------------------------------------
	@classmethod
	def test_cross_process_journal_read(cls):
		state = cls._patch_runtime()

		try:
			memory   = o.services.Memory
			revision = memory.revision()
			memory.set('o.T.WriteRemote._3.value', 17)

			script = '''
import lmdb
import msgpack
import sys

env = lmdb.open(sys.argv[1], readonly=True, lock=True, max_dbs=1)
revision = int(sys.argv[2])

with env.begin() as tx:
	cursor = tx.cursor()
	found = cursor.set_range(f'changes/{revision + 1:020d}'.encode())
	assert found
	changed = set(msgpack.unpackb(cursor.value(), raw=False))
	assert int(sys.argv[3]) in changed

env.close()
'''
			result = subprocess.run(
				[sys.executable, '-c', script, memory.path, str(revision),
				 str(o.services.Id.hash('o.T.WriteRemote._3'))],
				capture_output = True,
				text           = True,
				timeout        = 20,
			)

			assert result.returncode == 0, result.stdout + result.stderr
		finally:
			cls._restore_runtime(state)

	# Read-only operations do not leave journal entries.
	# ----------------------------------------------------------------------
	@classmethod
	def test_reads_and_missing_deletions(cls):
		state = cls._patch_runtime()

		try:
			memory   = o.services.Memory
			revision = memory.revision()

			assert memory.get('o.T.Absent') is o.Undefined
			memory.unset('o.T.Absent')
			assert list(memory.changes(revision)) == []
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestWriteTracking.run()
