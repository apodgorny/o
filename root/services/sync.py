# ==============================================================================
# SYNC SERVICE
# ==============================================================================
# Queue committed changes from memory and transport through one worker.
# ==============================================================================

import logging
import threading

from queue import SimpleQueue

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

	# Deliver each queued change separately until the process exits.
	# ----------------------------------------------------------------------
	def _run_worker_loop(self):
		while True:
			event = self._queue.get()

			ids, local = event
			ids = None if ids is None else frozenset(ids)
			self._update(ids, local=local)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Create one worker per ontology; there is no pre-commit fallback.
	# ----------------------------------------------------------------------
	def initialize(self):
		# Only the worker handles delivery.
		# --------------------------------------------------------------
		self._queue       = SimpleQueue()
		self._lock        = threading.Lock()
		self._subscribers = {}

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
		self._queue.put((ids, local))
