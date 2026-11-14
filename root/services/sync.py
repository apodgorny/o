# ==============================================================================
# SYNC SERVICE
# ==============================================================================
# Queue committed changes from memory and transport through one worker.
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

	# One delivery point for local and external invalidations.
	# ----------------------------------------------------------------------
	def _update(self, ids, local=True):
		if not local:
			o.services.Cache.invalidate(ids)

		with self._lock:
			callbacks = tuple(self._subscribers.items())

		full = ids is None

		for callback, (watched, local_only) in callbacks:
			if not local and local_only:
				continue

			matching = ids if full or watched is None else ids & watched

			if full or matching:
				try:
					callback(matching)
				except Exception:
					logging.exception('O Sync subscriber failed')

	# Deliver each queued change separately, in publication order.
	# ----------------------------------------------------------------------
	def _run_worker_loop(self):
		last_activity = monotonic()

		while not self._closed or not self._queue.empty():
			if not self._closed and monotonic() - last_activity >= self.idle_delay and self._queue.empty():
				self._wake.clear()
				self._sleeping = True

				if self._queue.empty() and not self._closed:
					self._wake.wait()

				self._sleeping = False
			elif not self._closed:
				self._wake.wait(self.batch_delay)

			self._wake.clear()

			while not self._queue.empty():
				try:
					ids, local = self._queue.get_nowait()
				except Empty:
					break

				last_activity = monotonic()
				ids = None if ids is None or 0 in ids else frozenset(ids)
				self._update(ids, local=local)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Create one worker per ontology; there is no pre-commit fallback.
	# ----------------------------------------------------------------------
	def initialize(self, batch_delay=0.001, idle_delay=0.02):
		if batch_delay <= 0 or idle_delay <= 0:
			raise ValueError('Sync delays must be positive')

		self.batch_delay = batch_delay
		self.idle_delay  = idle_delay

		# Only the worker handles delivery.
		# --------------------------------------------------------------
		self._queue       = SimpleQueue()
		self._wake        = threading.Event()
		self._lock        = threading.Lock()
		self._subscribers = {}
		self._sleeping    = False
		self._closed      = False

		self._worker = threading.Thread(
			target = self._run_worker_loop,
			name   = 'o-sync',
			daemon = True,
		)
		self._worker.start()

	# Subscribe to all changes or only those originating in this process.
	# Accept subscribe(callback) or subscribe({id, ...}, callback).
	# ----------------------------------------------------------------------
	def subscribe(self, ids=None, callback=None, local_only=False):
		if callback is None:
			callback = ids
			ids      = None

		if not callable(callback):
			raise TypeError('Sync subscriber must be callable')

		if type(local_only) is not bool:
			raise TypeError('local_only must be bool')

		if ids is not None:
			if not isinstance(ids, (set, frozenset)):
				raise TypeError('Sync subscription IDs must be a set')

			ids = frozenset(ids)

		with self._lock:
			if self._closed:
				raise RuntimeError('Sync is closed')

			self._subscribers[callback] = (ids, local_only)

		return callback

	# Stop notifications to the given callback.
	# ----------------------------------------------------------------------
	def unsubscribe(self, callback):
		with self._lock:
			self._subscribers.pop(callback, None)

	# Queue changes immediately; the worker dispatches each event.
	# ----------------------------------------------------------------------
	def publish_change(self, ids, local=True):
		if self._closed:
			raise RuntimeError('Sync is closed')

		if not local and ids is not None:
			if not isinstance(ids, (set, frozenset)):
				raise TypeError('Sync invalidations must be a set or None')

			if not ids or any(type(id) is not int or id <= 0 for id in ids):
				raise ValueError('Sync invalidations must contain positive integer IDs')

			ids = frozenset(ids)

		self._queue.put((ids, local))

		if self._sleeping:
			self._wake.set()


	# Flush confirmed notifications and terminate cleanly.
	# ----------------------------------------------------------------------
	def close(self):
		self._closed = True
		self._wake.set()

		if self._worker is not threading.current_thread():
			self._worker.join()

		with self._lock:
			self._subscribers.clear()
