# ==============================================================================
# TEST SYNC
# ==============================================================================
# Verify local delivery, fallback, isolation, and LMDB transaction integration.
# ==============================================================================

import threading
import time

from concurrent.futures import ThreadPoolExecutor
from queue              import Empty, Queue
from types              import SimpleNamespace

import o


class TestSync(o.Tester):

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Give each test its own service singleton with a short fallback deadline.
	# ----------------------------------------------------------------------
	@classmethod
	def _sync(cls, fallback_delay=0.2):
		service_type = type('SyncTest', (type(o.services.Sync),), {})
		service      = service_type()
		service.initialize(fallback_delay=fallback_delay)

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
			sync.on_change(7, 11)
			sync.on_change(7, 11)
			sync.on_change(7, 22)
			sync.on_changed(7)

			ids, thread_id = results.get(timeout=2)
			assert ids == frozenset({11, 22})
			assert thread_id != threading.get_ident()
			assert sync.changes == {}
		finally:
			sync.close()

	# An open transaction gets a fallback, then a final commit notification.
	# ----------------------------------------------------------------------
	@classmethod
	def test_fallback_then_commit(cls):
		sync    = cls._sync(0.03)
		results = Queue()

		try:
			sync.subscribe(results.put)
			sync.on_change(10, 19)
			assert results.get(timeout=2) == frozenset({19})
			assert sync.changes[10][1] == [19]

			sync.on_change(10, 23)
			sync.on_changed(10)
			assert results.get(timeout=2) == frozenset({19, 23})
			assert sync.changes == {}
		finally:
			sync.close()

	# Rollback cancels the deadline and does not publish a commit.
	# ----------------------------------------------------------------------
	@classmethod
	def test_abort(cls):
		sync    = cls._sync(0.1)
		results = Queue()

		try:
			sync.subscribe(results.put)
			sync.on_change(20, 17)
			sync.on_aborted(20)
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
			sync.on_change(30, 100)
			sync.on_change(30, 0)
			sync.on_changed(30)
			assert results.get(timeout=2) == frozenset({0})
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
			sync.on_change(40, 81)
			sync.on_changed(40)

			try:
				unexpected = results.get(timeout=0.1)
			except Empty:
				unexpected = None

			assert unexpected is None
		finally:
			sync.close()

	# LMDB may reuse an aborted transaction ID; stale deadlines stay cancelled.
	# ----------------------------------------------------------------------
	@classmethod
	def test_transaction_id_reuse(cls):
		sync    = cls._sync(0.12)
		results = Queue()

		try:
			sync.subscribe(results.put)
			sync.on_change(45, 1)
			sync.on_aborted(45)
			sync.on_change(45, 2)
			sync.on_changed(45)
			assert results.get(timeout=2) == frozenset({2})
		finally:
			sync.close()

	# Subscriber failures do not block other subscribers or later commits.
	# ----------------------------------------------------------------------
	@classmethod
	def test_failing_subscriber(cls):
		sync    = cls._sync()
		results = Queue()

		def fail(ids):
			raise ValueError('Expected subscriber failure')

		try:
			sync.subscribe(fail)
			sync.subscribe(results.put)
			sync.on_change(50, 41)
			sync.on_changed(50)
			assert results.get(timeout=2) == frozenset({41})
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
				sync.on_change(txn, id)

			sync.on_changed(txn)

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
		events = []

		memory.sync = SimpleNamespace(
			on_change  = lambda txn, id: events.append(('change', txn, id)),
			on_changed = lambda txn: events.append(('commit', txn)),
			on_aborted = lambda txn: events.append(('abort', txn)),
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
				('commit', txn_id),
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
		events = []

		memory.sync = SimpleNamespace(
			on_change  = lambda txn, id: events.append(('change', txn, id)),
			on_changed = lambda txn: events.append(('commit', txn)),
			on_aborted = lambda txn: events.append(('abort', txn)),
		)

		try:
			try:
				with memory.write() as batch:
					txn_id = batch.tx.id()
					memory.set('sync/rolled_back', 3, 303)
					raise ValueError('Rollback')
			except ValueError:
				pass

			assert events == [('change', txn_id, 303), ('abort', txn_id)]
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
			sync.on_change(70, 71)
			sync.on_changed(70)

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
				sync.on_change(txn, txn + 1)
				sync.on_changed(txn)
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
				sync.on_change(txn, txn + 1)
				sync.on_changed(txn)

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
				sync.on_change(txn, id)
				sync.on_changed(txn)

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

	# Repeated fallback includes newly changed IDs while keeping the
	# transaction open, and a later commit publishes its complete state.
	# ----------------------------------------------------------------------
	@classmethod
	def test_multiple_fallbacks_before_commit(cls):
		sync    = cls._sync(0.04)
		results = Queue()

		try:
			sync.subscribe(results.put)
			sync.on_change(301, 81)
			assert results.get(timeout=2) == frozenset({81})

			sync.on_change(301, 82)
			assert results.get(timeout=2) == frozenset({81, 82})

			sync.on_changed(301)
			assert results.get(timeout=2) == frozenset({81, 82})
			assert sync.changes == {}
		finally:
			sync.close()

	# Aborting after one speculative notification prevents subsequent
	# fallback delivery from the abandoned transaction.
	# ----------------------------------------------------------------------
	@classmethod
	def test_abort_after_fallback(cls):
		sync    = cls._sync(0.04)
		results = Queue()

		try:
			sync.subscribe(results.put)
			sync.on_change(302, 91)
			assert results.get(timeout=2) == frozenset({91})

			sync.on_aborted(302)
			assert sync.changes == {}

			try:
				unexpected = results.get(timeout=0.12)
			except Empty:
				unexpected = None

			assert unexpected is None
		finally:
			sync.close()

	# An LMDB ID reused after speculative invalidation must not revive
	# the previous transaction or publish its old owner IDs.
	# ----------------------------------------------------------------------
	@classmethod
	def test_reuse_after_speculative_fallback(cls):
		sync    = cls._sync(0.04)
		results = Queue()

		try:
			sync.subscribe(results.put)
			sync.on_change(303, 101)
			assert results.get(timeout=2) == frozenset({101})
			sync.on_aborted(303)

			sync.on_change(303, 102)
			sync.on_changed(303)
			assert results.get(timeout=2) == frozenset({102})

			try:
				unexpected = results.get(timeout=0.12)
			except Empty:
				unexpected = None

			assert unexpected is None
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
			sync.on_change(304, 111)
			sync.on_changed(304)
			assert first.get(timeout=2) == frozenset({111})

			sync.on_change(305, 112)
			sync.on_changed(305)
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
				sync.on_change(txn, txn + 1000)
				sync.on_changed(txn)

		try:
			sync.subscribe(callback)
			sync.on_change(399, 1399)
			sync.on_changed(399)
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
			sync.on_change(601, 1601)
			sync.on_changed(601)
			sync.on_change(602, 1602)
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
			sync.on_change(603, 1603)
			sync.on_changed(603)
			assert received.get(timeout=2) == frozenset({1603})

			sync.close()
			assert not sync._worker.is_alive()

			failed = False

			try:
				sync.on_change(604, 1604)
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
		sync.on_change(60, 61)
		sync.on_changed(60)
		sync.close()

		assert results == [frozenset({61})]

		failed = False

		try:
			sync.on_change(61, 62)
		except RuntimeError:
			failed = True

		assert failed


if __name__ == '__main__':
	TestSync.run()
