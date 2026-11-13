# ==============================================================================
# SYNC SERVICE
# ==============================================================================
# Keep transaction bookkeeping in the producer and notification delivery in a
# separate worker. Handoff uses SimpleQueue; the worker sleeps when idle.
# ==============================================================================

import logging
import threading

from queue import Empty, SimpleQueue
from time  import monotonic

import o


class Sync(o.Service):

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Drain the queue at its current size. New arrivals wait for the next
	# cycle so that the producer can always make progress.
	# ----------------------------------------------------------------------
	def _drain(self, queue):
		items = []

		for index in range(queue.qsize()):
			try:
				items.append(queue.get_nowait())
			except Empty:
				break

		return items

	# Notify subscribers after coalescing all available committed batches.
	# ----------------------------------------------------------------------
	def _update(self, ids):
		with self._lock:
			callbacks = tuple(self._subscribers.items())

		full = ids is None

		for callback, watched in callbacks:
			matching = ids if full or watched is None else ids & watched

			if full or matching:
				try:
					callback(matching)
				except Exception:
					logging.exception('O Sync subscriber failed')

	# Coalesce local or remote invalidations; do not republish incoming events.
	# ----------------------------------------------------------------------
	def _deliver(self, batches, remote=False):
		full = any(batch is None or None in batch for batch in batches)
		ids  = None if full else frozenset(id for batch in batches for id in batch)

		if remote:
			o.services.Cache.invalidate(ids)
		elif self._transport is not None and o.services.Memory.path == self._transport.path:
			self._transport.send(ids)

		self._update(ids)

	# Sleep without a deadline when idle; otherwise poll for committed
	# batches and fallback candidates with minimal producer interference.
	# ----------------------------------------------------------------------
	def _run(self):
		pending       = []
		last_activity = monotonic()

		while not self._closed:
			# Recheck the queues after declaring sleep, so a simultaneous
			# commit can always wake the worker.
			# ----------------------------------------------------------
			if (
				monotonic() - last_activity >= self.idle_delay
				and not pending and self._registered.empty()
				and self._ready.empty() and self._remote.empty()
			):
				self._wake.clear()
				self._sleeping = True

				if not pending and self._registered.empty() and self._ready.empty() and self._remote.empty():
					self._wake.wait()

				self._sleeping = False
			else:
				self._wake.wait(self.batch_delay)

			self._wake.clear()

			# The worker owns the list of pending fallback records. Records
			# are uniquely allocated, so reused LMDB txn IDs cannot collide.
			# ----------------------------------------------------------
			for record in self._drain(self._registered):
				if record[2]:
					pending.append(record)

			batches = self._drain(self._ready)
			remote  = self._drain(self._remote)
			now     = monotonic()
			active  = []

			for record in pending:
				if record[2]:
					if now >= record[0]:
						batches.append(tuple(record[1]))
						record[0] = now + self.fallback_delay

					active.append(record)

			pending = active

			if batches:
				last_activity = now
				self._deliver(batches)

			if remote:
				last_activity = now
				self._deliver(remote, remote=True)

		# A close requested after commit must still deliver queued changes.
		# ------------------------------------------------------------------
		batches = self._drain(self._ready)
		remote  = self._drain(self._remote)

		if batches:
			self._deliver(batches)

		if remote:
			self._deliver(remote, remote=True)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Create one worker per ontology. Default delivery poll is 1 ms,
	# fallback is 1 second, and the worker sleeps after 20 ms of quiet.
	# ----------------------------------------------------------------------
	def initialize(self, batch_delay=0.001, fallback_delay=1.0, idle_delay=0.02):
		if batch_delay <= 0 or fallback_delay <= 0 or idle_delay <= 0:
			raise ValueError('Sync delays must be positive')

		self.batch_delay    = batch_delay
		self.fallback_delay = fallback_delay
		self.idle_delay     = idle_delay

		# The producer exclusively owns changes; the worker receives
		# independently allocated records and completed ID lists.
		# --------------------------------------------------------------
		self.changes      = {}
		self._registered  = SimpleQueue()
		self._ready       = SimpleQueue()
		self._remote      = SimpleQueue()
		self._transport   = None
		self._wake        = threading.Event()
		self._lock        = threading.Lock()
		self._subscribers = {}
		self._sleeping    = False
		self._closed      = False

		self._worker = threading.Thread(
			target = self._run,
			name   = 'o-sync',
			daemon = True,
		)
		self._worker.start()

	# Subscribe globally or to a set of owner IDs, before the initial read.
	# Callback receives matching frozenset IDs, or None for a full refresh.
	# Accept subscribe(callback) or subscribe({id, ...}, callback).
	# ----------------------------------------------------------------------
	def subscribe(self, ids=None, callback=None):
		if callback is None:
			callback = ids
			ids      = None

		if not callable(callback):
			raise TypeError('Sync subscriber must be callable')

		if ids is not None:
			if not isinstance(ids, (set, frozenset)):
				raise TypeError('Sync subscription IDs must be a set')

			ids = frozenset(ids)

		with self._lock:
			if self._closed:
				raise RuntimeError('Sync is closed')

			self._subscribers[callback] = ids

		return callback

	# Connect a host-local relay without changing the subscriber API.
	# ----------------------------------------------------------------------
	def attach_transport(self, transport):
		self._transport = transport

	# Enqueue remote owner IDs, or None for full invalidation.
	# ----------------------------------------------------------------------
	def receive(self, ids):
		if self._closed:
			raise RuntimeError('Sync is closed')

		if ids is not None:
			if not isinstance(ids, (set, frozenset)):
				raise TypeError('Sync invalidations must be a set or None')

			if not ids or any(type(id) is not int or id <= 0 for id in ids):
				raise ValueError('Sync invalidations must contain positive integer IDs')

			ids = frozenset(ids)

		self._remote.put(ids)
		self._wake.set()

	# Stop notifications to the given callback.
	# ----------------------------------------------------------------------
	def unsubscribe(self, callback):
		with self._lock:
			self._subscribers.pop(callback, None)

	# Append an ID without acquiring the worker's lock. Each LMDB write
	# transaction has one producer and a private record.
	# ----------------------------------------------------------------------
	def register_change(self, txn, id):
		if self._closed:
			raise RuntimeError('Sync is closed')

		record = self.changes.get(txn)

		if record is None:
			record = [monotonic() + self.fallback_delay, [id], True]
			self.changes[txn] = record
			self._registered.put(record)

			if self._sleeping:
				self._wake.set()
		else:
			record[1].append(id)

	# Transfer a committed record to the worker without waiting for it.
	# ----------------------------------------------------------------------
	def register_change_commit(self, txn):
		if self._closed:
			raise RuntimeError('Sync is closed')

		record = self.changes.pop(txn, None)

		if record is not None:
			record[2] = False
			self._ready.put(record[1])

	# Drop a rolled-back candidate. A fallback already delivered is allowed.
	# ----------------------------------------------------------------------
	def register_abort(self, txn):
		record = self.changes.pop(txn, None)

		if record is not None:
			record[2] = False

	# Flush confirmed notifications and terminate cleanly.
	# ----------------------------------------------------------------------
	def close(self):
		if self._transport is not None:
			self._transport.close()

		self._closed = True
		self._wake.set()

		if self._worker is not threading.current_thread():
			self._worker.join()

		with self._lock:
			self._subscribers.clear()
