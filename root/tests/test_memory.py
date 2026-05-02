import os
import shutil
import tempfile

import o

UNDEFINED = o.Undefined


class TestMemory(o.Tester):

	# ----------------------------------------------------------------------
	@classmethod
	def _patch_memory(cls):
		root   = tempfile.mkdtemp(prefix='o_memory_')
		path   = os.path.join(root, '__memory__')
		memory = o.services.Memory
		state  = {
			'root'         : root,
			'memory'       : memory,
			'old_path'     : getattr(memory, 'path', UNDEFINED),
			'old_size'     : getattr(memory, 'size', UNDEFINED),
			'old_data_dir' : o.DATA_DIR,
			'old_size_key' : o.MEMORY_SIZE,
		}

		o.DATA_DIR    = os.path.relpath(path, o.__path__)
		o.MEMORY_SIZE = 10485760
		memory.initialize()

		return state

	# ----------------------------------------------------------------------
	@classmethod
	def _restore_memory(cls, state):
		memory   = state['memory']
		old_path = state['old_path']
		old_size = state['old_size']
		o.DATA_DIR    = state['old_data_dir']
		o.MEMORY_SIZE = state['old_size_key']

		if old_path is not UNDEFINED and old_size is not UNDEFINED:
			memory.path = old_path
			memory.size = old_size
			memory.initialize()

		if os.path.isdir(state['root']):
			shutil.rmtree(state['root'])

	# ----------------------------------------------------------------------
	@classmethod
	def test_initialize_sets_path_and_size(cls):
		state = cls._patch_memory()

		try:
			assert state['memory'].path == os.path.realpath(os.path.join(state['root'], '__memory__'))
			assert state['memory'].size == 10485760
			assert os.path.isdir(state['memory'].path)
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_to_bytes_and_from_bytes_support_all_atomic_types(cls):
		values = (
			None,
			True,
			False,
			0,
			17,
			-4,
			0.0,
			3.25,
			'Alexander',
			b'abc',
		)

		for value in values:
			data = o.services.Memory.to_bytes(value)
			assert o.services.Memory.from_bytes(data) == value

	# ----------------------------------------------------------------------
	@classmethod
	def test_set_get_and_has(cls):
		state = cls._patch_memory()

		try:
			memory = state['memory']

			memory.set('o.T.User', 'Ada')

			assert memory.has('o.T.User') == True
			assert memory.get('o.T.User') == 'Ada'
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_get_returns_default_for_missing(cls):
		state = cls._patch_memory()

		try:
			memory = state['memory']

			assert memory.get('missing') is UNDEFINED
			assert memory.get('missing', 'fallback') == 'fallback'
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_unset_removes_value(cls):
		state = cls._patch_memory()

		try:
			memory = state['memory']

			memory.set('o.T.User', 7)
			memory.unset('o.T.User')

			assert memory.has('o.T.User') == False
			assert memory.get('o.T.User') is UNDEFINED
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_items_iterates_by_prefix(cls):
		state = cls._patch_memory()

		try:
			memory = state['memory']

			memory.set('o.T.User._.age.type', 7)
			memory.set('o.T.User._.name.default', 'Ada')
			memory.set('o.T.Other._.age.type', 9)

			items = list(memory.items('o.T.User._'))

			assert items == [
				('o.T.User._.age.type', 7),
				('o.T.User._.name.default', 'Ada'),
			]
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_keys_iterates_by_prefix(cls):
		state = cls._patch_memory()

		try:
			memory = state['memory']

			memory.set('o.T.User._.age.type', 7)
			memory.set('o.T.User._.name.default', 'Ada')
			memory.set('o.T.Other._.age.type', 9)

			keys = list(memory.keys('o.T.User._'))

			assert keys == [
				'o.T.User._.age.type',
				'o.T.User._.name.default',
			]
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_unset_all_removes_prefix(cls):
		state = cls._patch_memory()

		try:
			memory = state['memory']

			memory.set('o.T.User._.age.type', 7)
			memory.set('o.T.User._.name.default', 'Ada')
			memory.set('o.T.Other._.age.type', 9)

			memory.unset_all('o.T.User._')

			assert memory.has('o.T.User._.age.type') == False
			assert memory.has('o.T.User._.name.default') == False
			assert memory.has('o.T.Other._.age.type') == True
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_write_batch_groups_operations(cls):
		state = cls._patch_memory()

		try:
			memory = state['memory']

			with memory.write() as batch:
				batch.set('o.T.User.name', 'Ada')
				batch.set('o.T.User.age', 37)

			assert memory.get('o.T.User.name') == 'Ada'
			assert memory.get('o.T.User.age') == 37
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_nested_write_batch_reuses_transaction(cls):
		state = cls._patch_memory()

		try:
			memory = state['memory']

			with memory.write() as outer:
				with memory.write() as inner:
					assert outer is inner
					inner.set('o.T.User.name', 'Ada')

			assert memory.get('o.T.User.name') == 'Ada'
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_zone_set_get_has_and_remove(cls):
		state = cls._patch_memory()

		try:
			memory = state['memory']
			zone   = memory.zone('o.T.User._.')

			zone.set('age.type', 7)

			assert zone.has('age.type') == True
			assert zone.get('age.type') == 7
			assert memory.get('o.T.User._.age.type') == 7

			zone.unset('age.type')

			assert zone.has('age.type') == False
			assert zone.get('age.type') is UNDEFINED
			assert memory.has('o.T.User._.age.type') == False
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_zone_get_returns_default_for_missing(cls):
		state = cls._patch_memory()

		try:
			zone = state['memory'].zone('o.T.User._.')

			assert zone.get('missing') is UNDEFINED
			assert zone.get('missing', 'fallback') == 'fallback'
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_zone_items_and_keys_strip_prefix(cls):
		state = cls._patch_memory()

		try:
			memory = state['memory']
			zone   = memory.zone('o.T.User._.')

			memory.set('o.T.User._.age.type', 7)
			memory.set('o.T.User._.name.default', 'Ada')
			memory.set('o.T.Other._.age.type', 9)

			items = list(zone.items())
			keys  = list(zone.keys())

			assert items == [
				('age.type', 7),
				('name.default', 'Ada'),
			]
			assert keys == [
				'age.type',
				'name.default',
			]
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_zone_clear_removes_only_zone_prefix(cls):
		state = cls._patch_memory()

		try:
			memory = state['memory']
			zone   = memory.zone('o.T.User._.')

			zone.set('age.type', 7)
			zone.set('name.default', 'Ada')
			memory.set('o.T.Other._.age.type', 9)

			zone.clear()

			assert memory.has('o.T.User._.age.type') == False
			assert memory.has('o.T.User._.name.default') == False
			assert memory.has('o.T.Other._.age.type') == True
			assert zone.has('age.type') == False
		finally:
			cls._restore_memory(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_zone_prefix_is_isolated(cls):
		state = cls._patch_memory()

		try:
			memory    = state['memory']
			user_zone = memory.zone('o.T.User._.')
			post_zone = memory.zone('o.T.Post._.')

			user_zone.set('title.default', 'User')
			post_zone.set('title.default', 'Post')

			assert user_zone.get('title.default') == 'User'
			assert post_zone.get('title.default') == 'Post'
			assert memory.get('o.T.User._.title.default') == 'User'
			assert memory.get('o.T.Post._.title.default') == 'Post'
		finally:
			cls._restore_memory(state)


if __name__ == '__main__':
	TestMemory.run()
