# ==============================================================================
# TEST SYNC
# ==============================================================================
# Verify committed local/remote delivery, isolation, and LMDB integration.
# ==============================================================================

import threading
import time

from concurrent.futures import ThreadPoolExecutor
from queue              import Empty, Queue
from types              import SimpleNamespace
from unittest.mock      import patch

import o


class TestSync(o.Tester):

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Give each test its own service singleton and worker.
	# ----------------------------------------------------------------------
	@classmethod
	def _sync(cls):
		service_type = type('SyncTest', (type(o.services.Sync),), {})
		service      = service_type()
		service.initialize()

		return service

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Commit publishes deduplicated IDs outside the writer thread.
	# ----------------------------------------------------------------------
	@classmethod
	def test_committed_change(cls):
		sync    = cls._sync()
		results = Queue()

		try:
			sync.subscribe(lambda ids: results.put((ids, threading.get_ident())))
			sync.register_change(7, 11)
			sync.register_change(7, 11)
			sync.register_change(7, 22)
			sync.publish_change(sync.changes.pop(7), local=True)

			ids, thread_id = results.get(timeout=2)
			assert ids == frozenset({11, 22})
			assert thread_id != threading.get_ident()
			assert sync.changes == {}
		finally:
			sync.close()

	# Pending IDs must remain invisible until the outer commit publishes.
	# ----------------------------------------------------------------------
	@classmethod
	def test_no_precommit_publication(cls):
		sync    = cls._sync()
		results = Queue()

		try:
			sync.subscribe(results.put)
			sync.register_change(10, 19)
			sync.register_change(10, 23)
			assert sync.changes[10] == [19, 23]

			try:
				unexpected = results.get(timeout=0.05)
			except Empty:
				unexpected = None

			assert unexpected is None
			sync.publish_change(sync.changes.pop(10), local=True)
			assert results.get(timeout=2) == frozenset({19, 23})
		finally:
			sync.close()

	# Both IPC and local commits reach subscribers through the same worker.
	# ----------------------------------------------------------------------
	@classmethod
	def test_single_local_remote_dispatch(cls):
		sync         = cls._sync()
		published    = Queue()
		subscribed   = Queue()
		transport    = SimpleNamespace(
			send = lambda ids: published.put((ids, threading.get_ident())),
		)

		try:
			sync.subscribe(transport.send, local_only=True)
			sync.subscribe(lambda ids: subscribed.put((ids, threading.get_ident())))

			sync.register_change(90001, 90002)
			sync.publish_change(sync.changes.pop(90001), local=True)

			local_out, local_thread = published.get(timeout=2)
			local_in, subscriber_thread = subscribed.get(timeout=2)
			assert local_out == local_in == frozenset({90002})
			assert local_thread == subscriber_thread != threading.get_ident()

			sync.publish_change(frozenset({90003}), local=False)

			remote_in, remote_thread = subscribed.get(timeout=2)
			assert remote_in == frozenset({90003})
			assert remote_thread == local_thread
			assert published.empty()
		finally:
			sync.close()
	# Rollback removes pending IDs and never publishes.
	# ----------------------------------------------------------------------
	@classmethod
	def test_abort(cls):
		sync    = cls._sync()
		results = Queue()

		try:
			sync.subscribe(results.put)
			sync.register_change(20, 17)
			sync.changes.pop(20, None)
			assert sync.changes == {}

			try:
				unexpected = results.get(timeout=0.15)
			except Empty:
				unexpected = None

			assert unexpected is None
		finally:
			sync.close()

	# Unknown owner zero requires a full invalidation rather than partial IDs.
	# ----------------------------------------------------------------------
	@classmethod
	def test_full_invalidation(cls):
		sync    = cls._sync()
		results = Queue()

		try:
			sync.subscribe(results.put)
			sync.register_change(30, 100)
			sync.register_change(30, 0)
			sync.publish_change(sync.changes.pop(30), local=True)
			assert results.get(timeout=2) is None
		finally:
			sync.close()


	# Global subscribers see every owner; selective subscribers see only
	# the intersection with the changed IDs, never unrelated owners.
	# ----------------------------------------------------------------------
	@classmethod
	def test_filtered_and_global_subscriptions(cls):
		sync     = cls._sync()
		global_q = Queue()
		filter_q = Queue()
		other_q  = Queue()

		try:
			sync.subscribe(global_q.put)
			sync.subscribe({11, 33}, filter_q.put)
			sync.subscribe({77}, other_q.put)

			for id in (11, 22, 33):
				sync.register_change(801, id)

			sync.publish_change(sync.changes.pop(801), local=True)

			assert global_q.get(timeout=2) == frozenset({11, 22, 33})
			assert filter_q.get(timeout=2) == frozenset({11, 33})

			try:
				unexpected = other_q.get(timeout=0.05)
			except Empty:
				unexpected = None

			assert unexpected is None
		finally:
			sync.close()

	# ID zero requests full invalidation even for empty subscriptions.
	# Every subscriber receives only the zero sentinel in that case.
	# ----------------------------------------------------------------------
	@classmethod
	def test_filtered_full_invalidation(cls):
		sync      = cls._sync()
		global_q  = Queue()
		filtered  = Queue()
		empty_ids = Queue()

		try:
			sync.subscribe(global_q.put)
			sync.subscribe(frozenset({55}), filtered.put)
			sync.subscribe(set(), empty_ids.put)
			sync.register_change(802, 99)
			sync.register_change(802, 0)
			sync.publish_change(sync.changes.pop(802), local=True)

			for result in (global_q, filtered, empty_ids):
				assert result.get(timeout=2) is None
		finally:
			sync.close()

	# Capture the watched set at subscribe time. A second registration of
	# the same callback replaces its scope rather than duplicating delivery.
	# ----------------------------------------------------------------------
	@classmethod
	def test_filtered_subscription_snapshot_and_replace(cls):
		sync    = cls._sync()
		global_q = Queue()
		results = Queue()
		watched = {101}

		try:
			sync.subscribe(global_q.put)
			callback = sync.subscribe(watched, results.put)
			assert callback == results.put

			watched.clear()
			watched.add(102)
			sync.register_change(803, 101)
			sync.publish_change(sync.changes.pop(803), local=True)

			assert global_q.get(timeout=2) == frozenset({101})
			assert results.get(timeout=2) == frozenset({101})

			sync.subscribe({102}, callback)
			sync.register_change(804, 101)
			sync.register_change(804, 102)
			sync.publish_change(sync.changes.pop(804), local=True)

			assert global_q.get(timeout=2) == frozenset({101, 102})
			assert results.get(timeout=2) == frozenset({102})

			try:
				unexpected = results.get(timeout=0.05)
			except Empty:
				unexpected = None

			assert unexpected is None
		finally:
			sync.close()

	# Unsubscribing a selective callback stops further notifications,
	# while a global callback continues to receive the same changes.
	# ----------------------------------------------------------------------
	@classmethod
	def test_filtered_unsubscribe(cls):
		sync     = cls._sync()
		global_q = Queue()
		filtered = Queue()

		try:
			sync.subscribe(global_q.put)
			callback = sync.subscribe({121}, filtered.put)
			sync.unsubscribe(callback)

			sync.register_change(805, 121)
			sync.publish_change(sync.changes.pop(805), local=True)
			assert global_q.get(timeout=2) == frozenset({121})

			try:
				unexpected = filtered.get(timeout=0.05)
			except Empty:
				unexpected = None

			assert unexpected is None
		finally:
			sync.close()
	# Preserve the callback keyword and reject unsupported ID collections.
	# ----------------------------------------------------------------------
	@classmethod
	def test_subscription_arguments(cls):
		sync    = cls._sync()
		results = Queue()

		try:
			callback = sync.subscribe(callback=results.put)
			assert callback == results.put
			sync.register_change(807, 141)
			sync.publish_change(sync.changes.pop(807), local=True)
			assert results.get(timeout=2) == frozenset({141})

			failed = False

			try:
				sync.subscribe([141], results.put)
			except TypeError:
				failed = True

			assert failed
		finally:
			sync.close()

	# Unsubscribe excludes a callback from future dispatch.
	# ----------------------------------------------------------------------
	@classmethod
	def test_unsubscribe(cls):
		sync     = cls._sync()
		results  = Queue()
		callback = sync.subscribe(results.put)

		try:
			sync.unsubscribe(callback)
			sync.register_change(40, 81)
			sync.publish_change(sync.changes.pop(40), local=True)

			try:
				unexpected = results.get(timeout=0.1)
			except Empty:
				unexpected = None

			assert unexpected is None
		finally:
			sync.close()

	# LMDB may reuse an aborted transaction ID; old IDs must not leak.
	# ----------------------------------------------------------------------
	@classmethod
	def test_transaction_id_reuse(cls):
		sync    = cls._sync()
		results = Queue()

		try:
			sync.subscribe(results.put)
			sync.register_change(45, 1)
			sync.changes.pop(45, None)
			sync.register_change(45, 2)
			sync.publish_change(sync.changes.pop(45), local=True)
			assert results.get(timeout=2) == frozenset({2})
		finally:
			sync.close()

	# Subscriber failures are logged without interrupting later deliveries.
	# ----------------------------------------------------------------------
	@classmethod
	def test_failing_subscriber(cls):
		sync    = cls._sync()
		results = Queue()
		errors  = []

		def fail(ids):
			raise ValueError('Expected subscriber failure')

		try:
			with patch('logging.exception', side_effect=errors.append):
				sync.subscribe(fail)
				sync.subscribe(results.put)

				for txn, id in ((50, 41), (51, 42)):
					sync.register_change(txn, id)
					sync.publish_change(sync.changes.pop(txn), local=True)
					assert results.get(timeout=2) == frozenset({id})

				sync.close()

			assert errors == ['O Sync subscriber failed'] * 2
		finally:
			sync.close()

	# Concurrent writers keep independent transaction data.
	# ----------------------------------------------------------------------
	@classmethod
	def test_concurrent_transactions(cls):
		sync    = cls._sync()
		results = Queue()

		def write(txn):
			for id in range(txn * 10, txn * 10 + 5):
				sync.register_change(txn, id)

			sync.publish_change(sync.changes.pop(txn), local=True)

		try:
			sync.subscribe(results.put)

			with ThreadPoolExecutor(max_workers=4) as pool:
				list(pool.map(write, range(1, 5)))

			seen = set()

			for index in range(4):
				seen.update(results.get(timeout=2))
				if len(seen) == 20:
					break

			expected = (
				set(range(10, 15)) |
				set(range(20, 25)) |
				set(range(30, 35)) |
				set(range(40, 45))
			)
			assert seen == expected
		finally:
			sync.close()

	# A MemoryBatch uses the LMDB ID for all nested writes and commit.
	# ----------------------------------------------------------------------
	@classmethod
	def test_memory_batch_uses_lmdb_transaction_id(cls):
		state  = cls._patch_runtime()
		memory = o.services.Memory
		sync   = memory.sync
		events  = []
		changes = {}

		def register_change(txn, id):
			events.append(('change', txn, id))
			changes.setdefault(txn, []).append(id)

		memory.sync = SimpleNamespace(
			changes         = changes,
			register_change = register_change,
			publish_change  = lambda ids, local=True: events.append(('publish', ids, local)),
		)

		try:
			with memory.write() as batch:
				txn_id = batch.tx.id()
				assert batch.txn_id == txn_id
				memory.set('sync/first', 1, 101)

				with memory.write() as nested:
					assert nested is batch
					memory.set('sync/second', 2, 202)

			assert events == [
				('change', txn_id, 101),
				('change', txn_id, 202),
				('publish', [101, 202], True),
			]
		finally:
			memory.sync = sync
			cls._restore_runtime(state)

	# Aborted MemoryBatch sends cancellation with the same LMDB ID.
	# ----------------------------------------------------------------------
	@classmethod
	def test_memory_batch_abort(cls):
		state  = cls._patch_runtime()
		memory = o.services.Memory
		sync   = memory.sync
		events  = []
		changes = {}

		def register_change(txn, id):
			events.append(('change', txn, id))
			changes.setdefault(txn, []).append(id)

		memory.sync = SimpleNamespace(
			changes         = changes,
			register_change = register_change,
			publish_change  = lambda ids, local=True: events.append(('publish', ids, local)),
		)

		try:
			try:
				with memory.write() as batch:
					txn_id = batch.tx.id()
					memory.set('sync/rolled_back', 3, 303)
					raise ValueError('Rollback')
			except ValueError:
				pass

			assert events == [('change', txn_id, 303)]
			assert changes == {}
			assert memory.get('sync/rolled_back') is o.Undefined
		finally:
			memory.sync = sync
			cls._restore_runtime(state)

	# Wake a dormant worker and deliver the first committed change.
	# ----------------------------------------------------------------------
	@classmethod
	def test_wake_after_idle(cls):
		sync    = cls._sync()
		results = Queue()

		try:
			sync.subscribe(results.put)
			deadline = time.monotonic() + 2

			while not sync._sleeping and time.monotonic() < deadline:
				time.sleep(0.002)

			assert sync._sleeping
			sync.register_change(70, 71)
			sync.publish_change(sync.changes.pop(70), local=True)

			assert results.get(timeout=2) == frozenset({71})
		finally:
			sync.close()

	# Confirm commit delivery through repeated transitions to idle sleep.
	# ----------------------------------------------------------------------
	@classmethod
	def test_repeated_idle_wakeups(cls):
		sync    = cls._sync()
		results = Queue()

		sync.idle_delay = 0.005

		try:
			sync.subscribe(results.put)

			for txn in range(20):
				deadline = time.monotonic() + 2

				while not sync._sleeping and time.monotonic() < deadline:
					time.sleep(0.0005)

				assert sync._sleeping
				sync.register_change(txn, txn + 1)
				sync.publish_change(sync.changes.pop(txn), local=True)
				assert results.get(timeout=2) == frozenset({txn + 1})
		finally:
			sync.close()

	# A burst of confirmations must not lose IDs while the worker coalesces.
	# ----------------------------------------------------------------------
	@classmethod
	def test_burst_delivery(cls):
		sync    = cls._sync()
		results = []

		try:
			sync.subscribe(results.append)

			for txn in range(1000):
				sync.register_change(txn, txn + 1)
				sync.publish_change(sync.changes.pop(txn), local=True)

			sync.close()

			ids = set()

			for batch in results:
				ids.update(batch)

			assert ids == set(range(1, 1001))
		finally:
			sync.close()


	# Concurrent writers must deliver every committed owner ID exactly once
	# or in a coalesced batch, without leaking aborted transaction records.
	# ----------------------------------------------------------------------
	@classmethod
	def test_many_concurrent_commits(cls):
		sync     = cls._sync()
		received = []
		barrier  = threading.Barrier(6)

		def write(worker):
			barrier.wait(timeout=5)

			for index in range(40):
				id  = worker * 1000 + index + 1
				txn = worker * 1000 + index
				sync.register_change(txn, id)
				sync.publish_change(sync.changes.pop(txn), local=True)

		try:
			sync.subscribe(received.append)

			with ThreadPoolExecutor(max_workers=6) as pool:
				list(pool.map(write, range(6)))

			sync.close()

			observed = set()

			for batch in received:
				assert isinstance(batch, frozenset)
				observed.update(batch)

			expected = {
				worker * 1000 + index + 1
				for worker in range(6)
				for index in range(40)
			}
			assert observed == expected
			assert sync.changes == {}
			assert not sync._worker.is_alive()
		finally:
			sync.close()
	# Callbacks may change subscriptions during delivery without deadlock.
	# Only subscribers registered for the next dispatch receive it.
	# ----------------------------------------------------------------------
	@classmethod
	def test_subscriber_reentrancy(cls):
		sync    = cls._sync()
		first   = Queue()
		second  = Queue()

		def change_subscriptions(ids):
			sync.unsubscribe(change_subscriptions)
			sync.subscribe(second.put)
			first.put(ids)

		try:
			sync.subscribe(change_subscriptions)
			sync.register_change(304, 111)
			sync.publish_change(sync.changes.pop(304), local=True)
			assert first.get(timeout=2) == frozenset({111})

			sync.register_change(305, 112)
			sync.publish_change(sync.changes.pop(305), local=True)
			assert second.get(timeout=2) == frozenset({112})

			try:
				unexpected = first.get(timeout=0.1)
			except Empty:
				unexpected = None

			assert unexpected is None
		finally:
			sync.close()

	# A blocked subscriber must not hold the writer's transaction path.
	# Confirmations queued during a callback must arrive after it resumes.
	# ----------------------------------------------------------------------
	@classmethod
	def test_slow_subscriber_does_not_block_writes(cls):
		sync     = cls._sync()
		entered  = threading.Event()
		release  = threading.Event()
		received = []

		def callback(ids):
			entered.set()
			assert release.wait(timeout=5)
			received.append(ids)

		def write():
			for txn in range(400, 600):
				sync.register_change(txn, txn + 1000)
				sync.publish_change(sync.changes.pop(txn), local=True)

		try:
			sync.subscribe(callback)
			sync.register_change(399, 1399)
			sync.publish_change(sync.changes.pop(399), local=True)
			assert entered.wait(timeout=2)

			with ThreadPoolExecutor(max_workers=1) as pool:
				result = pool.submit(write)
				result.result(timeout=3)

			assert not release.is_set()
			release.set()
			sync.close()

			observed = set()

			for batch in received:
				observed.update(batch)

			assert observed == set(range(1399, 1600))
		finally:
			release.set()
			sync.close()

	# Close delivers already committed changes but discards candidates
	# belonging to transactions that never committed.
	# ----------------------------------------------------------------------
	@classmethod
	def test_close_with_uncommitted_transaction(cls):
		sync     = cls._sync()
		received = []

		try:
			sync.subscribe(received.append)
			sync.register_change(601, 1601)
			sync.publish_change(sync.changes.pop(601), local=True)
			sync.register_change(602, 1602)
			sync.close()

			observed = set()

			for batch in received:
				observed.update(batch)

			assert observed == {1601}
			assert not sync._worker.is_alive()
		finally:
			sync.close()

	# A subscriber is allowed to close its own Sync worker, without
	# joining the current thread or leaving future writes enabled.
	# ----------------------------------------------------------------------
	@classmethod
	def test_close_from_subscriber(cls):
		sync     = cls._sync()
		received = Queue()

		def callback(ids):
			sync.close()
			received.put(ids)

		try:
			sync.subscribe(callback)
			sync.register_change(603, 1603)
			sync.publish_change(sync.changes.pop(603), local=True)
			assert received.get(timeout=2) == frozenset({1603})

			sync.close()
			assert not sync._worker.is_alive()

			failed = False

			try:
				sync.register_change(604, 1604)
			except RuntimeError:
				failed = True

			assert failed
		finally:
			sync.close()

	# A real LMDB commit must be visible to subscribers running on the
	# worker thread, after the writer has finished the transaction.
	# ----------------------------------------------------------------------
	@classmethod
	def test_real_memory_commit_visibility(cls):
		state   = cls._patch_runtime()
		memory  = o.services.Memory
		original = memory.sync
		sync    = cls._sync()
		results = Queue()
		key     = 'sync/correctness/committed'

		def observe(ids):
			results.put((ids, memory.get(key)))

		try:
			memory.sync = sync
			sync.subscribe(observe)
			memory.set(key, 42, 1701)

			assert results.get(timeout=2) == (frozenset({1701}), 42)
		finally:
			memory.sync = original
			sync.close()
			cls._restore_runtime(state)

	# Close waits for queued commits but refuses future writes.
	# ----------------------------------------------------------------------
	@classmethod
	def test_close(cls):
		sync    = cls._sync()
		results = []

		sync.subscribe(results.append)
		sync.register_change(60, 61)
		sync.publish_change(sync.changes.pop(60), local=True)
		sync.close()

		assert results == [frozenset({61})]

		failed = False

		try:
			sync.register_change(61, 62)
		except RuntimeError:
			failed = True

		assert failed


if __name__ == '__main__':
	TestSync.run()
