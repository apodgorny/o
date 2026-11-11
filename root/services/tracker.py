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

	# Append a known persistent identity without resolving an object.
	# ----------------------------------------------------------------------
	def _record_id(self, operation, entity_id):
		for mode, reads, writes in self._scopes(False):
			if operation == 'r' and 'r' in mode:
				reads.append(entity_id)
			elif operation == 'w' and 'w' in mode:
				writes.append(entity_id)

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

	# Observe structural traversal, including an object with no children.
	# A generator records at iteration time, inside the actual read scope.
	# ----------------------------------------------------------------------
	def _install_dependants_read(self):
		cls      = o.T
		name     = '__dependants__'
		original = cls.__dict__[name]
		self._saved_reads[(cls, name)] = original

		def dependants(instance, *args, **kwargs):
			self._record('r', instance)
			yield from original(instance, *args, **kwargs)

		type.__setattr__(cls, name, dependants)

	# Observe class membership even when enumeration yields no instances.
	# ----------------------------------------------------------------------
	def _install_class_enumeration_read(self):
		cls = o.TMeta

		for name in ('__instances__', '__subclasses__'):
			original = cls.__dict__[name]
			self._saved_reads[(cls, name)] = original

			if name == '__instances__':
				def instances(owner):
					self._record('r', owner)
					yield from original_instances(owner)

				original_instances = original
				wrapper = instances
			else:
				def subclasses(owner):
					result = original_subclasses(owner)
					self._record('r', owner)
					return result

				original_subclasses = original
				wrapper = subclasses

			type.__setattr__(cls, name, wrapper)

	# Observe existence checks without altering their results.
	# An absent entity has no live object, so track its prospective identity.
	# ----------------------------------------------------------------------
	def _install_existence_read(self):
		cls      = type(o.services.Entity)
		name     = 'exists'
		original = cls.__dict__[name]
		self._saved_reads[(cls, name)] = original

		def exists(service, identity):
			result = original(service, identity)

			if type(identity) is int:
				entity_id = identity
			elif isinstance(identity, str) and (identity == 'o.T' or identity.startswith('o.T.')):
				entity_id = o.services.Id.hash(identity)
			else:
				entity_id = o.T.id

			self._record_id('r', entity_id)
			return result

		type.__setattr__(cls, name, exists)

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
		self._install_dependants_read()
		self._install_class_enumeration_read()
		self._install_existence_read()

	# Record new instances only after construction has completed successfully.
	# ----------------------------------------------------------------------
	def _install_instance_creation_write(self):
		cls      = o.TMeta
		name     = '__call__'
		original = cls.__dict__[name]
		self._saved_writes[(cls, name)] = original

		def construct(owner, *args, **kwargs):
			result = original(owner, *args, **kwargs)
			passed = args[0] if args else UNDEFINED

			if result is not passed:
				self._record('w', result)
				self._record('w', result.__class__)

			return result

		type.__setattr__(cls, name, construct)

	# Record deletion of a persisted entity and change to its class membership.
	# ----------------------------------------------------------------------
	def _install_entity_deletion_write(self):
		cls      = type(o.services.Id)
		name     = 'unset'
		original = cls.__dict__[name]
		self._saved_writes[(cls, name)] = original

		def unset(service, entity_id):
			entity = o.services.Cache.entities.get(entity_id, UNDEFINED)
			result = original(service, entity_id)
			self._record_id('w', entity_id)

			if entity is not UNDEFINED:
				if isinstance(entity, type):
					parent = entity.__parent__
					if parent is not None:
						self._record('w', parent)
				else:
					self._record('w', entity.__class__)

			return result

		type.__setattr__(cls, name, unset)

	# Register changes in the set of classes and their fields.
	# ----------------------------------------------------------------------
	def _install_class_mutation_write(self):
		cls = o.TMeta

		for name in ('extend', '__setattr__', '__delattr__'):
			original = cls.__dict__[name]
			self._saved_writes[(cls, name)] = original

			if name == 'extend':
				def extend(owner, *args, **kwargs):
					result = original_extend(owner, *args, **kwargs)
					self._record('w', owner)
					self._record('w', result)
					return result

				original_extend = original
				wrapper = extend
			elif name == '__setattr__':
				def assign(owner, field, value):
					result = original_assign(owner, field, value)
					if not field.startswith('_') and field != 'id':
						self._record('w', owner)
					return result

				original_assign = original
				wrapper = assign
			else:
				def delete(owner, field):
					result = original_delete(owner, field)
					if not field.startswith('_') and field != 'id':
						self._record('w', owner)
					return result

				original_delete = original
				wrapper = delete

			type.__setattr__(cls, name, wrapper)

	# Register source-route updates for existence queries by route.
	# ----------------------------------------------------------------------
	def _install_route_write(self):
		cls = type(o.services.Route)

		for name in ('set', 'unset'):
			original = cls.__dict__[name]
			self._saved_writes[(cls, name)] = original

			if name == 'set':
				def set(service, route, value):
					result = original_set(service, route, value)
					self._record('w', o.T)
					return result

				original_set = original
				wrapper = set
			else:
				def unset(service, route):
					result = original_unset(service, route)
					self._record('w', o.T)
					return result

				original_unset = original
				wrapper = unset

			type.__setattr__(cls, name, wrapper)

	# Add write-side wrappers without affecting the read-only hot path.
	# ----------------------------------------------------------------------
	def _install_writes(self):
		self._install_field_writer()
		self._install_field_deletion()

		for cls in (o.List, o.Dict):
			self._install_collection_writer(cls)

		self._install_instance_creation_write()
		self._install_entity_deletion_write()
		self._install_class_mutation_write()
		self._install_route_write()

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