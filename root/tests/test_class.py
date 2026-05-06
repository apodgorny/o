import os
import shutil
import sys

import o

UNDEFINED = o.Undefined


class TestClass(o.Tester):
	RUNTIME_PREFIX = 'o_class_'

	# ----------------------------------------------------------------------
	@classmethod
	def _patch_runtime(cls):
		runtime_state  = o.Tester._patch_store(cls.RUNTIME_PREFIX)
		temp_root      = runtime_state['temp_root']
		source_root    = os.path.join(o.__path__, 'tests_runtime')
		root           = runtime_state['root']
		registry_state = o.Tester._patch_registry()

		os.makedirs(source_root, exist_ok=True)

		state          = {
			'root'          : root,
			'temp_root'     : temp_root,
			'source_root'   : source_root,
			'registry'      : registry_state,
			'runtime'       : runtime_state,
			'entities'      : dict(o.__entities__),
			'cast_map'      : dict(o.__cast_map__),
			'modules'       : [],
			'paths'         : [],
		}

		return state

	# ----------------------------------------------------------------------
	@classmethod
	def _restore_runtime(cls, state):
		o.__entities__.clear()
		o.__entities__.update(state['entities'])

		o.__cast_map__.clear()
		o.__cast_map__.update(state['cast_map'])

		for module_name in state['modules']:
			if module_name in sys.modules:
				del sys.modules[module_name]

		for path in state['paths']:
			if os.path.exists(path):
				os.remove(path)

		o.Tester._restore_store(state['runtime'])
		o.Tester._restore_registry(state['registry'])

		if os.path.isdir(state['source_root']):
			shutil.rmtree(state['source_root'])

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

			name_field = FieldDefinitionFromSource._.name
			age_field  = FieldDefinitionFromSource._.age

			assert name_field is not None
			assert age_field is not None
			assert name_field.type is o.Str
			assert age_field.type is o.Int
			assert age_field.default == 7
			assert age_field.description == 'Age'
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
			assert o.services.Memory.get(f'{FieldPropsGetterAndSetter.__proto__}._.age.label') == 'Years'

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
			class_name = f'SourceDefinitionIsAuthoritative_{os.path.basename(state["root"])}'

			SourceDefinitionIsAuthoritative = o.T.extend(
				class_name,
				name=str,
				age=o.F(int, default=7, description='Age')
			)

			assert SourceDefinitionIsAuthoritative._.name.type is o.Str
			assert SourceDefinitionIsAuthoritative._.age.type is o.Int

			try:
				o.T.extend(class_name, name=o.F(str, description='Name'))
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
			class_name = f'ClassAnnotationCycle_{os.path.basename(state["root"])}'
			ClassAnnotationCycle = o.T.extend(class_name, list[str])

			base = ClassAnnotationCycle.__bases__[0]

			assert ClassAnnotationCycle.__annotation__ == o.Annotation(list[str])
			assert ClassAnnotationCycle.__dict__.get('__annotation__', UNDEFINED) is UNDEFINED
			assert base.__annotation__ == o.Annotation(list[str])
			assert base.__annotation__.annotation == list[str]

			del o.__entities__[ClassAnnotationCycle.id]
			reopened = getattr(base, class_name)

			assert reopened.__proto__ == ClassAnnotationCycle.__proto__
			assert reopened.__annotation__ == o.Annotation(list[str])
			assert reopened.__dict__.get('__annotation__', UNDEFINED) is UNDEFINED
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_user_class_inherits_annotation_without_owning(cls):
		state = cls._patch_runtime()

		try:
			class_name = f'UserClassInheritsAnnotation_{os.path.basename(state["root"])}'
			UserClassInheritsAnnotation = o.T.extend(class_name, list[str])

			base = UserClassInheritsAnnotation.__bases__[0]

			assert UserClassInheritsAnnotation.__annotation__ == o.Annotation(list[str])
			assert UserClassInheritsAnnotation.__dict__.get('__annotation__', UNDEFINED) is UNDEFINED
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
			root_name              = os.path.basename(state['root'])
			EmbodiedGenericBaseOne = o.T.extend(f'EmbodiedGenericBaseOne_{root_name}', dict[str, int])
			EmbodiedGenericBaseTwo = o.T.extend(f'EmbodiedGenericBaseTwo_{root_name}', dict[str, int])

			assert EmbodiedGenericBaseOne.__bases__[0] is EmbodiedGenericBaseTwo.__bases__[0]
			assert EmbodiedGenericBaseOne.__bases__[0].__name__.startswith('Generic')
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_only_annotation_law(cls):
		state = cls._patch_runtime()

		try:
			root_name            = os.path.basename(state['root'])
			RootOnlyAnnotationOk = o.T.extend(f'RootOnlyAnnotationOk_{root_name}', list[int])

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
			class_name   = f'FieldTypeLaw_{os.path.basename(state["root"])}'
			FieldTypeLaw = o.T.extend(class_name, data=dict[str, int])

			field    = FieldTypeLaw._.data
			type_cls = field.type

			assert field.annotation == o.Annotation(dict[str, int])
			assert type_cls.__annotation__ == o.Annotation(dict[str, int])
			assert FieldTypeLaw.__annotations__['data'] == type_cls.__annotation__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_materialization_through_getattr(cls):
		state = cls._patch_runtime()

		try:
			class_name = f'MaterializationThroughGetattr_{os.path.basename(state["root"])}'
			MaterializationThroughGetattr = o.T.extend(
				class_name,
				age=o.F(int, default=7, description='Age')
			)

			entity_id = MaterializationThroughGetattr.id

			del o.__entities__[entity_id]
			reopened = getattr(o.T, class_name)

			assert reopened.id == entity_id
			assert reopened.__proto__ == f'o.T.{class_name}'
			assert reopened._.age.type is o.Int
			assert reopened.age == 7
			assert reopened.__annotations__['age'] == o.Int.__annotation__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_extend_path(cls):
		state = cls._patch_runtime()

		try:
			fields_name     = f'ExtendedFieldsPath_{os.path.basename(state["root"])}'
			list_name       = f'ExtendedListPath_{os.path.basename(state["root"])}'
			extended_fields = o.T.extend(fields_name, name=str)
			extended_list   = o.T.extend(list_name, list[str])

			assert extended_fields.__proto__ == f'o.T.{fields_name}'
			assert extended_fields._.name.type is o.Str
			assert extended_list.__annotation__ == o.Annotation(list[str])

			try:
				o.T.extend(fields_name, age=int)
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
			root_name                    = os.path.basename(state['root'])
			CastMapAndEmbodimentReuseOne = o.T.extend(f'CastMapAndEmbodimentReuseOne_{root_name}', list[dict[str, int]])
			CastMapAndEmbodimentReuseTwo = o.T.extend(f'CastMapAndEmbodimentReuseTwo_{root_name}', list[dict[str, int]])

			assert o.__cast_map__[int] == o.Int.__proto__
			assert o.__cast_map__[str] == o.Str.__proto__
			assert CastMapAndEmbodimentReuseOne.__bases__[0] is CastMapAndEmbodimentReuseTwo.__bases__[0]
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_exists_aligns_with_class_room(cls):
		state = cls._patch_runtime()

		try:
			class_name                = f'ExistsAlignsWithClassRoom_{os.path.basename(state["root"])}'
			ExistsAlignsWithClassRoom = o.T.extend(class_name)

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
			assert o.get_route(SourceBackedClassPersistsOModule.__route__)['proto'] == SourceBackedClassPersistsOModule.__proto__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_runtime_defined_class_has_no_route(cls):
		state = cls._patch_runtime()

		try:
			root_name                       = os.path.basename(state['root'])
			class_name                      = f'RuntimeDefinedClassHasNoOModule_{root_name}'
			RuntimeDefinedClassHasNoOModule = o.T.extend(class_name)

			assert RuntimeDefinedClassHasNoOModule.__route__ is UNDEFINED
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
					'\titems: list\n'
					'\tmeta: dict\n'
				)
			)

			x = SourceBackedRestoresFormAndValuesAfterReload(
				name='alex',
				items=[1, 2],
				meta={'lang': 'uk'},
			)

			class_id = SourceBackedRestoresFormAndValuesAfterReload.id
			id       = x.id

			for entity_id in [class_id, id]:
				if entity_id in o.__entities__:
					del o.__entities__[entity_id]

			if module_key in sys.modules:
				del sys.modules[module_key]

			reopened = o.get(id)

			assert reopened.__class__.__proto__ == f'o.T.{class_name}'
			assert o.get_route(reopened.__class__.__route__)['proto'] == reopened.__class__.__proto__
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
			root_name  = os.path.basename(state['root'])
			class_name = f'RuntimeDefinedRestoresFormAndValuesAfterReload_{root_name}'
			RuntimeDefinedRestoresFormAndValuesAfterReload = o.T.extend(
				class_name,
				name=str,
				items=list,
				meta=dict,
			)

			x = RuntimeDefinedRestoresFormAndValuesAfterReload(
				name='alex',
				items=[1, 2],
				meta={'lang': 'uk'},
			)

			class_id = RuntimeDefinedRestoresFormAndValuesAfterReload.id
			id       = x.id

			for entity_id in [class_id, id]:
				if entity_id in o.__entities__:
					del o.__entities__[entity_id]

			reopened = o.get(id)

			assert reopened.__class__.__proto__ == f'o.T.{class_name}'
			assert reopened.__class__.__route__ is UNDEFINED
			assert reopened.name == 'alex'
			assert list(reopened.items) == [1, 2]
			assert dict(reopened.meta.items()) == {'lang': 'uk'}
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_description_is_seen_by_subclass_and_persists_after_reload(cls):
		state = cls._patch_runtime()

		try:
			root_name                          = os.path.basename(state['root'])
			class_name                         = f'RootDescriptionPersistsAfterReload_{root_name}'
			RootDescriptionPersistsAfterReload = o.T.extend(class_name)
			class_value                        = o.T.description
			x                                  = RootDescriptionPersistsAfterReload()
			instance_value                     = f'instance:{root_name}'
			class_id                           = RootDescriptionPersistsAfterReload.id
			class_proto                        = RootDescriptionPersistsAfterReload.__proto__
			id                                 = x.id
			proto                              = x.__proto__

			assert RootDescriptionPersistsAfterReload.description == class_value
			assert x.description == class_value

			x.description = instance_value

			assert x.description == instance_value
			assert o.services.Memory.get(f'{proto}.description', UNDEFINED) is not UNDEFINED

			for key in [class_id, class_proto, id, proto]:
				if key in o.__entities__:
					del o.__entities__[key]

			reopened = o.get(id)

			assert reopened.__class__.__proto__ == class_proto
			assert reopened.__class__.description == class_value
			assert reopened.description == instance_value
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_field_added_later_persists_across_reload_for_class_and_instances(cls):
		state = cls._patch_runtime()

		try:
			root_name    = os.path.basename(state['root'])
			class_name   = f'FieldAddedLaterPersists_{root_name}'
			field_name   = 'tag'
			field_value  = 'late default'
			before_value = 'before reload'
			after_value  = 'after reload'

			FieldAddedLaterPersists = o.T.extend(class_name)
			FieldAddedLaterPersists.tag = o.F(str, default=field_value)
			x_before                     = FieldAddedLaterPersists()
			x_before_id                  = x_before.id
			x_before_proto               = x_before.__proto__

			x_before.tag = before_value

			assert FieldAddedLaterPersists.tag == field_value
			assert x_before.tag == before_value

			class_id    = FieldAddedLaterPersists.id
			class_proto = FieldAddedLaterPersists.__proto__

			for key in [class_id, class_proto, x_before_id, x_before_proto]:
				if key in o.__entities__:
					del o.__entities__[key]

			ReloadedClass = o.get(class_id)
			x_before      = o.get(x_before_id)

			assert ReloadedClass.tag == field_value
			assert x_before.tag == before_value

			x_after       = ReloadedClass()
			x_after_id    = x_after.id
			x_after_proto = x_after.__proto__

			x_after.tag = after_value

			assert x_after.tag == after_value

			for key in [x_after_id, x_after_proto]:
				if key in o.__entities__:
					del o.__entities__[key]

			x_after = o.get(x_after_id)

			assert x_after.tag == after_value
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
			child_name   = f'RuntimeChild_{os.path.basename(state["root"])}'
			RuntimeChild = SourceParentRuntimeChild.extend(child_name)

			assert RuntimeChild.__bases__[0] is SourceParentRuntimeChild
			assert o.get_route(SourceParentRuntimeChild.__route__)['proto'] == SourceParentRuntimeChild.__proto__
			assert RuntimeChild.__route__ is UNDEFINED
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_runtime_parent_source_child_chain(cls):
		state = cls._patch_runtime()

		try:
			root_name                = os.path.basename(state['root'])
			parent_name              = f'RuntimeParentSourceChild_{root_name}'
			RuntimeParentSourceChild = o.T.extend(parent_name)
			LoadedChild              = cls._source_class(
				state,
				'LoadedChild',
				(
					'import o\n\n'
					f'class LoadedChild(o.T.{parent_name}):\n'
					'\tpass\n'
				)
			)

			assert RuntimeParentSourceChild in LoadedChild.__mro__[1:]
			assert RuntimeParentSourceChild.__route__ is UNDEFINED
			assert o.get_route(LoadedChild.__route__)['proto'] == LoadedChild.__proto__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_nested_subclass_proto_chain_materialization(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			outer_name = f'NestedSubclassProtoChainMaterialization_{root_name}'
			inner_name = f'Inner_{root_name}'
			NestedSubclassProtoChainMaterialization = o.T.extend(outer_name)
			Inner = NestedSubclassProtoChainMaterialization.extend(inner_name)

			outer_id = NestedSubclassProtoChainMaterialization.id
			inner_id = Inner.id

			del o.__entities__[outer_id]
			del o.__entities__[inner_id]

			reopened = getattr(getattr(o.T, outer_name), inner_name)

			assert reopened.id == inner_id
			assert reopened.__proto__ == f'o.T.{outer_name}.{inner_name}'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_root_parent_is_none(cls):
		state = cls._patch_runtime()

		try:
			assert o.T.__parent__ is None
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_runtime_child_parent_is_public_base(cls):
		state = cls._patch_runtime()

		try:
			root_name                    = os.path.basename(state['root'])
			parent_name                  = f'RuntimeChildParentIsPublicBase_{root_name}'
			child_name                   = f'Inner_{root_name}'
			RuntimeChildParentIsPublicBase = o.T.extend(parent_name)
			Inner                        = RuntimeChildParentIsPublicBase.extend(child_name)

			assert RuntimeChildParentIsPublicBase.__parent__ is o.T
			assert Inner.__parent__ is RuntimeChildParentIsPublicBase
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_raw_source_child_parent_is_public_base(cls):
		state = cls._patch_runtime()

		try:
			RawSourceChildParentIsPublicBase = cls._source_class(
				state,
				'RawSourceChildParentIsPublicBase',
				(
					'import o\n\n'
					'class RawSourceChildParentIsPublicBase(o.T):\n'
					'\tpass\n'
				)
			)
			RawSourceGrandchildParentIsPublicBase = cls._source_class(
				state,
				'RawSourceGrandchildParentIsPublicBase',
				(
					'import o\n\n'
					'class RawSourceGrandchildParentIsPublicBase(o.T.RawSourceChildParentIsPublicBase):\n'
					'\tpass\n'
				)
			)
			parent_module_key = os.path.realpath(
				os.path.join(state['source_root'], 'raw_source_child_parent_is_public_base.py')
			)
			module_key = os.path.realpath(
				os.path.join(state['source_root'], 'raw_source_grandchild_parent_is_public_base.py')
			)
			raw_parent = getattr(sys.modules[parent_module_key], 'RawSourceChildParentIsPublicBase')
			raw_child = getattr(sys.modules[module_key], 'RawSourceGrandchildParentIsPublicBase')

			assert raw_parent.__parent__ is o.T
			assert raw_child.__parent__ is RawSourceChildParentIsPublicBase
			assert RawSourceChildParentIsPublicBase in RawSourceGrandchildParentIsPublicBase.__mro__[1:]
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_public_source_parent_is_public_base(cls):
		state = cls._patch_runtime()

		try:
			PublicSourceParentIsPublicBase = cls._source_class(
				state,
				'PublicSourceParentIsPublicBase',
				(
					'import o\n\n'
					'class PublicSourceParentIsPublicBase(o.T):\n'
					'\tpass\n'
				)
			)

			assert PublicSourceParentIsPublicBase.__parent__ is o.T
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_public_source_child_parent_is_public_parent(cls):
		state = cls._patch_runtime()

		try:
			PublicSourceChildParentIsPublicParent = cls._source_class(
				state,
				'PublicSourceChildParentIsPublicParent',
				(
					'import o\n\n'
					'class PublicSourceChildParentIsPublicParent(o.T):\n'
					'\tpass\n'
				)
			)
			PublicSourceGrandchildParentIsPublicParent = cls._source_class(
				state,
				'PublicSourceGrandchildParentIsPublicParent',
				(
					'import o\n\n'
					'class PublicSourceGrandchildParentIsPublicParent(o.T.PublicSourceChildParentIsPublicParent):\n'
					'\tpass\n'
				)
			)

			assert PublicSourceGrandchildParentIsPublicParent.__parent__ is PublicSourceChildParentIsPublicParent
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_extend_with_annotation_and_fields(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			extended  = o.T.extend(f'ExtendWithAnnotationAndFields_{root_name}', list[str], title=str)

			assert extended.__annotation__ == o.Annotation(list[str])
			assert extended._.title.type is o.Str
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_class_has_zone_and_accessor_reuses_it(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			ClassWithZone = o.T.extend(f'ClassWithZone_{root_name}', name=str)

			assert ClassWithZone.__zone__.prefix == f'{ClassWithZone.__proto__}.'
			assert ClassWithZone._.zone is ClassWithZone.__zone__
			assert ClassWithZone.__zone__.get('_.name.type') == o.Str.id
			assert o.services.Memory.get(f'{ClassWithZone.__proto__}._.name.type') == o.Str.id
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_temp_class_can_not_be_subclassed(cls):
		state = cls._patch_runtime()

		try:
			Temp   = o.T.extend()
			raised = False

			try:
				Temp.extend('TempClassCanNotBeSubclassed')
			except TypeError:
				raised = True

			assert raised == True
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestClass.run()
