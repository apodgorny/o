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
