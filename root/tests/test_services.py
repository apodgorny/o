# ==============================================================================
# TEST ONTOLOGY SERVICES
# ==============================================================================
# Verify singular service names, cache ownership, and entity value semantics.
# ==============================================================================

import inspect
import time

from unittest.mock import patch

import o


class TestServices(o.Tester):

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Keep one service per responsibility and retain the explicit start call.
	# ----------------------------------------------------------------------
	@classmethod
	def test_service_layout(cls):
		assert type(o.services.Cache).__name__ == 'Cache'
		assert type(o.services.Entity).__name__ == 'Entity'
		assert type(o.services.Id).__name__ == 'Id'
		assert type(o.services.Route).__name__ == 'Route'
		assert type(o.services.Migration).__name__ == 'Migration'
		assert o.start.__self__ is o.services.Ontology

	# Keep the fast LMDB policy as the explicit public API default.
	# ----------------------------------------------------------------------
	@classmethod
	def test_start_sync_default(cls):
		assert inspect.signature(o.start).parameters['sync'].default is False

	# Resolve loaded classes through their cache keys and annotations.
	# ----------------------------------------------------------------------
	@classmethod
	def test_cache_owns_registry(cls):
		cache = o.services.Cache

		assert cache.cast_map[int] == o.Int.__proto__
		assert cache.entities[o.Int.id] is o.Int
		assert o.services.Entity.get(o.Int.id) is o.Int
		assert o.services.Entity.get_by_annotation(int) is o.Int

	# Return primitive values for atoms and entities for structured objects.
	# ----------------------------------------------------------------------
	@classmethod
	def test_entity_value(cls):
		state = cls._patch_runtime()

		try:
			integer = o.Int(73)

			assert o.services.Entity.value(integer.id) == 73
			assert o.services.Entity.value(o.V.id) is o.V
		finally:
			cls._restore_runtime(state)

	# Looking up an absent class must not create an id mapping on disk.
	# ----------------------------------------------------------------------
	@classmethod
	def test_missing_class_lookup_is_read_only(cls):
		name  = f'AbsentType{time.time_ns()}'
		proto = f'{o.T.__proto__}.{name}'
		id    = o.services.Id.hash(proto)

		assert not o.services.Id.has(id)
		assert not hasattr(o.T, name)
		assert not o.services.Id.has(id)

	# A newly defined type must publish its id after successful creation.
	# ----------------------------------------------------------------------
	@classmethod
	def test_new_class_id_is_persisted(cls):
		state = cls._patch_runtime()

		try:
			name  = f'IdRegistration{time.time_ns()}'
			Class = o.T.extend(name)

			assert Class.id == o.services.Id.hash(Class.__proto__)
			assert o.services.Id.get(Class.id) == Class.__proto__
			assert o.services.Entity.get(Class.id) is Class
		finally:
			cls._restore_runtime(state)

	# Reconstructing an already persisted instance must not write its id again.
	# ----------------------------------------------------------------------
	@classmethod
	def test_instance_reconstruction_is_read_only(cls):
		state = cls._patch_runtime()

		try:
			integer = o.Int(73)
			ids     = o.services.Id

			assert ids.get(integer.id) == integer.__proto__

			with patch.object(ids, 'set', side_effect=AssertionError('Unexpected id write')):
				reopened = o.Int.__read__(f'_{integer.__version__}')

			assert reopened.id == integer.id
			assert reopened.__proto__ == integer.__proto__
		finally:
			cls._restore_runtime(state)

	# Keep service paths in normal Python's attribute cache.
	# ----------------------------------------------------------------------
	@classmethod
	def test_cached_service_path(cls):
		services = o.services
		entity   = services.Entity

		assert o.__dict__['services'] is services
		assert services.__dict__['Entity'] is entity

	# Reload an atom from storage while preserving its identity.
	# ----------------------------------------------------------------------
	@classmethod
	def test_atom_invalidation(cls):
		state = cls._patch_runtime()

		try:
			integer = o.Int(73)
			id      = integer.id

			o.services.Memory.set(f'{integer.__proto__}.__value__', 91)
			integer.__invalidate__()

			assert integer.id == id
			assert integer.__value__ == 91
			assert o.services.Cache.entities[id] is integer
		finally:
			cls._restore_runtime(state)

	# Reload list and dictionary item indexes from persistent storage.
	# ----------------------------------------------------------------------
	@classmethod
	def test_collection_invalidation(cls):
		state = cls._patch_runtime()

		try:
			items   = o.List([1, 2])
			mapping = o.Dict({'first': 1})

			items.__zone__.cache['__items__'] = b''
			mapping.__zone__.cache['__items__'] = b''
			items.__invalidate__()
			mapping.__invalidate__()

			assert list(items) == [1, 2]
			assert dict(mapping.items()) == {'first': 1}
			assert o.services.Cache.entities[items.id] is items
			assert o.services.Cache.entities[mapping.id] is mapping
		finally:
			cls._restore_runtime(state)

	# Clear registered entity caches without losing their registry identities.
	# ----------------------------------------------------------------------
	@classmethod
	def test_cache_invalidate_all(cls):
		state = cls._patch_runtime()

		try:
			integer = o.Int(73)
			items   = o.List([1, 2])
			cache   = o.services.Cache

			for entity in (integer, items, o.Int, o.List):
				entity.__zone__.cache['stale'] = True

			cache.invalidate_all()

			for entity in (integer, items, o.Int, o.List):
				assert cache.entities[entity.id] is entity
				assert 'stale' not in entity.__zone__.cache

			assert cache.entities[integer.__proto__] is integer
			assert cache.entities[items.__proto__] is items
		finally:
			cls._restore_runtime(state)
