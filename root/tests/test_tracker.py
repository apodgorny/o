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

			with o.services.Tracker.track_reads(reads):
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
	def test_cache_miss_observes_read(cls):
		state = cls._patch_runtime()

		try:
			Model  = o.T.extend('TrackerCacheMiss', value=int)
			item   = Model(value=5)
			reads  = []
			del item.__dict__['value']

			with o.services.Tracker.track_reads(reads):
				assert item.value == 5
				assert item.value == 5

			assert reads == [item.id, item.id]
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

			with o.services.Tracker.track_reads(reads):
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

			with o.services.Tracker.track_reads(reads):
				Model = o.T.extend('TrackerNewClassInScope', value=int)
				item  = Model(value=8)

				assert item.value == 8
				Model.extra = o.F(str, default='hello')
				assert item.extra == 'hello'

			assert [entity_id for entity_id in reads if entity_id == item.id] == [item.id, item.id]
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

			with o.services.Tracker.track_reads(reads):
				assert items[0] == 1
				assert len(items) == 2
				assert list(items) == [1, 2]

			assert len(reads) >= 3
			assert set(reads) == {items.id}
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

			with o.services.Tracker.track_reads(reads):
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

			with o.services.Tracker.track_reads(reads):
				assert 'a' in mapping

			assert reads == [mapping.id]
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
			
			with o.services.Tracker.track_reads(outer_reads):
				first.value

				with o.services.Tracker.track_reads(inner_reads):
					other.value
					other.value = 4

				first.value

			assert [entity_id for entity_id in outer_reads if entity_id in (first.id, other.id)] == [first.id, other.id, first.id]
			assert [entity_id for entity_id in inner_reads if entity_id == other.id] == [other.id]
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
				with tracker.track_reads(reads):
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

	# Reject non-list read identity outputs without patching classes.
	# ----------------------------------------------------------------------
	@classmethod
	def test_invalid_tracking_arguments(cls):
		tracker = o.services.Tracker

		for ids in (None, (), 'ids', {}):
			failed = False

			try:
				with tracker.track_reads(ids):
					assert False
			except TypeError:
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
				with o.services.Tracker.track_reads(reads):
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
				with o.services.Tracker.track_reads(reads):
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

			with o.services.Tracker.track_reads(reads):
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
					reads_b  = []

					assert alice.T is not bob.T
					assert alice.services.Tracker is not bob.services.Tracker

					with alice.services.Tracker.track_reads(reads_a):
						assert second.value == 2
						second.value = 3
						assert reads_a == []

						with bob.services.Tracker.track_reads(reads_b):
							assert first.value == 1
							assert second.value == 3
							first.value = 4
							second.value = 5

						assert [entity_id for entity_id in reads_a if entity_id == first.id] == [first.id]
						assert [entity_id for entity_id in reads_b if entity_id == second.id] == [second.id]
				finally:
					for world in (alice, bob):
						if 'env' in world.services.Memory.__dict__:
							world.services.Memory.env.close()



if __name__ == '__main__':
	TestTracker.run()