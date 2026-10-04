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
			if isinstance(dependant, tuple):
				yield dependant
			else:
				yield dependant.__proto__, dependant.__proto__, dependant


class TestGarbage(o.Tester):

	# ----------------------------------------------------------------------
	@classmethod
	def _patch_memory(cls):
		temp_root = os.path.join(o.__path__, '__tmp__')
		root      = None
		state     = {
			'root'         : root,
			'old_data_dir' : o.DATA_DIR,
			'old_size_key' : o.MEMORY_SIZE,
		}

		os.makedirs(temp_root, exist_ok=True)
		root = tempfile.mkdtemp(prefix='o_garbage_', dir=temp_root)

		state['root'] = root

		o.DATA_DIR    = os.path.join('__tmp__', os.path.basename(root))
		o.MEMORY_SIZE = 10485760
		cls._switch_store(o.DATA_DIR)
		state['memory']  = o.services.Memory
		state['garbage'] = o.services.Garbage

		return state

	# ----------------------------------------------------------------------
	@classmethod
	def _restore_memory(cls, state):
		o.DATA_DIR = state['old_data_dir']
		o.MEMORY_SIZE = state['old_size_key']
		cls._switch_store(o.DATA_DIR)

		if os.path.isdir(state['root']):
			shutil.rmtree(state['root'])

	# ----------------------------------------------------------------------
	@classmethod
	def _patch_runtime(cls):
		temp_root = os.path.join(o.__path__, '__tmp__')
		root      = None

		os.makedirs(temp_root, exist_ok=True)
		root = tempfile.mkdtemp(prefix='o_garbage_', dir=temp_root)

		state = {
			'root'         : root,
			'data_dir'     : o.DATA_DIR,
			'entities'     : dict(o.__entities__),
			'cast_map'     : dict(o.__cast_map__),
			'value'        : o.__dict__.get('V', UNDEFINED),
			'old_size_key' : o.MEMORY_SIZE,
		}

		o.DATA_DIR = os.path.join('__tmp__', os.path.basename(root))
		cls._switch_store(o.DATA_DIR)
		state['memory']  = o.services.Memory
		state['garbage'] = o.services.Garbage

		if 'V' in o.__dict__:
			del o.__dict__['V']

		return state

	# ----------------------------------------------------------------------
	@classmethod
	def _restore_runtime(cls, state):
		o.DATA_DIR = state['data_dir']
		o.MEMORY_SIZE = state['old_size_key']

		o.__entities__.clear()
		o.__entities__.update(state['entities'])

		o.__cast_map__.clear()
		o.__cast_map__.update(state['cast_map'])

		if state['value'] is UNDEFINED:
			if 'V' in o.__dict__:
				del o.__dict__['V']
		else:
			o.__dict__['V'] = state['value']

		cls._switch_store(o.DATA_DIR)

		if os.path.isdir(state['root']):
			shutil.rmtree(state['root'])

	# ----------------------------------------------------------------------
	@classmethod
	def _instance(cls, id, proto, dependants=None):
		return GarbageInstance(id, proto, dependants)

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
	def test_root_value_allows_ad_hoc_regular_attrs(cls):
		state = cls._patch_runtime()

		try:
			value = o.ensure_value()
			value.foo = 1

			assert value.foo == 1
			assert value.__class__._.foo.type is o.Int
			assert o.services.Memory.has(f'{value.__proto__}.foo') == True

			del value.foo

			assert o.services.Memory.has(f'{value.__proto__}.foo') == False
			assert value.__class__.__has_field__('foo') == False
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_attr_mutation_updates_garbage_refcounts(cls):
		state = cls._patch_runtime()

		try:
			garbage   = state['garbage']
			root_name = os.path.basename(state['root'])
			Node      = o.T.extend(f'GarbageAttrNode_{root_name}')
			Owner     = o.T.extend(f'GarbageAttrOwner_{root_name}', child=o.F(Node, default=None))
			Root      = o.T.extend(f'GarbageAttrRoot_{root_name}', owner=Owner)
			owner     = Owner()
			child     = Node()
			root      = Root(owner=owner)
			garbage.on_instance_link(root)

			assert garbage.refcounts.get(owner.id, 0) > 0

			owner.child = child

			assert garbage.refcounts.get(child.id, 0) > 0
			assert garbage.garbage.has(child.id) == False

			del owner.child

			assert garbage.refcounts.get(child.id, 0) == 0
			assert garbage.garbage.get(child.id) == child.__proto__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_mutation_updates_garbage_refcounts(cls):
		state = cls._patch_runtime()

		try:
			garbage   = state['garbage']
			root_name = os.path.basename(state['root'])
			Node      = o.T.extend(f'GarbageListNode_{root_name}')
			Root      = o.T.extend(f'GarbageListRoot_{root_name}', items=o.List)
			items     = o.List([])
			old       = Node()
			new       = Node()
			root      = Root(items=items)
			garbage.on_instance_link(root)

			items.append(old)

			assert garbage.refcounts.get(items.id, 0) > 0
			assert garbage.refcounts.get(old.id, 0) > 0

			items[0] = new

			assert garbage.refcounts.get(old.id, 0) == 0
			assert garbage.garbage.get(old.id) == old.__proto__
			assert garbage.refcounts.get(new.id, 0) > 0

			del items[0]

			assert garbage.refcounts.get(new.id, 0) == 0
			assert garbage.garbage.get(new.id) == new.__proto__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_mutation_updates_garbage_refcounts(cls):
		state = cls._patch_runtime()

		try:
			garbage   = state['garbage']
			root_name = os.path.basename(state['root'])
			Node      = o.T.extend(f'GarbageDictNode_{root_name}')
			Root      = o.T.extend(f'GarbageDictRoot_{root_name}', items=o.Dict)
			items     = o.Dict({})
			old       = Node()
			new       = Node()
			root      = Root(items=items)
			garbage.on_instance_link(root)

			items['a'] = old

			assert garbage.refcounts.get(items.id, 0) > 0
			assert garbage.refcounts.get(old.id, 0) > 0

			items['a'] = new

			assert garbage.refcounts.get(old.id, 0) == 0
			assert garbage.garbage.get(old.id) == old.__proto__
			assert garbage.refcounts.get(new.id, 0) > 0

			del items['a']

			assert garbage.refcounts.get(new.id, 0) == 0
			assert garbage.garbage.get(new.id) == new.__proto__
		finally:
			cls._restore_runtime(state)

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
	def test_collect_removes_existing_garbage(cls):
		state = cls._patch_memory()

		try:
			memory = state['memory']
			garbage = state['garbage']
			proto = 'o.T.Node._3'
			id = 27

			memory.set(proto, True)
			memory.set(f'{proto}.name', 7)
			garbage.garbage.set(id, proto)

			garbage.collect()

			assert memory.has(proto) == False
			assert memory.has(f'{proto}.name') == False
			assert garbage.garbage.has(id) == False
		finally:
			cls._restore_memory(state)



if __name__ == '__main__':
	TestGarbage.run()
