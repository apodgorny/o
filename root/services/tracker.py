# ==============================================================================
# TRACKER SERVICE
# ==============================================================================
# Observe persistent ontology reads and writes within caller-owned scopes.
# Install only the interception paths required by the active tracking modes.
# ==============================================================================

import asyncio
import threading
import weakref

from contextlib import contextmanager
from types import DynamicClassAttribute

import o


UNDEFINED = o.Undefined


class Tracker(o.Service):
	_lock         = threading.RLock()
	_thread       = threading.local()
	_task_scopes  = weakref.WeakKeyDictionary()
	_active_count = 0
	_read_count   = 0
	_write_count  = 0
	_saved_reads  = {}
	_saved_writes = {}

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Select the current asynchronous task, if one is running.
	# ----------------------------------------------------------------------
	def _current_task(self):
		try:
			task = asyncio.current_task()
		except RuntimeError:
			task = None

		return task

	# Avoid asynchronous task lookup on ordinary synchronous reads.
	# ----------------------------------------------------------------------
	def _scopes(self, create=True):
		thread = self._thread

		if create:
			task = self._current_task()
		elif getattr(thread, 'async_count', 0):
			task = asyncio.current_task()
		else:
			task = None

		if task is None:
			scopes = getattr(thread, 'scopes', None)
			if scopes is None:
				scopes = []
				if create:
					thread.scopes = scopes
		else:
			scopes = self._task_scopes.get(task)
			if scopes is None:
				scopes = []
				if create:
					self._task_scopes[task] = scopes
					thread.async_count = getattr(thread, 'async_count', 0) + 1

		return scopes

	# Append owner identities to each matching scope in access order.
	# ----------------------------------------------------------------------
	def _record(self, operation, instance):
		for mode, reads, writes in self._scopes(False):
			if operation == 'r' and 'r' in mode:
				reads.append(instance.id)
			elif operation == 'w' and 'w' in mode:
				writes.append(instance.id)

	# Read a cached field or resolve it through the original cache-miss path.
	# ----------------------------------------------------------------------
	def _read_field(self, instance, name):
		self._record('r', instance)

		if name in instance.__dict__:
			value = instance.__dict__[name]
		else:
			value = instance.__getattr__(name)

		return value

	# Read a collection index without changing its storage semantics.
	# ----------------------------------------------------------------------
	def _read_slot(self, instance, name):
		if name not in instance.__dict__:
			raise AttributeError(name)

		self._record('r', instance)
		value = instance.__dict__[name]

		return value

	# Keep a data descriptor transparent to ordinary field assignments.
	# ----------------------------------------------------------------------
	def _write_slot(self, instance, name, value):
		instance.__dict__[name] = value

	# Install a read descriptor, preserving the original class attribute.
	# ----------------------------------------------------------------------
	def _install_property(self, cls, name, is_field):
		key = (cls, name)

		if key not in self._saved_reads:
			self._saved_reads[key] = cls.__dict__.get(name, UNDEFINED)

			if is_field:
				def get(instance):
					return self._read_field(instance, name)
			else:
				def get(instance):
					return self._read_slot(instance, name)

			def set(instance, value):
				self._write_slot(instance, name, value)

			def delete(instance):
				instance.__dict__.pop(name, None)

			type.__setattr__(cls, name, DynamicClassAttribute(get, set, delete))

	# Instrument the persisted fields declared by one ontology class.
	# ----------------------------------------------------------------------
	def _install_fields(self, cls):
		for name, _ in cls._.items():
			self._install_property(cls, name, True)

	# Include fields published after read tracking has already begun.
	# ----------------------------------------------------------------------
	def _install_field_publication(self):
		meta     = o.TMeta
		name     = '__publish_field__'
		original = meta.__dict__[name]
		self._saved_reads[(meta, name)] = original

		def publish(cls, field_name, field):
			original(cls, field_name, field)
			with self._lock:
				if self._read_count > 0:
					self._install_property(cls, field_name, True)

		type.__setattr__(meta, name, publish)

	# Observe successful field assignments after normal persistence completes.
	# ----------------------------------------------------------------------
	def _install_field_writer(self):
		cls      = o.T
		name     = '__setattr__'
		original = cls.__dict__[name]
		self._saved_writes[(cls, name)] = original

		def assign(instance, field_name, value):
			result = original(instance, field_name, value)
			self._record('w', instance)

			return result

		type.__setattr__(cls, name, assign)

	# Observe successful field deletion even for uncached fields.
	# ----------------------------------------------------------------------
	def _install_field_deletion(self):
		cls      = o.T
		name     = '__delattr__'
		original = cls.__dict__[name]
		self._saved_writes[(cls, name)] = original

		def delete(instance, field_name):
			result = original(instance, field_name)
			self._record('w', instance)

			return result

		type.__setattr__(cls, name, delete)

	# Observe collection changes at their shared persistence boundary.
	# ----------------------------------------------------------------------
	def _install_collection_writer(self, cls):
		name     = '__save_items__'
		original = cls.__dict__[name]
		self._saved_writes[(cls, name)] = original

		def save(instance, items):
			previous = instance.__dict__.get('__items__', UNDEFINED)
			result   = original(instance, items)

			if previous is UNDEFINED or previous != instance.__dict__['__items__']:
				self._record('w', instance)

			return result

		type.__setattr__(cls, name, save)

	# Capture dictionary membership without observing the key index twice.
	# ----------------------------------------------------------------------
	def _install_dict_membership(self):
		cls      = o.Dict
		name     = '__contains__'
		original = cls.__dict__[name]
		self._saved_reads[(cls, name)] = original

		def contains(instance, key):
			result = original(instance, key)
			self._record('r', instance)

			return result

		type.__setattr__(cls, name, contains)

	# Add read-side descriptors only while at least one scope needs reads.
	# ----------------------------------------------------------------------
	def _install_reads(self):
		self._install_field_publication()

		for entity_id, entity in tuple(o.services.Cache.entities.items()):
			if isinstance(entity_id, int) and isinstance(entity, type):
				if issubclass(entity, o.T):
					self._install_fields(entity)

		for cls in (o.List, o.Dict):
			self._install_property(cls, '__items__', False)

		self._install_dict_membership()

	# Add write-side wrappers without affecting the read-only hot path.
	# ----------------------------------------------------------------------
	def _install_writes(self):
		self._install_field_writer()
		self._install_field_deletion()

		for cls in (o.List, o.Dict):
			self._install_collection_writer(cls)

	# Restore only one direction of instrumentation in reverse order.
	# ----------------------------------------------------------------------
	def _uninstall(self, saved):
		for (cls, name), original in reversed(tuple(saved.items())):
			if original is UNDEFINED:
				type.__delattr__(cls, name)
			else:
				type.__setattr__(cls, name, original)

		saved.clear()

	# Activate the union of modes requested by all currently active scopes.
	# ----------------------------------------------------------------------
	def _enter(self, scope):
		mode = scope[0]

		with self._lock:
			need_reads  = 'r' in mode and self._read_count == 0
			need_writes = 'w' in mode and self._write_count == 0

			try:
				if need_reads:
					self._install_reads()
				if need_writes:
					self._install_writes()
			except BaseException:
				if need_writes:
					self._uninstall(self._saved_writes)
				if need_reads:
					self._uninstall(self._saved_reads)
				raise

			self._scopes().append(scope)
			self._active_count += 1

			if 'r' in mode:
				self._read_count += 1
			if 'w' in mode:
				self._write_count += 1

	# Release only the interceptors no longer needed by any active scope.
	# ----------------------------------------------------------------------
	def _exit(self, scope):
		mode = scope[0]

		with self._lock:
			scopes = self._scopes()
			assert scopes[-1] is scope
			scopes.pop()
			self._active_count -= 1

			if 'r' in mode:
				self._read_count -= 1
				if self._read_count == 0:
					self._uninstall(self._saved_reads)

			if 'w' in mode:
				self._write_count -= 1
				if self._write_count == 0:
					self._uninstall(self._saved_writes)

			if not scopes:
				task = self._current_task()
				if task is not None:
					del self._task_scopes[task]
					self._thread.async_count -= 1

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Record reads ('r'), writes ('w') or both ('rw') into caller-owned lists.
	# Use the current ontology's Tracker: o.services.Tracker.track(...).
	# Separate thread/async task scopes can overlap without sharing traces.
	# ----------------------------------------------------------------------
	@contextmanager
	def track(self, mode, reads=None, writes=None):
		if mode not in ('r', 'w', 'rw'):
			raise ValueError(f'Invalid tracking mode: {mode!r}')

		if mode == 'w' and writes is None:
			writes = reads
			reads  = None

		if 'r' in mode and not isinstance(reads, list):
			raise TypeError('Read tracking requires a list')

		if 'w' in mode and not isinstance(writes, list):
			raise TypeError('Write tracking requires a list')

		scope = (mode, reads, writes)
		self._enter(scope)

		try:
			yield
		finally:
			self._exit(scope)