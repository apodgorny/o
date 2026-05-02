import os
import shutil
import tempfile

import o

UNDEFINED = o.Undefined


class TestGc(o.Tester):
	__route__ = __file__

	# ----------------------------------------------------------------------
	@classmethod
	def _patch_registry(cls):
		services = o.services
		registry = type('RegistryState', (), {})()
		state    = {
			'services'     : services,
			'had_registry' : 'Registry' in services.__dict__,
			'registry'     : services.__dict__.get('Registry'),
			'paths'        : {},
		}

		def add(id, path):
			state['paths'][id] = path

		def remove(id):
			if id in state['paths']:
				del state['paths'][id]

		def get(id):
			return state['paths'].get(id, UNDEFINED)

		registry.add    = add
		registry.remove = remove
		registry.get    = get

		services.Registry = registry

		return state

	# ----------------------------------------------------------------------
	@classmethod
	def _restore_registry(cls, state):
		services = state['services']

		if state['had_registry']:
			services.Registry = state['registry']
		else:
			del services.Registry

	# ----------------------------------------------------------------------
	@classmethod
	def _patch_runtime(cls):
		temp_root      = os.path.join(o.__path__, '__tmp__')
		registry_state = cls._patch_registry()

		os.makedirs(temp_root, exist_ok=True)

		root = tempfile.mkdtemp(prefix='o_gc_', dir=temp_root)

		state = {
			'root'      : root,
			'temp_root' : temp_root,
			'registry'  : registry_state,
			'data_dir'  : o.DATA_DIR,
			'entities'  : dict(o.__entities__),
			'cast_map'  : dict(o.__cast_map__),
			'value'     : o.__dict__.get('V', UNDEFINED),
		}

		o.DATA_DIR = os.path.join('__tmp__', os.path.basename(root))

		return state

	# ----------------------------------------------------------------------
	@classmethod
	def _restore_runtime(cls, state):
		o.DATA_DIR = state['data_dir']

		o.__entities__.clear()
		o.__entities__.update(state['entities'])

		o.__cast_map__.clear()
		o.__cast_map__.update(state['cast_map'])

		if state['value'] is UNDEFINED:
			if 'V' in o.__dict__:
				del o.__dict__['V']
		else:
			o.__dict__['V'] = state['value']

		cls._restore_registry(state['registry'])

		if os.path.exists(state['root']):
			shutil.rmtree(state['root'])

		if os.path.isdir(state['temp_root']):
			shutil.rmtree(state['temp_root'])

	# ----------------------------------------------------------------------
	# @classmethod
	def test_o_v_accepts_and_deletes_regular_attrs(cls):
		state = cls._patch_runtime()

		try:
			if 'V' in o.__dict__:
				del o.__dict__['V']

			value = o.ensure_value()

			value.foo = 1

			assert value.foo == 1
			assert o.services.Memory.has(f'{value.__proto__}.foo') == True

			del value.foo

			assert o.services.Memory.has(f'{value.__proto__}.foo') == False

			try:
				value.foo
				assert False
			except AttributeError:
				pass
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	# @classmethod
	def test_attr_add_links_chain_on_0_to_1(cls):
		state = cls._patch_runtime()

		try:
			if 'V' in o.__dict__:
				del o.__dict__['V']

			root      = o.ensure_value()
			root_name = os.path.basename(state['root'])
			Node      = o.T.extend(f'GcAttrAddNode_{root_name}')
			parent    = Node()
			child     = Node()

			parent.child = child

			assert parent.__refcount__ == 0
			assert child.__refcount__ == 0

			root.parent = parent

			assert parent.__refcount__ == 1
			assert child.__refcount__ == 1
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	# @classmethod
	def test_attr_shared_child_keeps_children_unchanged_on_1_to_2_and_2_to_1(cls):
		state = cls._patch_runtime()

		try:
			if 'V' in o.__dict__:
				del o.__dict__['V']

			root      = o.ensure_value()
			root_name = os.path.basename(state['root'])
			Node      = o.T.extend(f'GcAttrSharedNode_{root_name}')
			left      = Node()
			right     = Node()
			child     = Node()
			grand     = Node()

			child.grand = grand
			root.left   = left
			root.right  = right
			left.child  = child

			assert child.__refcount__ == 1
			assert grand.__refcount__ == 1

			right.child = child

			assert child.__refcount__ == 2
			assert grand.__refcount__ == 1

			del left.child

			assert child.__refcount__ == 1
			assert grand.__refcount__ == 1
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	# @classmethod
	def test_attr_delete_on_1_to_0_deletes_node_and_updates_children(cls):
		state = cls._patch_runtime()

		try:
			if 'V' in o.__dict__:
				del o.__dict__['V']

			root      = o.ensure_value()
			root_name = os.path.basename(state['root'])
			Node      = o.T.extend(f'GcAttrDeleteNode_{root_name}')
			owner     = Node()
			child     = Node()
			grand     = Node()

			child.grand = grand
			root.owner  = owner
			owner.child = child

			assert child.__refcount__ == 1
			assert grand.__refcount__ == 1

			del owner.child

			assert child.__refcount__ == 0
			assert grand.__refcount__ == 0
			assert o.exists(child.id) == False
			assert o.exists(grand.id) == False
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	# @classmethod
	def test_list_append_links_chain_on_0_to_1(cls):
		state = cls._patch_runtime()

		try:
			if 'V' in o.__dict__:
				del o.__dict__['V']

			root      = o.ensure_value()
			root_name = os.path.basename(state['root'])
			Node      = o.T.extend(f'GcListAppendNode_{root_name}')
			items     = o.List([])
			child     = Node()
			grand     = Node()

			child.grand = grand
			root.items  = items
			items.append(child)

			assert child.__refcount__ == 1
			assert grand.__refcount__ == 1
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	# @classmethod
	def test_list_shared_item_keeps_children_unchanged_on_1_to_2_and_2_to_1(cls):
		state = cls._patch_runtime()

		try:
			if 'V' in o.__dict__:
				del o.__dict__['V']

			root      = o.ensure_value()
			root_name = os.path.basename(state['root'])
			Node      = o.T.extend(f'GcListSharedNode_{root_name}')
			left      = o.List([])
			right     = o.List([])
			child     = Node()
			grand     = Node()

			child.grand = grand
			root.left   = left
			root.right  = right
			left.append(child)

			assert child.__refcount__ == 1
			assert grand.__refcount__ == 1

			right.append(child)

			assert child.__refcount__ == 2
			assert grand.__refcount__ == 1

			del left[0]

			assert child.__refcount__ == 1
			assert grand.__refcount__ == 1
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	# @classmethod
	def test_list_replace_and_delete_drive_1_to_0(cls):
		state = cls._patch_runtime()

		try:
			if 'V' in o.__dict__:
				del o.__dict__['V']

			root      = o.ensure_value()
			root_name = os.path.basename(state['root'])
			Node      = o.T.extend(f'GcListReplaceNode_{root_name}')
			items     = o.List([])
			old       = Node()
			old_grand = Node()
			new       = Node()
			new_grand = Node()

			old.grand = old_grand
			new.grand = new_grand
			root.items = items
			items.append(old)

			items[0] = new

			assert old.__refcount__ == 0
			assert old_grand.__refcount__ == 0
			assert new.__refcount__ == 1
			assert new_grand.__refcount__ == 1
			assert o.exists(old.id) == False
			assert o.exists(old_grand.id) == False

			del items[0]

			assert new.__refcount__ == 0
			assert new_grand.__refcount__ == 0
			assert o.exists(new.id) == False
			assert o.exists(new_grand.id) == False
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	# @classmethod
	def test_dict_setitem_links_chain_on_0_to_1(cls):
		state = cls._patch_runtime()

		try:
			if 'V' in o.__dict__:
				del o.__dict__['V']

			root      = o.ensure_value()
			root_name = os.path.basename(state['root'])
			Node      = o.T.extend(f'GcDictAddNode_{root_name}')
			items     = o.Dict({})
			child     = Node()
			grand     = Node()

			child.grand = grand
			root.items  = items
			items['a']  = child

			assert child.__refcount__ == 1
			assert grand.__refcount__ == 1
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	# @classmethod
	def test_dict_shared_value_keeps_children_unchanged_on_1_to_2_and_2_to_1(cls):
		state = cls._patch_runtime()

		try:
			if 'V' in o.__dict__:
				del o.__dict__['V']

			root      = o.ensure_value()
			root_name = os.path.basename(state['root'])
			Node      = o.T.extend(f'GcDictSharedNode_{root_name}')
			left      = o.Dict({})
			right     = o.Dict({})
			child     = Node()
			grand     = Node()

			child.grand = grand
			root.left   = left
			root.right  = right
			left['a']   = child

			assert child.__refcount__ == 1
			assert grand.__refcount__ == 1

			right['a'] = child

			assert child.__refcount__ == 2
			assert grand.__refcount__ == 1

			del left['a']

			assert child.__refcount__ == 1
			assert grand.__refcount__ == 1
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	# @classmethod
	def test_dict_replace_and_delete_drive_1_to_0(cls):
		state = cls._patch_runtime()

		try:
			if 'V' in o.__dict__:
				del o.__dict__['V']

			root      = o.ensure_value()
			root_name = os.path.basename(state['root'])
			Node      = o.T.extend(f'GcDictReplaceNode_{root_name}')
			items     = o.Dict({})
			old       = Node()
			old_grand = Node()
			new       = Node()
			new_grand = Node()

			old.grand = old_grand
			new.grand = new_grand
			root.items = items
			items['a'] = old

			items['a'] = new

			assert old.__refcount__ == 0
			assert old_grand.__refcount__ == 0
			assert new.__refcount__ == 1
			assert new_grand.__refcount__ == 1
			assert o.exists(old.id) == False
			assert o.exists(old_grand.id) == False

			del items['a']

			assert new.__refcount__ == 0
			assert new_grand.__refcount__ == 0
			assert o.exists(new.id) == False
			assert o.exists(new_grand.id) == False
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	# @classmethod
	def test_class_delete_removes_memory_and_loaded_wrapper(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Node      = o.T.extend(f'GcDeleteClass_{root_name}', age=int)
			class_id  = Node.id
			proto     = Node.__proto__

			assert o.exists(proto) == True
			assert o.exists(class_id) == True
			assert class_id in o.__entities__

			Node.delete()

			assert o.exists(proto) == False
			assert o.exists(class_id) == False
			assert class_id not in o.__entities__
			assert o.get(class_id) is UNDEFINED
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	# @classmethod
	def test_temp_classes_clear_deletes_marked_classes(cls):
		state = cls._patch_runtime()

		try:
			Temp = o.T.extend()
			proto = Temp.__proto__
			id    = Temp.id

			o.services.TempClasses.set(proto)

			assert o.services.Memory.has(f'temp:{proto}') == True
			assert o.exists(proto) == True
			assert o.exists(id) == True

			o.services.TempClasses.clear()

			assert o.services.Memory.has(f'temp:{proto}') == False
			assert o.exists(proto) == False
			assert o.exists(id) == False
			assert id not in o.__entities__
			assert o.get(id) is UNDEFINED
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestGc.run()
