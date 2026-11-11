# ==============================================================================
# TRACKER SERVICE
# ==============================================================================
# Observe ontology reads and writes only while a tracking scope is active.
# Install temporary Python descriptors without modifying the tracked classes.
# ==============================================================================

import asyncio
import threading
import weakref

from contextlib import contextmanager
from types import DynamicClassAttribute

import o


UNDEFINED = o.Undefined


class Tracker(o.Service):
	_lock          = threading.RLock()
	_thread        = threading.local()
	_task_scopes   = weakref.WeakKeyDictionary()
	_active_count  = 0
	_saved_attrs   = {}

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

	# Resolve scopes belonging to the current task or ordinary thread.
	# ----------------------------------------------------------------------
	def _scopes(self, create=True):
		task = self._current_task()

		if task is None:
			scopes = getattr(self._thread, 'scopes', None)
			if scopes is None:
				scopes = []
				if create:
					self._thread.scopes = scopes
		else:
			scopes = self._task_scopes.get(task)
			if scopes is None:
				scopes = []
				if create:
					self._task_scopes[task] = scopes

		return scopes

	# Append owner identities in access order to every matching active scope.
	# ----------------------------------------------------------------------
	def _record(self, operation, instance):
		for mode, reads, writes in self._scopes(False):
			if operation == 'r' and 'r' in mode:
				reads.append(instance.id)
			elif operation == 'w' and 'w' in mode:
				writes.append(instance.id)

	# Read a cached field without losing observations on the first cache miss.
	# ----------------------------------------------------------------------
	def _read_field(self, instance, name):
		self._record('r', instance)

		if name in instance.__dict__:
			value = instance.__dict__[name]
		else:
			previous             = getattr(self._thread, 'loading', None)
			self._thread.loading = (instance, name)

			try:
				value = instance.__getattr__(name)
			finally:
				self._thread.loading = previous

		return value

	# Cache the visible field value and distinguish hydration from assignment.
	# ----------------------------------------------------------------------
	def _write_field(self, instance, name, value):
		instance.__dict__[name] = value

		if getattr(self._thread, 'loading', None) != (instance, name):
			self._record('w', instance)

	# Remove a cached field without altering its persisted deletion behavior.
	# ----------------------------------------------------------------------
	def _delete_field(self, instance, name):
		instance.__dict__.pop(name, None)

	# Read an internal collection slot, preserving its normal storage semantics.
	# ----------------------------------------------------------------------
	def _read_slot(self, instance, name):
		if name not in instance.__dict__:
			raise AttributeError(name)

		self._record('r', instance)
		value = instance.__dict__[name]

		return value

	# Update an internal slot without treating reconstruction as a mutation.
	# ----------------------------------------------------------------------
	def _write_slot(self, instance, name, value):
		instance.__dict__[name] = value

	# Install one property while remembering whether the class owned its name.
	# ----------------------------------------------------------------------
	def _install_property(self, cls, name, is_field):
		key = (cls, name)

		if key not in self._saved_attrs:
			self._saved_attrs[key] = cls.__dict__.get(name, UNDEFINED)

			if is_field:
				def get(instance):
					return self._read_field(instance, name)

				def set(instance, value):
					self._write_field(instance, name, value)

				def delete(instance):
					self._delete_field(instance, name)
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
		for name, field in cls._.items():
			self._install_property(cls, name, True)

	# Preserve future field publication, including classes born inside a scope.
	# ----------------------------------------------------------------------
	def _install_field_publication(self):
		meta     = o.TMeta
		name     = '__publish_field__'
		original = meta.__dict__[name]
		self._saved_attrs[(meta, name)] = original

		def publish(cls, field_name, field):
			original(cls, field_name, field)
			with self._lock:
				if self._active_count > 0:
					self._install_property(cls, field_name, True)

		type.__setattr__(meta, name, publish)

	# Count successful field deletion even when its value was never cached.
	# ----------------------------------------------------------------------
	def _install_field_deletion(self):
		cls      = o.T
		name     = '__delattr__'
		original = cls.__dict__[name]
		self._saved_attrs[(cls, name)] = original

		def delete(instance, field_name):
			result = original(instance, field_name)
			self._record('w', instance)

			return result

		type.__setattr__(cls, name, delete)

	# Record successful changes through the shared collection save operation.
	# ----------------------------------------------------------------------
	def _install_collection_writer(self, cls):
		name     = '__save_items__'
		original = cls.__dict__[name]
		self._saved_attrs[(cls, name)] = original

		def save(instance, items):
			previous = instance.__dict__.get('__items__', UNDEFINED)
			result   = original(instance, items)

			if previous is UNDEFINED or previous != instance.__dict__['__items__']:
				self._record('w', instance)

			return result

		type.__setattr__(cls, name, save)

	# Patch class dictionaries once, leaving the untracked fast path intact.
	# ----------------------------------------------------------------------
	def _install(self):
		self._install_field_publication()
		self._install_field_deletion()

		for entity_id, entity in tuple(o.services.Cache.entities.items()):
			if isinstance(entity_id, int) and isinstance(entity, type):
				if issubclass(entity, o.T):
					self._install_fields(entity)

		for cls in (o.List, o.Dict):
			self._install_property(cls, '__items__', False)
			self._install_collection_writer(cls)

		self._install_property(o.Dict, '__key_ids__', False)

	# Restore the original class dictionaries, including newly created classes.
	# ----------------------------------------------------------------------
	def _uninstall(self):
		for (cls, name), original in reversed(tuple(self._saved_attrs.items())):
			if original is UNDEFINED:
				type.__delattr__(cls, name)
			else:
				type.__setattr__(cls, name, original)

		self._saved_attrs.clear()

	# Enter a tracking scope while patching shared classes only once.
	# ----------------------------------------------------------------------
	def _enter(self, scope):
		with self._lock:
			if self._active_count == 0:
				try:
					self._install()
				except BaseException:
					self._uninstall()
					raise

			self._scopes().append(scope)
			self._active_count += 1

	# Leave one scope and restore classes when the last observer exits.
	# ----------------------------------------------------------------------
	def _exit(self, scope):
		with self._lock:
			scopes = self._scopes()
			assert scopes[-1] is scope
			scopes.pop()
			self._active_count -= 1

			if not scopes:
				task = self._current_task()
				if task is not None:
					del self._task_scopes[task]

			if self._active_count == 0:
				self._uninstall()

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Track reads ('r'), writes ('w') or both ('rw') in caller-owned lists.
	# Usage: with o.services.Tracker.track('rw', reads, writes): ...
	# For 'r' or 'w', the one output list is the second positional argument.
	# Calls from concurrent asyncio tasks and threads keep separate scopes.
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