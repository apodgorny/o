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
	def test_delattr_removes_runtime_field_from_class(cls):
		state = cls._patch_runtime()

		try:
			root_name          = os.path.basename(state['root'])
			FieldDeleteOnClass = o.T.extend(
				f'FieldDeleteOnClass_{root_name}',
				name=o.F(str, description='Name', default=None)
			)

			assert FieldDeleteOnClass.__has_field__('name') == True
			assert FieldDeleteOnClass._.name.description == 'Name'

			delattr(FieldDeleteOnClass, 'name')

			assert FieldDeleteOnClass.__has_field__('name') == False
			assert 'name' not in FieldDeleteOnClass.__annotations__
			assert o.services.Memory.has(f'{FieldDeleteOnClass.__proto__}._.name.type') == False
			assert o.services.Memory.has(f'{FieldDeleteOnClass.__proto__}._.name.description') == False
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_delattr_removes_root_value_ad_hoc_field_from_class(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			field     = f'query_{root_name}'

			o.initialize()
			setattr(o.V, field, 'hello')

			assert o.T.V.__has_field__(field) == True

			delattr(o.T.V, field)

			assert o.T.V.__has_field__(field) == False
			assert o.services.Memory.has(f'{o.T.V.__proto__}._.{field}.type') == False
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
	def test_runtime_class_repr_uses_proto(cls):
		state = cls._patch_runtime()

		try:
			RuntimeClassReprUsesProto = o.T.extend('RuntimeClassReprUsesProto')

			assert repr(RuntimeClassReprUsesProto) == '<class \'o.T.RuntimeClassReprUsesProto\'>'
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
	def test_drop_removes_class_subclasses_and_instances(cls):
		state = cls._patch_runtime()

		try:
			root_name   = os.path.basename(state['root'])
			Parent      = o.T.extend(f'DropParent_{root_name}', name=str)
			Child       = Parent.extend(f'DropChild_{root_name}', age=int)
			parent_inst = Parent(name='alex')
			child_inst  = Child(name='bob', age=7)

			parent_proto    = Parent.__proto__
			child_proto     = Child.__proto__
			parent_inst_proto = parent_inst.__proto__
			child_inst_proto  = child_inst.__proto__
			parent_id       = Parent.id
			child_id        = Child.id
			parent_inst_id  = parent_inst.id
			child_inst_id   = child_inst.id

			assert o.services.Memory.has(parent_proto) == True
			assert o.services.Memory.has(child_proto) == True
			assert o.services.Memory.has(parent_inst_proto) == True
			assert o.services.Memory.has(child_inst_proto) == True

			Parent.drop()

			assert o.services.Memory.has(parent_proto) == False
			assert o.services.Memory.has(child_proto) == False
			assert o.services.Memory.has(parent_inst_proto) == False
			assert o.services.Memory.has(child_inst_proto) == False

			assert o.services.Memory.has(f'{parent_proto}._.name.type') == False
			assert o.services.Memory.has(f'{child_proto}._.age.type') == False
			assert o.services.Memory.has(f'{parent_inst_proto}.name') == False
			assert o.services.Memory.has(f'{child_inst_proto}.age') == False

			assert parent_id not in o.__entities__
			assert child_id not in o.__entities__
			assert parent_inst_id not in o.__entities__
			assert child_inst_id not in o.__entities__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_drop_single_instance_leaves_class_and_siblings(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Owner     = o.T.extend(f'DropOneOwner_{root_name}', name=str)
			one       = Owner(name='one')
			two       = Owner(name='two')

			one_proto = one.__proto__
			two_proto = two.__proto__
			one_id    = one.id

			one.drop()

			assert o.services.Memory.has(one_proto) == False
			assert o.services.Memory.has(f'{one_proto}.name') == False
			assert one_id not in o.__entities__

			assert o.services.Memory.has(Owner.__proto__) == True
			assert o.services.Memory.has(two_proto) == True
			assert o.services.Memory.has(f'{two_proto}.name') == True
			assert two.id in o.__entities__
		finally:
			cls._restore_runtime(state)


	# ----------------------------------------------------------------------
	@classmethod
	def test_instances_iterator_yields_persisted_instances(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Owner     = o.T.extend(f'InstancesIterOwner_{root_name}', name=str)

			assert list(Owner.__instances__()) == []

			a = Owner(name='a')
			b = Owner(name='b')
			c = Owner(name='c')

			ids = {inst.id for inst in Owner.__instances__()}

			assert ids == {a.id, b.id, c.id}

			for inst in Owner.__instances__():
				assert inst.__class__ is Owner
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_instances_iterator_excludes_subclass_instances(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Parent    = o.T.extend(f'InstancesIterParent_{root_name}', name=str)
			Child     = Parent.extend(f'InstancesIterChild_{root_name}', age=int)

			parent_inst = Parent(name='p')
			child_inst  = Child(name='c', age=1)

			parent_ids = {inst.id for inst in Parent.__instances__()}
			child_ids  = {inst.id for inst in Child.__instances__()}

			assert parent_ids == {parent_inst.id}
			assert child_ids == {child_inst.id}
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_drop_cascades_through_grandchild(cls):
		state = cls._patch_runtime()

		try:
			root_name  = os.path.basename(state['root'])
			Grand      = o.T.extend(f'DropGrand_{root_name}', name=str)
			Parent     = Grand.extend(f'DropParent_{root_name}', age=int)
			Child      = Parent.extend(f'DropChild_{root_name}', tag=str)

			g_inst = Grand(name='g')
			p_inst = Parent(name='p', age=1)
			c_inst = Child(name='c', age=2, tag='leaf')

			protos = [
				Grand.__proto__, Parent.__proto__, Child.__proto__,
				g_inst.__proto__, p_inst.__proto__, c_inst.__proto__,
			]
			ids    = [Grand.id, Parent.id, Child.id, g_inst.id, p_inst.id, c_inst.id]

			for proto in protos:
				assert o.services.Memory.has(proto) == True

			Grand.drop()

			for proto in protos:
				assert o.services.Memory.has(proto) == False
			for entity_id in ids:
				assert entity_id not in o.__entities__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_extend_without_name_raises(cls):
		state = cls._patch_runtime()

		try:
			raised = False
			try:
				o.T.extend()
			except TypeError:
				raised = True
			assert raised == True
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_extend_with_drop_is_noop_when_class_absent(cls):
		state = cls._patch_runtime()

		try:
			root_name  = os.path.basename(state['root'])
			class_name = f'ExtendDropAbsent_{root_name}'

			Made = o.T.extend(class_name, __drop__=True, name=str)

			assert Made.__proto__ == f'o.T.{class_name}'
			assert Made.__has_field__('name') == True
			assert o.services.Memory.has(Made.__proto__) == True
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_extend_with_drop_cascades_through_existing_subclasses(cls):
		state = cls._patch_runtime()

		try:
			root_name   = os.path.basename(state['root'])
			parent_name = f'ExtendDropCascadeParent_{root_name}'
			child_name  = f'ExtendDropCascadeChild_{root_name}'

			First      = o.T.extend(parent_name, name=str)
			OldChild   = First.extend(child_name, tag=str)
			first_inst = First(name='one')
			old_child_inst = OldChild(name='two', tag='x')

			old_child_proto      = OldChild.__proto__
			first_inst_proto     = first_inst.__proto__
			old_child_inst_proto = old_child_inst.__proto__

			Second = o.T.extend(parent_name, __drop__=True, age=int)

			assert Second.__has_field__('age') == True
			assert Second.__has_field__('name') == False
			assert o.services.Memory.has(old_child_proto) == False
			assert o.services.Memory.has(first_inst_proto) == False
			assert o.services.Memory.has(old_child_inst_proto) == False
			assert OldChild.id not in o.__entities__
			assert first_inst.id not in o.__entities__
			assert old_child_inst.id not in o.__entities__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_get_shape_hash_is_stable_for_same_inputs(cls):
		state = cls._patch_runtime()

		try:
			h1 = o.TMeta.__get_shape_hash__({'name': str, 'age': int})
			h2 = o.TMeta.__get_shape_hash__({'age': int, 'name': str})
			h3 = o.TMeta.__get_shape_hash__({'name': str})
			h4 = o.TMeta.__get_shape_hash__({'name': o.F(str)})

			assert h1 == h2
			assert h1 != h3
			assert h3 == h4
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_get_shape_hash_differs_when_field_props_differ(cls):
		state = cls._patch_runtime()

		try:
			h_plain  = o.TMeta.__get_shape_hash__({'name': o.F(str)})
			h_desc_a = o.TMeta.__get_shape_hash__({'name': o.F(str, description='alpha')})
			h_desc_b = o.TMeta.__get_shape_hash__({'name': o.F(str, description='beta')})
			h_default = o.TMeta.__get_shape_hash__({'name': o.F(str, default='x')})

			assert h_plain != h_desc_a
			assert h_desc_a != h_desc_b
			assert h_plain != h_default
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_shape_hash_is_persisted_on_class(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			Made      = o.T.extend(f'ShapeHashPersisted_{root_name}', name=str)

			assert Made.__shape_hash__ is not None
			assert Made.__zone__.get('__shape_hash__') == Made.__shape_hash__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_extend_same_shape_reuses_existing_class(cls):
		state = cls._patch_runtime()

		try:
			root_name  = os.path.basename(state['root'])
			class_name = f'ExtendSameShapeReuse_{root_name}'

			First  = o.T.extend(class_name, name=str, age=int)
			Second = o.T.extend(class_name, name=str, age=int)

			assert Second is First
			assert Second.__shape_hash__ == First.__shape_hash__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_extend_different_shape_raises(cls):
		state = cls._patch_runtime()

		try:
			root_name  = os.path.basename(state['root'])
			class_name = f'ExtendDifferentShape_{root_name}'

			o.T.extend(class_name, name=str)

			raised = False
			try:
				o.T.extend(class_name, age=int)
			except TypeError as e:
				raised = True
				assert 'different shape' in str(e)
			assert raised == True
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_extend_different_props_raises(cls):
		state = cls._patch_runtime()

		try:
			root_name  = os.path.basename(state['root'])
			class_name = f'ExtendDifferentProps_{root_name}'

			o.T.extend(class_name, name=o.F(str, description='alpha'))

			raised = False
			try:
				o.T.extend(class_name, name=o.F(str, description='beta'))
			except TypeError:
				raised = True
			assert raised == True
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_shape_hash_survives_reload(cls):
		state = cls._patch_runtime()

		try:
			root_name  = os.path.basename(state['root'])
			class_name = f'ShapeHashReload_{root_name}'

			Original   = o.T.extend(class_name, name=str, age=o.F(int, description='Age'))
			entity_id  = Original.id
			original_h = Original.__shape_hash__

			del o.__entities__[entity_id]

			Reopened = getattr(o.T, class_name)

			assert Reopened.id == entity_id
			assert Reopened.__shape_hash__ == original_h

			Same = o.T.extend(class_name, name=str, age=o.F(int, description='Age'))
			assert Same is Reopened
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_extend_with_drop_replaces_existing_class(cls):
		state = cls._patch_runtime()

		try:
			root_name = os.path.basename(state['root'])
			class_name = f'ExtendWithDrop_{root_name}'

			First      = o.T.extend(class_name, name=str)
			first_inst = First(name='first')
			first_id   = First.id

			raised = False
			try:
				o.T.extend(class_name, age=int)
			except TypeError:
				raised = True
			assert raised == True

			Second = o.T.extend(class_name, __drop__=True, age=int)

			assert Second is not First
			assert Second.id == first_id
			assert Second._.age.type is o.Int
			assert Second.__has_field__('age') == True
			assert Second.__has_field__('name') == False
			assert o.__entities__[first_id] is Second
			assert o.services.Memory.has(first_inst.__proto__) == False
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestClass.run()
