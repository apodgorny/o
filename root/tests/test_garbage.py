import os
import shutil
import tempfile

import o

UNDEFINED = o.Undefined


class GarbageInstance:

	def __init__(self, id, proto, dependants=None):
		self.id = id
		self.__proto__ = proto
		self.dependants = dependants or []

	def __dependants__(self):
		for dependant in self.dependants:
			yield dependant


class TestGarbage(o.Tester):
	__route__ = __file__

	# ----------------------------------------------------------------------
	@classmethod
	def _patch_memory(cls):
		root    = tempfile.mkdtemp(prefix='o_garbage_')
		path    = os.path.join(root, '__memory__')
		memory  = o.services.Memory
		garbage = o.services.Garbage
		state   = {
			'root'         : root,
			'memory'       : memory,
			'garbage'      : garbage,
			'old_path'     : getattr(memory, 'path', UNDEFINED),
			'old_size'     : getattr(memory, 'size', UNDEFINED),
			'old_data_dir' : o.DATA_DIR,
			'old_size_key' : o.MEMORY_SIZE,
		}

		o.DATA_DIR    = os.path.relpath(path, o.__path__)
		o.MEMORY_SIZE = 10485760
		memory.initialize()
		garbage.initialize()

		return state

	# ----------------------------------------------------------------------
	@classmethod
	def _restore_memory(cls, state):
		memory = state['memory']
		o.DATA_DIR = state['old_data_dir']
		o.MEMORY_SIZE = state['old_size_key']

		if state['old_path'] is not UNDEFINED and state['old_size'] is not UNDEFINED:
			memory.path = state['old_path']
			memory.size = state['old_size']
			memory.initialize()
			state['garbage'].initialize()

		if os.path.isdir(state['root']):
			shutil.rmtree(state['root'])

	# ----------------------------------------------------------------------
	@classmethod
	def _instance(cls, id, proto, dependants=None):
		return GarbageInstance(id, proto, dependants)

	# ----------------------------------------------------------------------
	@classmethod
	def _type(cls, id, proto, is_temp):
		return type(
			f'GarbageType{id}',
			(),
			{
				'id'         : id,
				'__proto__'  : proto,
				'__is_temp__': is_temp,
			}
		)

	# ----------------------------------------------------------------------
	@classmethod
	def test_link_sets_refcount_and_removes_garbage(cls):
		state = cls._patch_memory()

		try:
			garbage = state['garbage']
			instance = cls._instance(10, 'o.T.Node._0')

			garbage.garbage.set(instance.id, instance.__proto__)
			garbage.on_instance_link(instance)

			assert garbage.refcounts.get(instance.id, 0) == 1
			assert garbage.garbage.has(instance.id) == False
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_duplicate_links_do_not_duplicate_dependant_liveness(cls):
		state = cls._patch_memory()

		try:
			garbage = state['garbage']
			child   = cls._instance(11, 'o.T.Child._0')
			parent  = cls._instance(12, 'o.T.Parent._0', [child])

			garbage.on_instance_link(parent)
			garbage.on_instance_link(parent)

			assert garbage.refcounts.get(parent.id, 0) == 2
			assert garbage.refcounts.get(child.id, 0) == 1
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_unlink_two_to_one_keeps_dependants_alive(cls):
		state = cls._patch_memory()

		try:
			garbage = state['garbage']
			child   = cls._instance(13, 'o.T.Child._1')
			parent  = cls._instance(14, 'o.T.Parent._1', [child])

			garbage.on_instance_link(parent)
			garbage.on_instance_link(parent)
			garbage.on_instance_unlink(parent)

			assert garbage.refcounts.get(parent.id, 0) == 1
			assert garbage.refcounts.get(child.id, 0) == 1
			assert garbage.garbage.has(parent.id) == False
			assert garbage.garbage.has(child.id) == False
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_unlink_one_to_zero_marks_garbage_and_unlinks_dependants(cls):
		state = cls._patch_memory()

		try:
			garbage = state['garbage']
			child   = cls._instance(15, 'o.T.Child._2')
			parent  = cls._instance(16, 'o.T.Parent._2', [child])

			garbage.on_instance_link(parent)
			garbage.on_instance_unlink(parent)

			assert garbage.refcounts.get(parent.id, 0) == 0
			assert garbage.refcounts.get(child.id, 0) == 0
			assert garbage.garbage.get(parent.id) == parent.__proto__
			assert garbage.garbage.get(child.id) == child.__proto__
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_unlink_at_zero_does_not_go_negative(cls):
		state = cls._patch_memory()

		try:
			garbage = state['garbage']
			instance = cls._instance(17, 'o.T.Node._1')

			garbage.on_instance_unlink(instance)

			assert garbage.refcounts.get(instance.id, 0) == 0
			assert garbage.garbage.get(instance.id) == instance.__proto__
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_nested_liveness_propagates_only_on_boundary(cls):
		state = cls._patch_memory()

		try:
			garbage = state['garbage']
			leaf    = cls._instance(18, 'o.T.Leaf._0')
			child   = cls._instance(19, 'o.T.Child._3', [leaf])
			parent  = cls._instance(20, 'o.T.Parent._3', [child])

			garbage.on_instance_link(parent)
			garbage.on_instance_link(child)
			garbage.on_instance_unlink(parent)

			assert garbage.refcounts.get(parent.id, 0) == 0
			assert garbage.refcounts.get(child.id, 0) == 1
			assert garbage.refcounts.get(leaf.id, 0) == 1
			assert garbage.garbage.get(parent.id) == parent.__proto__
			assert garbage.garbage.has(child.id) == False
			assert garbage.garbage.has(leaf.id) == False
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_class_create_marks_only_temp_classes(cls):
		state = cls._patch_memory()

		try:
			garbage = state['garbage']
			temp_cls = cls._type(21, 'o.T.__temp_21', True)
			named_cls = cls._type(22, 'o.T.Named', False)

			garbage.on_class_create(temp_cls)
			garbage.on_class_create(named_cls)

			assert garbage.garbage.get(temp_cls.id) == temp_cls.__proto__
			assert garbage.garbage.has(named_cls.id) == False
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_first_temp_instance_removes_class_from_garbage(cls):
		state = cls._patch_memory()

		try:
			garbage = state['garbage']
			temp_cls = cls._type(23, 'o.T.__temp_23', True)
			instance = temp_cls()

			garbage.on_class_create(temp_cls)
			garbage.on_instance_create(instance)

			assert garbage.instancecounts.get(temp_cls.id, 0) == 1
			assert garbage.garbage.has(temp_cls.id) == False
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_temp_instance_delete_returns_class_to_garbage_on_zero(cls):
		state = cls._patch_memory()

		try:
			garbage = state['garbage']
			temp_cls = cls._type(24, 'o.T.__temp_24', True)
			first = temp_cls()
			second = temp_cls()

			garbage.on_instance_create(first)
			garbage.on_instance_create(second)
			garbage.on_instance_delete(first)

			assert garbage.instancecounts.get(temp_cls.id, 0) == 1
			assert garbage.garbage.has(temp_cls.id) == False

			garbage.on_instance_delete(second)

			assert garbage.instancecounts.get(temp_cls.id, 0) == 0
			assert garbage.garbage.get(temp_cls.id) == temp_cls.__proto__
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_non_temp_instances_do_not_touch_instancecounts(cls):
		state = cls._patch_memory()

		try:
			garbage = state['garbage']
			named_cls = cls._type(25, 'o.T.NamedClass', False)
			instance = named_cls()

			garbage.on_instance_create(instance)
			garbage.on_instance_delete(instance)

			assert garbage.instancecounts.has(named_cls.id) == False
			assert garbage.garbage.has(named_cls.id) == False
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_collect_removes_garbage_rooms_and_clears_garbage(cls):
		state = cls._patch_memory()

		try:
			memory = state['memory']
			garbage = state['garbage']
			proto = 'o.T.Node._2'
			other_proto = 'o.T.Node._20'
			id = 26

			memory.set(proto, True)
			memory.set(f'{proto}.name', 7)
			memory.set(other_proto, True)
			memory.set(f'{other_proto}.name', 20)
			memory.set('o.T.Other._0', True)
			garbage.garbage.set(id, proto)

			garbage.collect()

			assert memory.has(proto) == False
			assert memory.has(f'{proto}.name') == False
			assert memory.has(other_proto) == True
			assert memory.has(f'{other_proto}.name') == True
			assert memory.has('o.T.Other._0') == True
			assert garbage.garbage.has(id) == False
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_initialize_collects_existing_garbage(cls):
		state = cls._patch_memory()

		try:
			memory = state['memory']
			garbage = state['garbage']
			proto = 'o.T.Node._3'
			id = 27

			memory.set(proto, True)
			memory.set(f'{proto}.name', 7)
			garbage.garbage.set(id, proto)

			garbage.initialize()

			assert memory.has(proto) == False
			assert memory.has(f'{proto}.name') == False
			assert garbage.garbage.has(id) == False
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_collect_removes_temp_classes_and_instances_from_memory(cls):
		state = cls._patch_memory()

		try:
			memory = state['memory']
			garbage = state['garbage']
			class_a = 'o.T.__temp_a'
			class_b = 'o.T.__temp_b'
			instance_a = f'{class_a}._0'
			instance_b = f'{class_b}._0'
			keep = 'o.T.Keep._0'

			memory.set(class_a, True)
			memory.set(f'{class_a}.__version__', 1)
			memory.set(instance_a, True)
			memory.set(f'{instance_a}.value', 1)
			memory.set(class_b, True)
			memory.set(instance_b, True)
			memory.set(f'{instance_b}.value', 2)
			memory.set(keep, True)

			garbage.garbage.set(31, class_a)
			garbage.garbage.set(32, instance_b)

			before_count = len(list(memory.keys()))

			garbage.collect()

			after_count = len(list(memory.keys()))

			assert after_count < before_count
			assert memory.has(class_a) == False
			assert memory.has(f'{class_a}.__version__') == False
			assert memory.has(instance_a) == False
			assert memory.has(f'{instance_a}.value') == False
			assert memory.has(class_b) == True
			assert memory.has(instance_b) == False
			assert memory.has(f'{instance_b}.value') == False
			assert memory.has(keep) == True
			assert garbage.garbage.has(31) == False
			assert garbage.garbage.has(32) == False
		finally:
			cls._restore_memory(state)


if __name__ == '__main__':
	TestGarbage.run()
