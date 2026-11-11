# ==============================================================================
# TEST TRACKER
# ==============================================================================
# Verify reversible tracking of persistent fields and collection mutations.
# ==============================================================================

import asyncio
import tempfile
import threading
import time

from concurrent.futures import ThreadPoolExecutor
from types import DynamicClassAttribute, SimpleNamespace
from unittest.mock import patch

import o


class TestTracker(o.Tester):
	RUNTIME_PREFIX = 'o_tracker_'

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Preserve the order and repetition of cached attribute reads.
	# ----------------------------------------------------------------------
	@classmethod
	def test_cached_field_reads(cls):
		state = cls._patch_runtime()

		try:
			Model = o.T.extend('TrackerCachedReads', value=int)
			first = Model(value=11)
			other = Model(value=22)
			reads = []

			with o.services.Tracker.track('r', reads):
				assert first.value == 11
				assert other.value == 22
				assert first.value == 11

			assert reads == [first.id, other.id, first.id]
			assert first.value == 11
			assert reads == [first.id, other.id, first.id]
		finally:
			cls._restore_runtime(state)

	# Read an uncached field without mistaking its cache fill for a write.
	# ----------------------------------------------------------------------
	@classmethod
	def test_cache_miss_does_not_count_as_write(cls):
		state = cls._patch_runtime()

		try:
			Model  = o.T.extend('TrackerCacheMiss', value=int)
			item   = Model(value=5)
			reads  = []
			writes = []
			del item.__dict__['value']

			with o.services.Tracker.track('rw', reads, writes):
				assert item.value == 5
				assert item.value == 5

			assert reads == [item.id, item.id]
			assert writes == []
		finally:
			cls._restore_runtime(state)

	# Observe writes without counting the reads performed around them.
	# ----------------------------------------------------------------------
	@classmethod
	def test_field_writes(cls):
		state = cls._patch_runtime()

		try:
			Model  = o.T.extend('TrackerFieldWrites', value=int)
			item   = Model(value=1)
			writes = []

			with o.services.Tracker.track('w', writes):
				assert item.value == 1
				item.value = 2
				assert item.value == 2
				item.value = 3

			assert writes == [item.id, item.id]
			assert item.value == 3
		finally:
			cls._restore_runtime(state)

	# Capture persisted field deletion with and without a populated cache.
	# ----------------------------------------------------------------------
	@classmethod
	def test_field_deletion(cls):
		state = cls._patch_runtime()

		try:
			Model  = o.T.extend('TrackerFieldDeletion', value=o.F(int, default=0))
			first  = Model(value=1)
			other  = Model(value=2)
			writes = []
			del other.__dict__['value']

			with o.services.Tracker.track('w', writes):
				del first.value
				del other.value

			assert writes == [first.id, other.id]
			assert first.value == 0
			assert other.value == 0
		finally:
			cls._restore_runtime(state)

	# Capture each access direction independently within one context.
	# ----------------------------------------------------------------------
	@classmethod
	def test_read_write_mode(cls):
		state = cls._patch_runtime()

		try:
			Model  = o.T.extend('TrackerCombinedMode', value=int)
			item   = Model(value=1)
			reads  = []
			writes = []

			with o.services.Tracker.track('rw', reads, writes):
				assert item.value == 1
				item.value = 7
				assert item.value == 7

			assert reads == [item.id, item.id]
			assert writes == [item.id]
		finally:
			cls._restore_runtime(state)

	# Keep class-side field defaults visible while tracking instance access.
	# ----------------------------------------------------------------------
	@classmethod
	def test_field_defaults_and_inheritance(cls):
		state = cls._patch_runtime()

		try:
			Base   = o.T.extend('TrackerInheritedBase', value=o.F(int, default=17))
			Child  = Base.extend('TrackerInheritedChild', other=int)
			item   = Child(other=9)
			reads  = []

			with o.services.Tracker.track('r', reads):
				assert Base.value == 17
				assert Child.value == 17
				assert item.value == 17
				assert item.other == 9

			assert reads == [item.id, item.id]
		finally:
			cls._restore_runtime(state)

	# Include classes and fields published after tracking has already begun.
	# ----------------------------------------------------------------------
	@classmethod
	def test_new_class_and_field_inside_scope(cls):
		state = cls._patch_runtime()

		try:
			reads = []

			with o.services.Tracker.track('r', reads):
				Model = o.T.extend('TrackerNewClassInScope', value=int)
				item  = Model(value=8)

				assert item.value == 8
				Model.extra = o.F(str, default='hello')
				assert item.extra == 'hello'

			assert reads == [item.id, item.id]
			assert item.extra == 'hello'
		finally:
			cls._restore_runtime(state)

	# Instrument collection reads through their common in-memory index.
	# ----------------------------------------------------------------------
	@classmethod
	def test_list_reads(cls):
		state = cls._patch_runtime()

		try:
			items = o.List([1, 2])
			reads = []

			with o.services.Tracker.track('r', reads):
				assert items[0] == 1
				assert len(items) == 2
				assert list(items) == [1, 2]

			assert len(reads) >= 3
			assert set(reads) == {items.id}
		finally:
			cls._restore_runtime(state)

	# Capture all list mutations at the existing single save boundary.
	# ----------------------------------------------------------------------
	@classmethod
	def test_list_writes(cls):
		state = cls._patch_runtime()

		try:
			items  = o.List([1, 2])
			writes = []

			with o.services.Tracker.track('w', writes):
				items[0] = 3
				items.append(4)
				del items[1]

			assert writes == [items.id, items.id, items.id]
			assert list(items) == [3, 4]
		finally:
			cls._restore_runtime(state)

	# Catch list methods implemented through a visible Python copy.
	# ----------------------------------------------------------------------
	@classmethod
	def test_list_builtin_mutations(cls):
		state = cls._patch_runtime()

		try:
			items  = o.List([2, 1])
			writes = []

			with o.services.Tracker.track('w', writes):
				items.reverse()
				items.pop()

			assert writes == [items.id, items.id]
			assert list(items) == [1]
		finally:
			cls._restore_runtime(state)

	# Observe dictionary lookup, membership, length and iteration.
	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_reads(cls):
		state = cls._patch_runtime()

		try:
			mapping = o.Dict({'a': 1})
			reads   = []

			with o.services.Tracker.track('r', reads):
				assert mapping['a'] == 1
				assert 'a' in mapping
				assert len(mapping) == 1
				assert list(mapping.keys()) == ['a']
				assert list(mapping.items()) == [('a', 1)]

			assert len(reads) >= 5
			assert set(reads) == {mapping.id}
		finally:
			cls._restore_runtime(state)

	# Observe membership even though dictionary lookup uses a separate index.
	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_membership_only(cls):
		state = cls._patch_runtime()

		try:
			mapping = o.Dict({'a': 1})
			reads   = []

			with o.services.Tracker.track('r', reads):
				assert 'a' in mapping

			assert reads == [mapping.id]
		finally:
			cls._restore_runtime(state)

	# Capture item replacement, insertion, update and removal once each.
	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_writes(cls):
		state = cls._patch_runtime()

		try:
			mapping = o.Dict({'a': 1})
			writes  = []

			with o.services.Tracker.track('w', writes):
				mapping['a'] = 2
				mapping.update({'b': 3})
				del mapping['b']

			assert writes == [mapping.id, mapping.id, mapping.id]
			assert dict(mapping.items()) == {'a': 2}
		finally:
			cls._restore_runtime(state)

	# Catch mutations implemented through dictionary built-in methods.
	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_builtin_mutations(cls):
		state = cls._patch_runtime()

		try:
			mapping = o.Dict({'a': 1, 'b': 2})
			writes  = []

			with o.services.Tracker.track('w', writes):
				mapping.pop('a')
				mapping.clear()

			assert writes == [mapping.id, mapping.id]
			assert dict(mapping.items()) == {}
		finally:
			cls._restore_runtime(state)

	# Rebuilding a collection cache is a read, not a persisted mutation.
	# ----------------------------------------------------------------------
	@classmethod
	def test_collection_reconstruction_is_not_a_write(cls):
		state = cls._patch_runtime()

		try:
			items   = o.List([1, 2])
			mapping = o.Dict({'a': 1})
			writes  = []

			with o.services.Tracker.track('w', writes):
				items.__load_items__()
				mapping.__load_items__()

			assert writes == []
		finally:
			cls._restore_runtime(state)

	# Forward nested observations to every matching scope in lexical order.
	# ----------------------------------------------------------------------
	@classmethod
	def test_nested_scopes(cls):
		state = cls._patch_runtime()

		try:
			Model        = o.T.extend('TrackerNested', value=int)
			first        = Model(value=1)
			other        = Model(value=2)
			outer_reads  = []
			inner_reads  = []
			inner_writes = []

			with o.services.Tracker.track('r', outer_reads):
				first.value

				with o.services.Tracker.track('rw', inner_reads, inner_writes):
					other.value
					other.value = 4

				first.value

			assert outer_reads == [first.id, other.id, first.id]
			assert inner_reads == [other.id]
			assert inner_writes == [other.id]
		finally:
			cls._restore_runtime(state)

	# Restore the class dictionary and hook implementations after an error.
	# ----------------------------------------------------------------------
	@classmethod
	def test_exception_restores_descriptors(cls):
		state = cls._patch_runtime()

		try:
			Model           = o.T.extend('TrackerException', value=int)
			item            = Model(value=1)
			tracker         = o.services.Tracker
			original_save   = o.List.__dict__['__save_items__']
			original_publish = o.TMeta.__dict__['__publish_field__']
			reads           = []
			failed          = False

			try:
				with tracker.track('r', reads):
					assert isinstance(Model.__dict__['value'], DynamicClassAttribute)
					assert isinstance(o.List.__dict__['__items__'], DynamicClassAttribute)
					item.value
					raise ValueError('Expected failure')
			except ValueError:
				failed = True

			assert failed
			assert reads == [item.id]
			assert 'value' not in Model.__dict__
			assert '__items__' not in o.List.__dict__
			assert o.List.__dict__['__save_items__'] is original_save
			assert o.TMeta.__dict__['__publish_field__'] is original_publish
		finally:
			cls._restore_runtime(state)

	# Reject unsupported modes and non-list outputs without patching classes.
	# ----------------------------------------------------------------------
	@classmethod
	def test_invalid_tracking_arguments(cls):
		tracker = o.services.Tracker
		values  = [
			('unknown', [], []),
			('r', None, None),
			('w', None, None),
			('rw', [], None),
		]

		for mode, reads, writes in values:
			failed = False

			try:
				with tracker.track(mode, reads, writes):
					assert False
			except (TypeError, ValueError):
				failed = True

			assert failed

		assert tracker._active_count == 0

	# Separate simultaneous callers even when class descriptors are shared.
	# ----------------------------------------------------------------------
	@classmethod
	def test_concurrent_threads(cls):
		state = cls._patch_runtime()

		try:
			Model   = o.T.extend('TrackerThreaded', value=int)
			first   = Model(value=1)
			other   = Model(value=2)
			barrier = threading.Barrier(2)
			reads_a = []
			reads_b = []

			def worker(item, reads):
				with o.services.Tracker.track('r', reads):
					barrier.wait(timeout=10)
					item.value
					item.value

			with ThreadPoolExecutor(max_workers=2) as pool:
				first_job = pool.submit(worker, first, reads_a)
				other_job = pool.submit(worker, other, reads_b)
				first_job.result(timeout=15)
				other_job.result(timeout=15)

			assert reads_a == [first.id, first.id]
			assert reads_b == [other.id, other.id]
		finally:
			cls._restore_runtime(state)

	# Keep concurrently interleaved asynchronous tasks independent.
	# ----------------------------------------------------------------------
	@classmethod
	def test_concurrent_async_tasks(cls):
		state = cls._patch_runtime()

		try:
			Model   = o.T.extend('TrackerAsync', value=int)
			first   = Model(value=1)
			other   = Model(value=2)
			reads_a = []
			reads_b = []

			async def worker(item, reads):
				with o.services.Tracker.track('r', reads):
					item.value
					await asyncio.sleep(0)
					item.value

			async def run():
				await asyncio.gather(worker(first, reads_a), worker(other, reads_b))

			asyncio.run(run())

			assert reads_a == [first.id, first.id]
			assert reads_b == [other.id, other.id]
		finally:
			cls._restore_runtime(state)

	# Ensure write-only observation leaves the read-side fast path untouched.
	# ----------------------------------------------------------------------
	@classmethod
	def test_write_only_does_not_patch_reads(cls):
		state = cls._patch_runtime()

		try:
			Model            = o.T.extend('TrackerWriteOnly', value=int)
			item             = Model(value=1)
			items            = o.List([1])
			original_assign  = o.T.__dict__['__setattr__']
			original_publish = o.TMeta.__dict__['__publish_field__']
			writes           = []

			with o.services.Tracker.track('w', writes):
				assert 'value' not in Model.__dict__
				assert '__items__' not in o.List.__dict__
				assert o.TMeta.__dict__['__publish_field__'] is original_publish
				assert o.T.__dict__['__setattr__'] is not original_assign
				assert item.value == 1
				assert items[0] == 1
				item.value = 2
				items.append(3)

			assert writes == [item.id, items.id]
			assert o.T.__dict__['__setattr__'] is original_assign
		finally:
			cls._restore_runtime(state)

	# Ensure read-only observation leaves write hooks uninstalled.
	# ----------------------------------------------------------------------
	@classmethod
	def test_read_only_does_not_patch_writes(cls):
		state = cls._patch_runtime()

		try:
			Model           = o.T.extend('TrackerReadOnly', value=int)
			item            = Model(value=1)
			items           = o.List([1])
			original_assign = o.T.__dict__['__setattr__']
			original_save   = o.List.__dict__['__save_items__']
			reads           = []

			with o.services.Tracker.track('r', reads):
				assert isinstance(Model.__dict__['value'], DynamicClassAttribute)
				assert isinstance(o.List.__dict__['__items__'], DynamicClassAttribute)
				assert o.T.__dict__['__setattr__'] is original_assign
				assert o.List.__dict__['__save_items__'] is original_save
				assert item.value == 1
				assert items[0] == 1
				item.value = 2
				items.append(3)

			assert reads.count(item.id) >= 1
			assert reads.count(items.id) >= 1
			assert o.List.__dict__['__save_items__'] is original_save
		finally:
			cls._restore_runtime(state)

	# Install and release each direction independently for nested mixed modes.
	# ----------------------------------------------------------------------
	@classmethod
	def test_nested_mixed_modes_release_independently(cls):
		state = cls._patch_runtime()

		try:
			Model           = o.T.extend('TrackerModeSwitch', value=int)
			item            = Model(value=1)
			tracker         = o.services.Tracker
			original_assign = o.T.__dict__['__setattr__']
			reads           = []
			writes          = []

			with tracker.track('w', writes):
				assert 'value' not in Model.__dict__
				item.value

				with tracker.track('r', reads):
					assert isinstance(Model.__dict__['value'], DynamicClassAttribute)
					assert o.T.__dict__['__setattr__'] is not original_assign
					assert item.value == 1
					item.value = 2

				assert 'value' not in Model.__dict__
				assert o.T.__dict__['__setattr__'] is not original_assign
				item.value = 3

			assert reads == [item.id]
			assert writes == [item.id, item.id]
			assert o.T.__dict__['__setattr__'] is original_assign

			with tracker.track('r', reads):
				assert isinstance(Model.__dict__['value'], DynamicClassAttribute)
				with tracker.track('w', writes):
					item.value = 4
				assert o.T.__dict__['__setattr__'] is original_assign
				assert item.value == 4

			assert reads == [item.id, item.id]
			assert writes == [item.id, item.id, item.id]
			assert 'value' not in Model.__dict__
		finally:
			cls._restore_runtime(state)

	# Keep different tracking modes isolated when asyncio tasks interleave.
	# ----------------------------------------------------------------------
	@classmethod
	def test_concurrent_mixed_async_modes(cls):
		state = cls._patch_runtime()

		try:
			Model  = o.T.extend('TrackerAsyncMixed', value=int)
			item   = Model(value=1)
			reads  = []
			writes = []

			async def read_task():
				with o.services.Tracker.track('r', reads):
					assert item.value == 1
					await asyncio.sleep(0)
					await asyncio.sleep(0)
					assert item.value == 2

			async def write_task():
				with o.services.Tracker.track('w', writes):
					await asyncio.sleep(0)
					item.value = 2
					await asyncio.sleep(0)

			async def run():
				await asyncio.gather(read_task(), write_task())

			asyncio.run(run())

			assert reads == [item.id, item.id]
			assert writes == [item.id]
		finally:
			cls._restore_runtime(state)

	# A fork's tracker must observe only its own ontology objects.
	# ----------------------------------------------------------------------
	@classmethod
	def test_forked_ontologies_keep_trackers_isolated(cls):
		with tempfile.TemporaryDirectory(prefix='o_tracker_forks_') as directory:
			app   = SimpleNamespace(__lib_path__=directory)
			alice = o.fork(f'tracker_alice_{time.time_ns()}')
			bob   = o.fork(f'tracker_bob_{time.time_ns()}')

			with patch.object(type(o), '__app__', app):
				try:
					alice.start()
					bob.start()

					Alice  = alice.T.extend('TrackerForkPerson', value=int)
					Bob    = bob.T.extend('TrackerForkPerson', value=int)
					first  = Alice(value=1)
					second = Bob(value=2)
					reads_a  = []
					writes_a = []
					reads_b  = []
					writes_b = []

					assert alice.T is not bob.T
					assert alice.services.Tracker is not bob.services.Tracker

					with alice.services.Tracker.track('rw', reads_a, writes_a):
						assert second.value == 2
						second.value = 3
						assert reads_a == []
						assert writes_a == []

						with bob.services.Tracker.track('rw', reads_b, writes_b):
							assert first.value == 1
							assert second.value == 3
							first.value = 4
							second.value = 5

						assert reads_a == [first.id]
						assert writes_a == [first.id]
						assert reads_b == [second.id]
						assert writes_b == [second.id]
				finally:
					for world in (alice, bob):
						if 'env' in world.services.Memory.__dict__:
							world.services.Memory.env.close()



if __name__ == '__main__':
	TestTracker.run()