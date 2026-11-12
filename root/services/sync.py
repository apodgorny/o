# ==============================================================================
# SYNC SERVICE
# ==============================================================================
# Deliver local ontology invalidations asynchronously. Keep candidate changes
# until commit or rollback, with periodic fallback for missing confirmations.
# ==============================================================================

import logging
import threading

from collections import defaultdict, deque
from time        import monotonic

import o


class Sync(o.Service):

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Start one worker for commits and transaction fallback deadlines.
	# The caller holds the condition lock.
	# ----------------------------------------------------------------------
	def _start_worker(self):
		if self._worker is None:
			worker = threading.Thread(
				target = self._run,
				name   = 'o-sync',
				daemon = True,
			)
			worker.start()
			self._worker = worker

	# Schedule a new fallback, identifying its generation separately from
	# LMDB's transaction ID, which may be reused after a rollback.
	# The caller holds the condition lock.
	# ----------------------------------------------------------------------
	def _schedule(self, txn, deadline):
		self._generation += 1
		self._scheduled[txn] = self._generation
		self._deadlines.append((deadline, self._generation, txn))

	# Notify subscribers without blocking the write transaction.
	# ----------------------------------------------------------------------
	def _update(self, ids):
		with self._condition:
			callbacks = tuple(self._subscribers)

		for callback in callbacks:
			try:
				callback(ids)
			except Exception:
				logging.exception('O Sync subscriber failed')

	# Wake for confirmed changes or speculative fallback deadlines.
	# Deduplication and subscriber callbacks run outside the writer's lock.
	# ----------------------------------------------------------------------
	def _run(self):
		running = True

		while running:
			batches = ()

			with self._condition:
				now = monotonic()

				while self._deadlines and self._deadlines[0][0] <= now:
					_deadline, generation, txn = self._deadlines.popleft()

					if self._scheduled.get(txn) == generation:
						self._ready.append(tuple(self.changes[txn]))
						self._schedule(txn, now + self.fallback_delay)

				if self._ready:
					batches = tuple(self._ready)
					self._ready.clear()
				elif self._closed:
					running = False
				else:
					timeout = None

					if self._deadlines:
						timeout = max(0.0, self._deadlines[0][0] - monotonic())

					self._condition.wait(timeout)

			if batches:
				ids = set()

				for batch in batches:
					ids.update(batch)

				self._update(frozenset({0}) if 0 in ids else frozenset(ids))

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Initialize independently for each ontology; default fallback is 1 second.
	# ----------------------------------------------------------------------
	def initialize(self, fallback_delay=1.0):
		if fallback_delay <= 0:
			raise ValueError('fallback_delay must be positive')

		self.fallback_delay = fallback_delay

		self.changes        = defaultdict(list)
		self._deadlines     = deque()
		self._scheduled     = {}
		self._generation    = 0
		self._ready         = deque()
		self._subscribers   = set()
		self._condition     = threading.Condition()
		self._worker        = None
		self._closed        = False

	# Register a subscriber; callbacks receive immutable sets of owner IDs
	# on the worker thread. Return the callback as its subscription token.
	# ----------------------------------------------------------------------
	def subscribe(self, callback):
		if not callable(callback):
			raise TypeError('Sync subscriber must be callable')

		with self._condition:
			if self._closed:
				raise RuntimeError('Sync is closed')

			self._subscribers.add(callback)

		return callback

	# Remove a subscriber without disturbing pending changes.
	# ----------------------------------------------------------------------
	def unsubscribe(self, callback):
		with self._condition:
			self._subscribers.discard(callback)

	# Record a candidate owner ID; LMDB supplies txn once per write batch.
	# ----------------------------------------------------------------------
	def on_change(self, txn, id):
		with self._condition:
			if self._closed:
				raise RuntimeError('Sync is closed')

			first = txn not in self.changes
			self.changes[txn].append(id)

			if first:
				self._schedule(txn, monotonic() + self.fallback_delay)
				self._start_worker()
				self._condition.notify()

	# Publish committed changes immediately; keep any earlier fallback as
	# a harmless duplicate rather than risking a missed late write.
	# ----------------------------------------------------------------------
	def on_changed(self, txn):
		with self._condition:
			if self._closed:
				raise RuntimeError('Sync is closed')

			ids = self.changes.pop(txn, None)
			self._scheduled.pop(txn, None)

			if ids:
				self._ready.append(ids)
				self._start_worker()
				self._condition.notify()

	# Cancel candidate changes on rollback; an already-delivered speculative
	# invalidation is harmless.
	# ----------------------------------------------------------------------
	def on_aborted(self, txn):
		with self._condition:
			self.changes.pop(txn, None)
			self._scheduled.pop(txn, None)
			self._condition.notify()

	# Deliver queued commits and stop the worker without waiting for timers.
	# ----------------------------------------------------------------------
	def close(self):
		with self._condition:
			self._closed = True
			self.changes.clear()
			self._deadlines.clear()
			self._scheduled.clear()
			self._condition.notify_all()
			worker = self._worker

		if worker is not None and worker is not threading.current_thread():
			worker.join()

		with self._condition:
			self._subscribers.clear()
