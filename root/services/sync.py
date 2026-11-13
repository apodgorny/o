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
		with self._condition:
			callbacks = tuple(self._subscribers)

		for callback in callbacks:
			try:
				callback(ids)
			except Exception:
				logging.exception('O Sync subscriber failed')

	# Sleep without a deadline when idle; otherwise poll for committed
	# batches and fallback candidates with minimal producer interference.
	# ----------------------------------------------------------------------
	def _run(self):
		pending       = []
		last_activity = monotonic()

		while not self._stopped.is_set():
			# Recheck the queues after declaring sleep, so a simultaneous
			# commit can always wake the worker.
			# ----------------------------------------------------------
			if (
				monotonic() - last_activity >= self.idle_delay
				and not pending and self._registered.empty()
				and self._ready.empty()
			):
				self._wake.clear()
				self._sleeping = True

				if not pending and self._registered.empty() and self._ready.empty():
					self._wake.wait()

				self._sleeping = False
				self._wake.clear()
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
				ids = set()

				for batch in batches:
					ids.update(batch)

				self._update(frozenset({0}) if 0 in ids else frozenset(ids))

		# A close requested after commit must still deliver queued changes.
		# ------------------------------------------------------------------
		batches = self._drain(self._ready)

		if batches:
			ids = set()

			for batch in batches:
				ids.update(batch)

			self._update(frozenset({0}) if 0 in ids else frozenset(ids))

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
		self._wake        = threading.Event()
		self._stopped     = threading.Event()
		self._condition   = threading.Condition()
		self._subscribers = set()
		self._sleeping    = False
		self._closed      = False

		self._worker = threading.Thread(
			target = self._run,
			name   = 'o-sync',
			daemon = True,
		)
		self._worker.start()

	# Subscribe before taking the initial read snapshot. Callback receives
	# a frozenset of changed owner IDs; zero means full invalidation.
	# ----------------------------------------------------------------------
	def subscribe(self, callback):
		if not callable(callback):
			raise TypeError('Sync subscriber must be callable')

		with self._condition:
			if self._closed:
				raise RuntimeError('Sync is closed')

			self._subscribers.add(callback)

		return callback

	# Stop notifications to the given callback.
	# ----------------------------------------------------------------------
	def unsubscribe(self, callback):
		with self._condition:
			self._subscribers.discard(callback)

	# Append an ID without acquiring the worker's lock. Each LMDB write
	# transaction has one producer and a private record.
	# ----------------------------------------------------------------------
	def on_change(self, txn, id):
		if self._closed:
			raise RuntimeError('Sync is closed')

		record = self.changes.get(txn)

		if record is None:
			record = [monotonic() + self.fallback_delay, [id], True]
			self.changes[txn] = record
			self._registered.put(record)
		else:
			record[1].append(id)

		if self._sleeping:
			self._wake.set()

	# Transfer a committed record to the worker without waiting for it.
	# ----------------------------------------------------------------------
	def on_changed(self, txn):
		if self._closed:
			raise RuntimeError('Sync is closed')

		record = self.changes.pop(txn, None)

		if record is not None:
			record[2] = False
			self._ready.put(record[1])

			if self._sleeping:
				self._wake.set()

	# Drop a rolled-back candidate. A fallback already delivered is allowed.
	# ----------------------------------------------------------------------
	def on_aborted(self, txn):
		record = self.changes.pop(txn, None)

		if record is not None:
			record[2] = False

	# Flush confirmed notifications and terminate cleanly.
	# ----------------------------------------------------------------------
	def close(self):
		self._closed = True
		self._stopped.set()
		self._wake.set()

		if self._worker is not threading.current_thread():
			self._worker.join()

		with self._condition:
			self._subscribers.clear()
