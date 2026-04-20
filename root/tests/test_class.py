import os
import shutil
import sys
import tempfile

import o


class TestClass(o.Test):

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
			return state['paths'].get(id, o.Undefined)

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
		source_root    = os.path.join(o.__path__, 'tests_runtime')
		root           = None
		registry_state = cls._patch_registry()

		os.makedirs(temp_root, exist_ok=True)
		os.makedirs(source_root, exist_ok=True)
		root = tempfile.mkdtemp(prefix='o_class_', dir=temp_root)

		state          = {
			'root'          : root,
			'temp_root'     : temp_root,
			'source_root'   : source_root,
			'registry'      : registry_state,
			'data_dir'      : o.DATA_DIR,
			'entities'      : dict(o.__entities__),
			'disk_classes'  : dict(o.__disk_classes__),
			'cast_map'      : dict(o.__cast_map__),
			'modules'       : [],
			'paths'         : [],
		}

		o.DATA_DIR = os.path.join('__tmp__', os.path.basename(root))

		return state

	# ----------------------------------------------------------------------
	@classmethod
	def _restore_runtime(cls, state):
		o.DATA_DIR = state['data_dir']

		o.__entities__.clear()
		o.__entities__.update(state['entities'])

		o.__disk_classes__.clear()
		o.__disk_classes__.update(state['disk_classes'])

		o.__cast_map__.clear()
		o.__cast_map__.update(state['cast_map'])

		for module_name in state['modules']:
			if module_name in sys.modules:
				del sys.modules[module_name]

		for path in state['paths']:
			if os.path.exists(path):
				os.remove(path)

		cls._restore_registry(state['registry'])
		shutil.rmtree(state['root'])

		if os.path.isdir(state['source_root']):
			shutil.rmtree(state['source_root'])

		if os.path.isdir(state['temp_root']):
			shutil.rmtree(state['temp_root'])

	# ----------------------------------------------------------------------
	@classmethod
	def _source_class(cls, state, class_name, source):
		file_name  = o.String.camel_to_snake(class_name) + '.py'
		path       = os.path.join(state['source_root'], file_name)
		module_key = os.path.realpath(path)
		result     = None

		with open(path, 'w') as file:
			file.write(source)

		state['paths'].append(path)
		state['modules'].append(module_key)
		result = getattr(o.tests_runtime, class_name)

		return result

	# ----------------------------------------------------------------------
	@classmethod
	def test_ordinary_class_namespace_survives(cls):
		state = cls._patch_runtime()

		try:
			OrdinaryClassNamespace = cls._source_class(
				state,
				'OrdinaryClassNamespace',
				(
					'import o\n\n'
					'class OrdinaryClassNamespace(o.T):\n'
					'\tname: str\n'
					'\t_hidden = 7\n\n'
					'\tdef ping(self):\n'
					'\t\treturn \'pong\'\n'
				)
			)

			assert OrdinaryClassNamespace._hidden == 7
			assert 'ping' in OrdinaryClassNamespace.__dict__
			assert callable(OrdinaryClassNamespace.ping)
			assert hasattr(OrdinaryClassNamespace, '_')
			assert 'name' not in OrdinaryClassNamespace.__dict__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_direct_runtime_class_definition_raises(cls):
		state = cls._patch_runtime()

		try:
			try:
				class DirectRuntimeClassDefinitionRaises(o.T):
					pass

				assert False
			except TypeError as e:
				assert 'loaded from o.Module' in str(e)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_field_definition_from_source(cls):
		state = cls._patch_runtime()

		try:
			FieldDefinitionFromSource = cls._source_class(
				state,
				'FieldDefinitionFromSource',
				(
					'import o\n\n'
					'class FieldDefinitionFromSource(o.T):\n'
					'\tname: str\n'
					'\tage = o.F(int, default=7, description=\'Age\')\n'
				)
			)

			name_field = FieldDefinitionFromSource.__disk_class__.fields.get('name')
			age_field  = FieldDefinitionFromSource.__disk_class__.fields.get('age')

			assert name_field is not None
			assert age_field is not None
			assert name_field.get('type') == o.Str.id
			assert age_field.get('type') == o.Int.id
			assert age_field.get('default') == 7
			assert age_field.get('description') == 'Age'
			assert FieldDefinitionFromSource.age == 7
			assert FieldDefinitionFromSource.__annotations__['name'] == o.Str.__annotation__
			assert FieldDefinitionFromSource.__annotations__['age'] == o.Int.__annotation__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_field_props_getter_and_setter(cls):
		state = cls._patch_runtime()

		try:
			FieldPropsGetterAndSetter = cls._source_class(
				state,
				'FieldPropsGetterAndSetter',
				(
					'import o\n\n'
					'class FieldPropsGetterAndSetter(o.T):\n'
					'\tage = o.F(int, default=7, description=\'Age\')\n'
				)
			)

			assert FieldPropsGetterAndSetter._.age.description == 'Age'

			FieldPropsGetterAndSetter._.age.label = 'Years'

			assert FieldPropsGetterAndSetter._.age.label == 'Years'
			assert FieldPropsGetterAndSetter.__disk_class__.fields.get('age').get('label') == 'Years'

			entity_id = FieldPropsGetterAndSetter.id

			del o.__entities__[entity_id]

			reopened = o.T.FieldPropsGetterAndSetter

			assert reopened._.age.label == 'Years'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_source_definition_is_authoritative(cls):
		state = cls._patch_runtime()

		try:
			SourceDefinitionIsAuthoritative = o.T.extend(
				'SourceDefinitionIsAuthoritative',
				name=str,
				age=o.F(int, default=7, description='Age')
			)

			first_path = SourceDefinitionIsAuthoritative.__disk_class__.path
			assert os.path.isdir(os.path.join(first_path, '__fields__', 'name'))
			assert os.path.isdir(os.path.join(first_path, '__fields__', 'age'))

			try:
				o.T.extend('SourceDefinitionIsAuthoritative', name=o.F(str, description='Name'))
				assert False
			except TypeError as e:
				assert 'already exists' in str(e)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_class_annotation_cycle(cls):
		state = cls._patch_runtime()

		try:
			ClassAnnotationCycle = o.T.extend('ClassAnnotationCycle', list[str])

			base = ClassAnnotationCycle.__bases__[0]

			assert ClassAnnotationCycle.__annotation__ == o.Annotation(list[str])
			assert ClassAnnotationCycle.__dict__.get('__annotation__', o.Undefined) is o.Undefined
			assert ClassAnnotationCycle.__disk_class__.annotation is o.Undefined
			assert base.__annotation__ == o.Annotation(list[str])
			assert base.__disk_class__.annotation.annotation == list[str]

			del o.__entities__[ClassAnnotationCycle.id]
			reopened = base.ClassAnnotationCycle

			assert reopened.__proto__ == ClassAnnotationCycle.__proto__
			assert reopened.__annotation__ == o.Annotation(list[str])
			assert reopened.__dict__.get('__annotation__', o.Undefined) is o.Undefined
			assert reopened.__disk_class__.annotation is o.Undefined
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_user_class_inherits_annotation_without_owning(cls):
		state = cls._patch_runtime()

		try:
			UserClassInheritsAnnotation = o.T.extend('UserClassInheritsAnnotation', list[str])

			base = UserClassInheritsAnnotation.__bases__[0]

			assert UserClassInheritsAnnotation.__annotation__ == o.Annotation(list[str])
			assert UserClassInheritsAnnotation.__dict__.get('__annotation__', o.Undefined) is o.Undefined
			assert UserClassInheritsAnnotation.__disk_class__.annotation is o.Undefined
			assert base.__annotation__ == o.Annotation(list[str])
			assert base.__dict__['__annotation__'] == o.Annotation(list[str])
			assert str(base.__annotation__.annotation) == 'list[str]'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_embodied_generic_base(cls):
		state = cls._patch_runtime()

		try:
			EmbodiedGenericBaseOne = o.T.extend('EmbodiedGenericBaseOne', dict[str, int])
			EmbodiedGenericBaseTwo = o.T.extend('EmbodiedGenericBaseTwo', dict[str, int])

			assert EmbodiedGenericBaseOne.__bases__[0] is EmbodiedGenericBaseTwo.__bases__[0]
			assert EmbodiedGenericBaseOne.__bases__[0].__name__.startswith('Generic')
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_only_annotation_law(cls):
		state = cls._patch_runtime()

		try:
			RootOnlyAnnotationOk = o.T.extend('RootOnlyAnnotationOk', list[int])

			assert RootOnlyAnnotationOk.__annotation__ == o.Annotation(list[int])

			try:
				RootOnlyAnnotationOk.extend('RootOnlyAnnotationBad', dict[str, int])
				assert False
			except TypeError as e:
				assert 'Only o.T can accept annotation as second base class' in str(e)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_field_type_law(cls):
		state = cls._patch_runtime()

		try:
			FieldTypeLaw = o.T.extend('FieldTypeLaw', payload=dict[str, int])

			disk_field = FieldTypeLaw.__disk_class__.fields.get('payload')
			type_id    = disk_field.get('type')
			type_cls   = o.get(type_id)

			assert disk_field.has('annotation') == False
			assert type_cls.__annotation__ == o.Annotation(dict[str, int])
			assert FieldTypeLaw.__annotations__['payload'] == type_cls.__annotation__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_materialization_through_getattr(cls):
		state = cls._patch_runtime()

		try:
			MaterializationThroughGetattr = o.T.extend(
				'MaterializationThroughGetattr',
				age=o.F(int, default=7, description='Age')
			)

			entity_id = MaterializationThroughGetattr.id

			del o.__entities__[entity_id]
			reopened = o.T.MaterializationThroughGetattr

			assert reopened.id == entity_id
			assert reopened.__proto__ == 'o.T.MaterializationThroughGetattr'
			assert reopened.__disk_class__.fields.has('age') == True
			assert reopened.age == 7
			assert reopened.__annotations__['age'] == o.Int.__annotation__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_extend_path(cls):
		state = cls._patch_runtime()

		try:
			extended_fields = o.T.extend('ExtendedFieldsPath', name=str)
			extended_list   = o.T.extend('ExtendedListPath', list[str])

			assert extended_fields.__proto__ == 'o.T.ExtendedFieldsPath'
			assert extended_fields.__disk_class__.fields.has('name') == True
			assert extended_fields.__disk_class__.fields.get('name').get('type') == o.Str.id
			assert extended_list.__annotation__ == o.Annotation(list[str])

			try:
				o.T.extend('ExtendedFieldsPath', age=int)
				assert False
			except TypeError as e:
				assert 'already exists' in str(e)
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_cast_map_and_embodiment_reuse(cls):
		state = cls._patch_runtime()

		try:
			CastMapAndEmbodimentReuseOne = o.T.extend('CastMapAndEmbodimentReuseOne', list[dict[str, int]])
			CastMapAndEmbodimentReuseTwo = o.T.extend('CastMapAndEmbodimentReuseTwo', list[dict[str, int]])

			assert o.__cast_map__[int] is o.Int
			assert o.__cast_map__[str] is o.Str
			assert CastMapAndEmbodimentReuseOne.__bases__[0] is CastMapAndEmbodimentReuseTwo.__bases__[0]
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_exists_aligns_with_class_room(cls):
		state = cls._patch_runtime()

		try:
			ExistsAlignsWithClassRoom = o.T.extend('ExistsAlignsWithClassRoom')

			assert o.exists(ExistsAlignsWithClassRoom.__proto__) == True
			assert o.exists(ExistsAlignsWithClassRoom.id) == True
			assert o.exists('o.T.MissingClass') == False
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_get_reconstructs_class_on_cache_miss(cls):
		state = cls._patch_runtime()

		try:
			GetReconstructsClassOnCacheMiss = cls._source_class(
				state,
				'GetReconstructsClassOnCacheMiss',
				(
					'import o\n\n'
					'class GetReconstructsClassOnCacheMiss(o.T):\n'
					'\tage: int = 7\n\n'
					'\tdef ping(self):\n'
					'\t\treturn \'pong\'\n'
				)
			)

			class_id = GetReconstructsClassOnCacheMiss.id
			loaded   = o.get(class_id)

			assert loaded is GetReconstructsClassOnCacheMiss

			del o.__entities__[class_id]

			reopened = o.get(class_id)
			t1       = reopened()

			assert reopened.id == class_id
			assert reopened.__proto__ == 'o.T.GetReconstructsClassOnCacheMiss'
			assert reopened.age == 7
			assert t1.ping() == 'pong'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_source_backed_class_persists_route(cls):
		state = cls._patch_runtime()

		try:
			SourceBackedClassPersistsOModule = cls._source_class(
				state,
				'SourceBackedClassPersistsOModule',
				(
					'import o\n\n'
					'class SourceBackedClassPersistsOModule(o.T):\n'
					'\tpass\n'
				)
			)

			assert SourceBackedClassPersistsOModule.__has_own_module__ == True
			assert SourceBackedClassPersistsOModule.__disk_class__.route == SourceBackedClassPersistsOModule.__route__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_runtime_defined_class_has_no_route(cls):
		state = cls._patch_runtime()

		try:
			RuntimeDefinedClassHasNoOModule = o.T.extend('RuntimeDefinedClassHasNoOModule')

			assert RuntimeDefinedClassHasNoOModule.__disk_class__.route is o.Undefined
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_source_backed_instance_restores_form_and_values_after_reload(cls):
		state = cls._patch_runtime()

		try:
			class_name = 'SourceBackedRestoresFormAndValuesAfterReload'
			file_name  = o.String.camel_to_snake(class_name) + '.py'
			path       = os.path.join(state['source_root'], file_name)
			module_key  = os.path.realpath(path)

			SourceBackedRestoresFormAndValuesAfterReload = cls._source_class(
				state,
				class_name,
				(
					'import o\n\n'
					f'class {class_name}(o.T):\n'
					'\tname: str\n'
				)
			)

			x       = SourceBackedRestoresFormAndValuesAfterReload(name='alex')
			x.items = [1, 2]
			x.meta  = {'lang': 'uk'}

			class_id = SourceBackedRestoresFormAndValuesAfterReload.id
			id       = x.id

			for entity_id in [class_id, id]:
				if entity_id in o.__entities__:
					del o.__entities__[entity_id]

			if module_key in sys.modules:
				del sys.modules[module_key]

			reopened = o.get(id)

			assert reopened.__class__.__proto__ == f'o.T.{class_name}'
			assert reopened.__class__.__disk_class__.route == reopened.__class__.__route__
			assert reopened.name == 'alex'
			assert list(reopened.items) == [1, 2]
			assert dict(reopened.meta.items()) == {'lang': 'uk'}
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_runtime_defined_instance_restores_form_and_values_after_reload(cls):
		state = cls._patch_runtime()

		try:
			RuntimeDefinedRestoresFormAndValuesAfterReload = o.T.extend(
				'RuntimeDefinedRestoresFormAndValuesAfterReload',
				name=str,
			)

			x       = RuntimeDefinedRestoresFormAndValuesAfterReload(name='alex')
			x.items = [1, 2]
			x.meta  = {'lang': 'uk'}

			class_id = RuntimeDefinedRestoresFormAndValuesAfterReload.id
			id       = x.id

			for entity_id in [class_id, id]:
				if entity_id in o.__entities__:
					del o.__entities__[entity_id]

			reopened = o.get(id)

			assert reopened.__class__.__proto__ == 'o.T.RuntimeDefinedRestoresFormAndValuesAfterReload'
			assert reopened.__class__.__disk_class__.route is o.Undefined
			assert reopened.name == 'alex'
			assert list(reopened.items) == [1, 2]
			assert dict(reopened.meta.items()) == {'lang': 'uk'}
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_source_parent_runtime_child_chain(cls):
		state = cls._patch_runtime()

		try:
			SourceParentRuntimeChild = cls._source_class(
				state,
				'SourceParentRuntimeChild',
				(
					'import o\n\n'
					'class SourceParentRuntimeChild(o.T):\n'
					'\tpass\n'
				)
			)
			RuntimeChild = SourceParentRuntimeChild.extend('RuntimeChild')

			assert RuntimeChild.__bases__[0] is SourceParentRuntimeChild
			assert SourceParentRuntimeChild.__disk_class__.route == SourceParentRuntimeChild.__route__
			assert RuntimeChild.__disk_class__.route is o.Undefined
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_runtime_parent_source_child_chain(cls):
		state = cls._patch_runtime()

		try:
			RuntimeParentSourceChild = o.T.extend('RuntimeParentSourceChild')
			LoadedChild              = cls._source_class(
				state,
				'LoadedChild',
				(
					'import o\n\n'
					'class LoadedChild(o.T.RuntimeParentSourceChild):\n'
					'\tpass\n'
				)
			)

			assert LoadedChild.__bases__[0] is RuntimeParentSourceChild
			assert RuntimeParentSourceChild.__disk_class__.route is o.Undefined
			assert LoadedChild.__disk_class__.route == LoadedChild.__route__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_nested_subclass_proto_chain_materialization(cls):
		state = cls._patch_runtime()

		try:
			NestedSubclassProtoChainMaterialization = o.T.extend('NestedSubclassProtoChainMaterialization')
			Inner = NestedSubclassProtoChainMaterialization.extend('Inner')

			outer_id = NestedSubclassProtoChainMaterialization.id
			inner_id = Inner.id

			del o.__entities__[outer_id]
			del o.__entities__[inner_id]

			reopened = o.T.NestedSubclassProtoChainMaterialization.Inner

			assert reopened.id == inner_id
			assert reopened.__proto__ == 'o.T.NestedSubclassProtoChainMaterialization.Inner'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_extend_with_annotation_and_fields(cls):
		state = cls._patch_runtime()

		try:
			extended = o.T.extend('ExtendWithAnnotationAndFields', list[str], title=str)

			assert extended.__annotation__ == o.Annotation(list[str])
			assert extended.__disk_class__.fields.has('title') == True
			assert extended.__disk_class__.fields.get('title').get('type') == o.Str.id
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestClass.run()
