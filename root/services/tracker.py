# ==============================================================================
# TRACKER SERVICE
# ==============================================================================
# Observe persistent ontology reads only within caller-owned scopes.
# Restore ordinary class descriptors outside tracked computations.
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
	_saved_reads  = {}

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

	# Append observed object identities to each active read scope.
	# ----------------------------------------------------------------------
	def _record(self, instance):
		for scope in self._scopes(False):
			scope[0].append(instance.id)

	# Observe prospective identities without resolving or loading the object.
	# ----------------------------------------------------------------------
	def _record_id(self, entity_id):
		for scope in self._scopes(False):
			scope[0].append(entity_id)

	# Install one temporary interception, retaining its original for restoration.
	# ----------------------------------------------------------------------
	def _install_interceptor(self, cls, name, replacement):
		self._saved_reads[(cls, name)] = cls.__dict__.get(name, UNDEFINED)
		type.__setattr__(cls, name, replacement)

	# Read a cached field or resolve it through the original cache-miss path.
	# ----------------------------------------------------------------------
	def _read_field(self, instance, name):
		self._record(instance)

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

		self._record(instance)
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

			self._install_interceptor(cls, name, DynamicClassAttribute(get, set, delete))

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

		def publish(cls, field_name, field):
			original(cls, field_name, field)
			with self._lock:
				if self._active_count > 0:
					self._install_property(cls, field_name, True)

		self._install_interceptor(meta, name, publish)

	# Capture dictionary membership without observing the key index twice.
	# ----------------------------------------------------------------------
	def _install_dict_membership(self):
		cls      = o.Dict
		name     = '__contains__'
		original = cls.__dict__[name]

		def contains(instance, key):
			result = original(instance, key)
			self._record(instance)

			return result

		self._install_interceptor(cls, name, contains)

	# Observe public data conversion rather than internal garbage traversals.
	# ----------------------------------------------------------------------
	def _install_public_data_read(self, name):
		cls      = o.T
		original = cls.__dict__[name]

		def convert(instance, *args, **kwargs):
			self._record(instance)
			return original(instance, *args, **kwargs)

		self._install_interceptor(cls, name, convert)

	# Observe each entity serialized, including nested and empty objects.
	# ----------------------------------------------------------------------
	def _install_serialization_read(self):
		cls      = o.Serializer
		name     = '_serialize_instance'
		original = cls.__dict__[name]

		def serialize(serializer_cls, instance, context):
			self._record(instance)
			return original.__func__(serializer_cls, instance, context)

		self._install_interceptor(cls, name, classmethod(serialize))

	# Observe each persistent node rendered by the public tree operation.
	# ----------------------------------------------------------------------
	def _install_tree_read(self):
		cls      = o.Tree
		name     = '_render_node'
		original = cls.__dict__[name]

		def render(tree, node, *args, **kwargs):
			if isinstance(node, o.T):
				self._record(node)
			return original(tree, node, *args, **kwargs)

		self._install_interceptor(cls, name, render)

	# Observe class membership, including enumerations that yield no results.
	# ----------------------------------------------------------------------
	def _install_class_enumeration_read(self):
		cls                 = o.TMeta
		original_instances  = cls.__dict__['__instances__']
		original_subclasses = cls.__dict__['__subclasses__']

		def instances(owner):
			self._record(owner)
			yield from original_instances(owner)

		def subclasses(owner):
			result = original_subclasses(owner)
			self._record(owner)
			return result

		self._install_interceptor(cls, '__instances__', instances)
		self._install_interceptor(cls, '__subclasses__', subclasses)

	# Observe existence checks without altering their results.
	# An absent entity has no live object, so track its prospective identity.
	# ----------------------------------------------------------------------
	def _install_existence_read(self):
		cls      = type(o.services.Entity)
		name     = 'exists'
		original = cls.__dict__[name]

		def exists(service, identity):
			result = original(service, identity)

			if type(identity) is int:
				entity_id = identity
			elif isinstance(identity, str) and (identity == 'o.T' or identity.startswith('o.T.')):
				entity_id = o.services.Id.hash(identity)
			else:
				entity_id = o.T.id

			self._record_id(entity_id)
			return result

		self._install_interceptor(cls, name, exists)

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
		self._install_public_data_read('to_data')
		self._install_public_data_read('to_data_shallow')
		self._install_serialization_read()
		self._install_tree_read()
		self._install_class_enumeration_read()
		self._install_existence_read()

	# Restore original descriptors after the last read scope closes.
	# ----------------------------------------------------------------------
	def _uninstall(self):
		for (cls, name), original in reversed(tuple(self._saved_reads.items())):
			if original is UNDEFINED:
				type.__delattr__(cls, name)
			else:
				type.__setattr__(cls, name, original)

		self._saved_reads.clear()

	# Install read interceptors once for overlapping nested scopes.
	# ----------------------------------------------------------------------
	def _enter(self, scope):
		with self._lock:
			if self._active_count == 0:
				try:
					self._install_reads()
				except BaseException:
					self._uninstall()
					raise

			self._scopes().append(scope)
			self._active_count += 1

	# Restore original class behavior when the last observer exits.
	# ----------------------------------------------------------------------
	def _exit(self, scope):
		with self._lock:
			scopes = self._scopes()
			assert scopes[-1] is scope
			scopes.pop()
			self._active_count -= 1

			if self._active_count == 0:
				self._uninstall()

			if not scopes:
				task = self._current_task()

				if task is not None:
					del self._task_scopes[task]
					self._thread.async_count -= 1

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Record persistent read identities in one caller-owned list.
	# Use the current fork's Tracker: o.services.Tracker.track('r', reads).
	# Nested calls, threads, and asynchronous tasks retain separate scopes.
	# ----------------------------------------------------------------------
	@contextmanager
	def track(self, mode, reads=None):
		if mode != 'r':
			raise ValueError(f'Invalid tracking mode: {mode!r}')

		if not isinstance(reads, list):
			raise TypeError('Read tracking requires a list')

		scope = (reads,)
		self._enter(scope)

		try:
			yield
		finally:
			self._exit(scope)
