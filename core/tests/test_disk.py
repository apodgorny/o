import os
import sys
import shutil
import tempfile

import o


class TestDisk(o.Test):

	# ----------------------------------------------------------------------
	@classmethod
	def _new_root(cls):
		root = tempfile.mkdtemp(prefix='o_disk_')

		return root

	# ----------------------------------------------------------------------
	@classmethod
	def _patch_registry(cls):
		services = o.services
		registry = type('RegistryState', (), {})()
		state    = {
			'services'      : services,
			'had_registry'  : 'Registry' in services.__dict__,
			'registry'      : services.__dict__.get('Registry'),
			'paths'         : {},
		}

		def add(id, path):
			state['paths'][id] = path

		def remove(id):
			if id in state['paths']:
				del state['paths'][id]

		def get(id):
			return state['paths'].get(id, o.undefined)

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
	def test_class_creates_disk_layout(cls):
		root           = cls._new_root()
		registry_state = cls._patch_registry()
		class_path     = os.path.join(root, 'user')

		try:
			__disk_class__ = o.disk.Class(class_path)
			loaded     = o.disk.Class.load(__disk_class__.id)

			assert __disk_class__.path == class_path
			assert loaded.path == class_path
			assert os.path.isdir(class_path)
			assert os.path.isdir(os.path.join(class_path, '__fields__'))
			assert os.path.isdir(os.path.join(class_path, '__subclasses__'))
			assert os.path.isdir(os.path.join(class_path, '__instances__'))
		finally:
			cls._restore_registry(registry_state)
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_class_persists_o_module(cls):
		root           = cls._new_root()
		registry_state = cls._patch_registry()
		class_path     = os.path.join(root, 'user')

		try:
			disk_class = o.disk.Class(class_path)
			reopened   = None

			assert disk_class.o_module is o.undefined

			disk_class.o_module = 'o.T'
			reopened            = o.disk.Class(class_path)

			assert reopened.o_module == 'o.T'
		finally:
			cls._restore_registry(registry_state)
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_fields_store_property_files(cls):
		root       = cls._new_root()
		class_path = os.path.join(root, 'user')

		try:
			fields = o.disk.Fields(class_path)
			field  = fields.set('name')

			field.set('required')
			field.set('count', 7)
			field.set('ratio', 1.5)
			field.set('enabled', True)
			field.set('default', None)

			assert fields.get('name') is field
			assert fields.has('name') == True
			assert field.get('required') == ''
			assert field.get('count') == 7
			assert field.get('ratio') == 1.5
			assert field.get('enabled') == True
			assert field.get('default') is None
			assert os.path.isfile(os.path.join(class_path, '__fields__', 'name', 'required'))

			reopened_fields = o.disk.Fields(class_path)
			reopened_field  = reopened_fields.get('name')

			assert reopened_fields.has('name') == True
			assert reopened_field.get('required') == ''
			assert reopened_field.get('count') == 7
			assert reopened_field.get('ratio') == 1.5
			assert reopened_field.get('enabled') == True
			assert reopened_field.get('default') is None
		finally:
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_fields_set_existing_field_preserves_existing_properties(cls):
		root       = cls._new_root()
		class_path = os.path.join(root, 'user')

		try:
			fields = o.disk.Fields(class_path)
			field  = fields.set('name')

			field.set('description', 'Age')
			field.set('default', 7)

			reopened_fields = o.disk.Fields(class_path)
			reopened_field  = reopened_fields.set('name')

			assert reopened_fields.has('name') == True
			assert reopened_field.get('description') == 'Age'
			assert reopened_field.get('default') == 7
		finally:
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_fields_reject_uppercase_names(cls):
		root       = cls._new_root()
		class_path = os.path.join(root, 'user')

		try:
			fields = o.disk.Fields(class_path)

			try:
				fields.set('Name')
				assert False
			except ValueError as e:
				assert 'must not contain uppercase letters' in str(e)
		finally:
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_fields_manage_items_by_name(cls):
		root       = cls._new_root()
		class_path = os.path.join(root, 'user')

		try:
			fields = o.disk.Fields(class_path)

			assert dict(fields.items()) == {}
			assert fields.get('name') is None
			assert fields.has('name') == False

			name = fields.set('name')
			age  = fields.set('age')

			assert dict(fields.items()) == {
				'name': name,
				'age' : age,
			}
			assert fields.get('name') is name
			assert fields.get('age') is age
			assert fields.has('name') == True
			assert fields.has('age') == True
			assert os.path.isdir(os.path.join(class_path, '__fields__', 'name'))
			assert os.path.isdir(os.path.join(class_path, '__fields__', 'age'))

			reopened = o.disk.Fields(class_path)

			assert set(dict(reopened.items()).keys()) == {'name', 'age'}
			assert reopened.get('name').name == 'name'
			assert reopened.get('age').name == 'age'
			assert reopened.has('name') == True
			assert reopened.has('age') == True
			assert reopened.get('missing') is None
			assert reopened.has('missing') == False
		finally:
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_subclasses_manage_items_by_name(cls):
		root       = cls._new_root()
		class_path = os.path.join(root, 'user')

		try:
			subclasses = o.disk.Subclasses(class_path)

			assert subclasses.items == {}
			assert subclasses.has('User') == False

			subclasses.set('User')
			subclasses.set('Admin')

			user  = subclasses.get('User')
			admin = subclasses.get('Admin')

			assert subclasses.items == {
				'User' : user,
				'Admin': admin,
			}
			assert isinstance(user, o.disk.Class)
			assert isinstance(admin, o.disk.Class)
			assert user.path == os.path.join(class_path, '__subclasses__', 'User')
			assert admin.path == os.path.join(class_path, '__subclasses__', 'Admin')
			assert subclasses.has('User') == True
			assert subclasses.has('Admin') == True
			assert os.path.isdir(os.path.join(class_path, '__subclasses__'))
			assert os.path.isdir(os.path.join(class_path, '__subclasses__', 'User'))
			assert os.path.isdir(os.path.join(class_path, '__subclasses__', 'Admin'))

			reopened = o.disk.Subclasses(class_path)

			assert reopened.items == {
				'User' : None,
				'Admin': None,
			}
			assert reopened.get('User') is None
			assert reopened.get('Admin') is None
			assert reopened.has('User') == True
			assert reopened.has('Admin') == True
			assert reopened.get('missing') is None
			assert reopened.has('missing') == False

			try:
				subclasses.set('user')
				assert False
			except ValueError as e:
				assert 'must start with a capital letter' in str(e)
		finally:
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_instances_store_index_state(cls):
		root       = cls._new_root()
		class_path = os.path.join(root, 'user')

		try:
			instances = o.disk.Instances(class_path)

			instances.set(4, [3, 1, 0])
			reopened = o.disk.Instances(class_path)

			assert reopened.count == 4
			assert reopened.order == [3, 1, 0]
			assert os.path.isfile(os.path.join(class_path, '__instances__', '__index__'))
		finally:
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_instances_reopen_empty_state(cls):
		root       = cls._new_root()
		class_path = os.path.join(root, 'user')

		try:
			reopened = o.disk.Instances(class_path)

			assert reopened.count == 0
			assert reopened.order == []
		finally:
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_instances_create_uses_incremental_versions(cls):
		root       = cls._new_root()
		class_path = os.path.join(root, 'user')

		try:
			instances = o.disk.Instances(class_path)

			instance_0 = instances.create(o.undefined)
			instance_1 = instances.create(o.undefined)

			assert instance_0.path == os.path.join(class_path, '__instances__', '_0')
			assert instance_1.path == os.path.join(class_path, '__instances__', '_1')
			assert os.path.isdir(os.path.join(class_path, '__instances__', '_0'))
			assert os.path.isdir(os.path.join(class_path, '__instances__', '_1'))

			instances.remove(0)

			instance_2 = instances.create(o.undefined)

			assert instance_2.path == os.path.join(class_path, '__instances__', '_2')

			reopened = o.disk.Instances(class_path)

			assert reopened.count == 3
			assert reopened.order == [1, 2]
			assert os.path.isdir(os.path.join(class_path, '__instances__', '_2'))
		finally:
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_instance_list_creates_list_shape(cls):
		root           = cls._new_root()
		registry_state = cls._patch_registry()
		instance_path  = os.path.join(root, 'user', '__instances__', '_0')

		try:
			instance = o.disk.Instance(instance_path, list[int])

			assert instance.annotation == o.Annotation(list[int])
			assert instance.attributes is not None
			assert instance.list is not o.undefined
			assert hasattr(instance, 'dict') == False
			assert os.path.isdir(instance_path)
			assert os.path.isdir(os.path.join(instance_path, '__attributes__'))
			assert os.path.isfile(os.path.join(instance_path, '__list__'))
			assert os.path.exists(os.path.join(instance_path, '__dict__')) == False
		finally:
			cls._restore_registry(registry_state)
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_instance_dict_creates_dict_shape(cls):
		root           = cls._new_root()
		registry_state = cls._patch_registry()
		instance_path  = os.path.join(root, 'user', '__instances__', '_1')

		try:
			instance = o.disk.Instance(instance_path, dict[str, int])

			assert instance.annotation == o.Annotation(dict[str, int])
			assert instance.attributes is not None
			assert hasattr(instance, 'list') == False
			assert instance.dict is not o.undefined
			assert os.path.isdir(instance_path)
			assert os.path.isdir(os.path.join(instance_path, '__attributes__'))
			assert os.path.isfile(os.path.join(instance_path, '__dict__'))
			assert os.path.exists(os.path.join(instance_path, '__list__')) == False
		finally:
			cls._restore_registry(registry_state)
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_instance_atomic_creates_plain_shape(cls):
		root           = cls._new_root()
		registry_state = cls._patch_registry()
		instance_path  = os.path.join(root, 'user', '__instances__', '_2')

		try:
			instance = o.disk.Instance(instance_path, int)

			assert instance.annotation == o.Annotation(int)
			assert instance.attributes is not None
			assert hasattr(instance, 'list') == False
			assert hasattr(instance, 'dict') == False
			assert instance.atomic is not o.undefined
			assert os.path.isdir(instance_path)
			assert os.path.isdir(os.path.join(instance_path, '__attributes__'))
			assert os.path.exists(os.path.join(instance_path, '__list__')) == False
			assert os.path.exists(os.path.join(instance_path, '__dict__')) == False
		finally:
			cls._restore_registry(registry_state)
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_instance_none_annotation_reopens_list_shape(cls):
		root           = cls._new_root()
		registry_state = cls._patch_registry()
		instance_path  = os.path.join(root, 'user', '__instances__', '_2')

		try:
			os.makedirs(instance_path, exist_ok=True)
			o.disk.List(instance_path)

			instance = o.disk.Instance(instance_path)

			assert instance.attributes is not None
			assert instance.list is not o.undefined
			assert hasattr(instance, 'dict') == False
		finally:
			cls._restore_registry(registry_state)
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_instance_none_annotation_reopens_dict_shape(cls):
		root           = cls._new_root()
		registry_state = cls._patch_registry()
		instance_path  = os.path.join(root, 'user', '__instances__', '_2')

		try:
			os.makedirs(instance_path, exist_ok=True)
			o.disk.Dict(instance_path)

			instance = o.disk.Instance(instance_path)

			assert instance.attributes is not None
			assert hasattr(instance, 'list') == False
			assert instance.dict is not o.undefined
		finally:
			cls._restore_registry(registry_state)
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_instance_none_annotation_reopens_atomic_shape(cls):
		root           = cls._new_root()
		registry_state = cls._patch_registry()
		instance_path  = os.path.join(root, 'user', '__instances__', '_2')

		try:
			os.makedirs(instance_path, exist_ok=True)
			atomic = o.disk.Atomic(instance_path)
			atomic.set(b'33')

			instance = o.disk.Instance(instance_path)

			assert instance.attributes is not None
			assert hasattr(instance, 'list') == False
			assert hasattr(instance, 'dict') == False
			assert instance.atomic is not o.undefined
		finally:
			cls._restore_registry(registry_state)
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_attributes_persist_pairs(cls):
		root          = cls._new_root()
		instance_path = os.path.join(root, 'user', '__instances__', '_3')

		try:
			os.makedirs(instance_path, exist_ok=True)

			attributes = o.disk.Attributes(instance_path)

			assert attributes.get('age') is None
			assert attributes.has('age') == False

			attributes.set('age', 33)
			attributes.set('name', 77)

			reopened = o.disk.Attributes(instance_path)

			assert reopened.items == {
				'age' : None,
				'name': None,
			}
			assert reopened.has('age') == True
			assert reopened.has('name') == True
			assert reopened.get('age') == 33
			assert reopened.get('name') == 77
			assert reopened.items == {
				'age' : 33,
				'name': 77,
			}
			assert os.path.isdir(os.path.join(instance_path, '__attributes__'))
			assert os.path.isfile(os.path.join(instance_path, '__attributes__', 'age'))
			assert os.path.isfile(os.path.join(instance_path, '__attributes__', 'name'))
		finally:
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_atomic_persists_value(cls):
		root          = cls._new_root()
		instance_path = os.path.join(root, 'user', '__instances__', '_3')

		try:
			os.makedirs(instance_path, exist_ok=True)

			atomic = o.disk.Atomic(instance_path)

			assert atomic.get() is o.undefined

			atomic.set(b'33')

			reopened = o.disk.Atomic(instance_path)

			assert reopened.get() == b'33'
			assert os.path.isfile(os.path.join(instance_path, '__value__'))
		finally:
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_persists_items(cls):
		root          = cls._new_root()
		instance_path = os.path.join(root, 'user', '__instances__', '_3')

		try:
			os.makedirs(instance_path, exist_ok=True)

			items = o.disk.List(instance_path)
			items.items = [10, 11, 12]

			reopened = o.disk.List(instance_path)

			assert reopened.items == [10, 11, 12]
			assert reopened.get(0) == 10
			assert reopened.get(1) == 11
			assert reopened.get(3) is None
			assert os.path.isfile(os.path.join(instance_path, '__list__'))
		finally:
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_overwrite_rewrites_full_state(cls):
		root          = cls._new_root()
		instance_path = os.path.join(root, 'user', '__instances__', '_3')

		try:
			os.makedirs(instance_path, exist_ok=True)

			items = o.disk.List(instance_path)
			items.items = [10, 11, 12]
			items.items = [99]

			reopened = o.disk.List(instance_path)

			assert reopened.items == [99]
		finally:
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_reopen_empty_state(cls):
		root          = cls._new_root()
		instance_path = os.path.join(root, 'user', '__instances__', '_3')

		try:
			os.makedirs(instance_path, exist_ok=True)

			reopened = o.disk.List(instance_path)

			assert reopened.items == []
		finally:
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_persists_items(cls):
		root          = cls._new_root()
		instance_path = os.path.join(root, 'user', '__instances__', '_4')

		try:
			os.makedirs(instance_path, exist_ok=True)

			items = o.disk.Dict(instance_path)
			items.items = {
				11: 101,
				22: 202,
			}

			reopened = o.disk.Dict(instance_path)

			assert reopened.items == {
				11: 101,
				22: 202,
			}
			assert reopened.get(11) == 101
			assert reopened.get(22) == 202
			assert reopened.get(33) is o.undefined
			assert os.path.isfile(os.path.join(instance_path, '__dict__'))
		finally:
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_overwrite_rewrites_full_state(cls):
		root          = cls._new_root()
		instance_path = os.path.join(root, 'user', '__instances__', '_4')

		try:
			os.makedirs(instance_path, exist_ok=True)

			items = o.disk.Dict(instance_path)
			items.items = {
				11: 101,
				22: 202,
			}
			items.items = {
				33: 303,
			}

			reopened = o.disk.Dict(instance_path)

			assert reopened.items == {
				33: 303,
			}
		finally:
			shutil.rmtree(root)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_reopen_empty_state(cls):
		root          = cls._new_root()
		instance_path = os.path.join(root, 'user', '__instances__', '_4')

		try:
			os.makedirs(instance_path, exist_ok=True)

			reopened = o.disk.Dict(instance_path)

			assert reopened.items == {}
		finally:
			shutil.rmtree(root)


if __name__ == '__main__':
	if len(sys.argv) > 1:
		getattr(TestDisk, sys.argv[1])()
		print(f'✅ {sys.argv[1]}')
	else:
		TestDisk.run()
