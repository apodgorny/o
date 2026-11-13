# ==============================================================================
# TEST TRACKER PUBLIC API
# ==============================================================================
# Verify dependency completeness at public O object and discovery boundaries.
# ==============================================================================

from contextlib import contextmanager
from queue      import Queue

import o


class TestTrackerPublicApi(o.Tester):
	RUNTIME_PREFIX = 'o_tracker_public_'

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Collect confirmed owner IDs from the real asynchronous Sync service.
	# ----------------------------------------------------------------------
	@classmethod
	@contextmanager
	def _observe_writes(cls):
		sync     = o.services.Sync
		received = Queue()
		callback = sync.subscribe(received.put)

		try:
			yield received
		finally:
			sync.unsubscribe(callback)

	# Wait until all expected owners have been published by Sync.
	# ----------------------------------------------------------------------
	@classmethod
	def _wait_for_writes(cls, received, expected):
		writes = set()

		while not expected <= writes:
			writes.update(received.get(timeout=2))

		return writes

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Serialization must observe objects reached through structural traversal.
	# ----------------------------------------------------------------------
	@classmethod
	def test_serialization_tracks_nested_objects(cls):
		state = cls._patch_runtime()

		try:
			Finance  = o.T.extend('TrackerPublicFinance', salary=int)
			Employee = o.T.extend('TrackerPublicEmployee', finance=Finance)
			finance  = Finance(salary=200)
			employee = Employee(finance=finance)
			reads    = []

			with o.services.Tracker.track_reads(reads):
				assert employee.to_data() == {'finance': {'salary': 200}}
				assert employee.to_json()
				assert employee.serialize()

			assert employee.id in reads
			assert finance.id in reads

			with cls._observe_writes() as received:
				finance.salary = 250
				writes = cls._wait_for_writes(received, {finance.id})

			assert finance.id in writes
			assert set(reads) & set(writes)
		finally:
			cls._restore_runtime(state)

	# Even an empty traversal depends on the object being traversed.
	# ----------------------------------------------------------------------
	@classmethod
	def test_empty_object_traversal_tracks_owner(cls):
		state = cls._patch_runtime()

		try:
			Model = o.T.extend('TrackerPublicEmpty', value=o.F(int, default=None))
			item  = Model()
			reads = []

			with o.services.Tracker.track_reads(reads):
				assert item.to_data() == {}

			assert item.id in reads
		finally:
			cls._restore_runtime(state)

	# An empty class enumeration must invalidate when an instance is born.
	# ----------------------------------------------------------------------
	@classmethod
	def test_empty_class_enumeration_and_creation(cls):
		state = cls._patch_runtime()

		try:
			Model  = o.T.extend('TrackerPublicInstances', value=int)
			reads  = []

			with o.services.Tracker.track_reads(reads):
				assert list(Model.__instances__()) == []

			assert Model.id in reads

			with cls._observe_writes() as received:
				item   = Model(value=1)
				writes = cls._wait_for_writes(received, {item.id, Model.id})

			assert item.id in writes
			assert Model.id in writes
			assert set(reads) & set(writes)
		finally:
			cls._restore_runtime(state)

	# Class membership must invalidate when an instance is dropped.
	# ----------------------------------------------------------------------
	@classmethod
	def test_class_enumeration_and_deletion(cls):
		state = cls._patch_runtime()

		try:
			Model  = o.T.extend('TrackerPublicDrop', value=int)
			item   = Model(value=1)
			reads  = []

			with o.services.Tracker.track_reads(reads):
				assert item.id in [value.id for value in Model.__instances__()]

			with cls._observe_writes() as received:
				item.drop()
				writes = cls._wait_for_writes(received, {item.id, Model.id})

			assert Model.id in reads
			assert Model.id in writes
			assert item.id in writes
			assert set(reads) & set(writes)
		finally:
			cls._restore_runtime(state)

	# Reading an absent entity records the identity that its birth will write.
	# ----------------------------------------------------------------------
	@classmethod
	def test_missing_entity_existence(cls):
		state = cls._patch_runtime()

		try:
			Model  = o.T.extend('TrackerPublicExists', value=int)
			proto  = f'{Model.__proto__}._{Model.__version__}'
			reads  = []

			with o.services.Tracker.track_reads(reads):
				assert not o.services.Entity.exists(proto)

			assert o.services.Id.hash(proto) in reads

			with cls._observe_writes() as received:
				item   = Model(value=7)
				writes = cls._wait_for_writes(received, {item.id})

			assert item.__proto__ == proto
			assert item.id in writes
			assert set(reads) & set(writes)
		finally:
			cls._restore_runtime(state)

	# Subclass membership uses the parent class as a dependency.
	# ----------------------------------------------------------------------
	@classmethod
	def test_subclass_enumeration_and_extension(cls):
		state = cls._patch_runtime()

		try:
			Base   = o.T.extend('TrackerPublicBase')
			reads  = []

			with o.services.Tracker.track_reads(reads):
				assert Base.__subclasses__() == []

			with cls._observe_writes() as received:
				Child  = Base.extend('TrackerPublicChild')
				writes = cls._wait_for_writes(received, {Base.id})

			assert Child.__parent__ is Base
			assert Base.id in reads
			assert Base.id in writes
			assert set(reads) & set(writes)
		finally:
			cls._restore_runtime(state)

	# Newly introduced observation paths must restore their original methods.
	# ----------------------------------------------------------------------
	@classmethod
	def test_new_interceptors_are_reversible(cls):
		tracker           = o.services.Tracker
		original_data      = o.T.__dict__['to_data']
		original_serialize = o.Serializer.__dict__['_serialize_instance']
		original_tree      = o.Tree.__dict__['_render_node']
		original_instances = o.TMeta.__dict__['__instances__']
		original_create   = o.TMeta.__dict__['__call__']
		original_remove   = type(o.services.Id).__dict__['unset']
		reads             = []
		writes            = []

		with tracker.track_reads(reads):
			assert o.T.__dict__['to_data'] is not original_data
			assert o.Serializer.__dict__['_serialize_instance'] is not original_serialize
			assert o.Tree.__dict__['_render_node'] is not original_tree
			assert o.TMeta.__dict__['__instances__'] is not original_instances
			assert o.TMeta.__dict__['__call__'] is original_create
			assert type(o.services.Id).__dict__['unset'] is original_remove

		assert o.T.__dict__['to_data'] is original_data
		assert o.Serializer.__dict__['_serialize_instance'] is original_serialize
		assert o.Tree.__dict__['_render_node'] is original_tree
		assert o.TMeta.__dict__['__instances__'] is original_instances
		assert o.TMeta.__dict__['__call__'] is original_create
		assert type(o.services.Id).__dict__['unset'] is original_remove


if __name__ == '__main__':
	TestTrackerPublicApi.run()
