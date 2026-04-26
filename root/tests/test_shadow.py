import os
import shutil
import sys
import tempfile

import o


class TestShadow(o.Tester):

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
		root = tempfile.mkdtemp(prefix='o_shadow_', dir=temp_root)

		state = {
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
	def _source_file_name(cls, class_name):
		file_name = o.String.camel_to_snake(class_name) + '.py'
		return file_name

	# ----------------------------------------------------------------------
	@classmethod
	def _source_path(cls, state, class_name):
		path = os.path.join(state['source_root'], cls._source_file_name(class_name))
		return path

	# ----------------------------------------------------------------------
	@classmethod
	def _source_module_key(cls, state, class_name):
		module_key = os.path.realpath(cls._source_path(state, class_name))
		return module_key

	# ----------------------------------------------------------------------
	@classmethod
	def _source_class(cls, state, class_name, source):
		path       = cls._source_path(state, class_name)
		module_key = cls._source_module_key(state, class_name)
		result     = None

		with open(path, 'w') as file:
			file.write(source)

		state['paths'].append(path)
		state['modules'].append(module_key)
		result = getattr(o.tests_runtime, class_name)

		return result

	# ----------------------------------------------------------------------
	@classmethod
	def _raw_source_class(cls, state, class_name):
		module_key = cls._source_module_key(state, class_name)
		module     = sys.modules[module_key]
		raw_cls    = getattr(module, class_name)

		return raw_cls

	# ----------------------------------------------------------------------
	@classmethod
	def test_source_access_returns_public_shadow_class(cls):
		state = cls._patch_runtime()

		try:
			SourceAccessReturnsPublicShadowClass = cls._source_class(
				state,
				'SourceAccessReturnsPublicShadowClass',
				(
					'import o\n\n'
					'class SourceAccessReturnsPublicShadowClass(o.T):\n'
					'\tpass\n'
				)
			)
			raw_cls = cls._raw_source_class(state, 'SourceAccessReturnsPublicShadowClass')

			assert SourceAccessReturnsPublicShadowClass is not raw_cls
			assert SourceAccessReturnsPublicShadowClass.__bases__[0] is raw_cls
			assert raw_cls.__dict__.get('__proto__', o.Undefined) is o.Undefined
			assert SourceAccessReturnsPublicShadowClass.__proto__ == 'o.T.SourceAccessReturnsPublicShadowClass'
			assert SourceAccessReturnsPublicShadowClass.__module__ == 'o'
			assert SourceAccessReturnsPublicShadowClass.__route__ == 'o.tests_runtime.SourceAccessReturnsPublicShadowClass'
			assert SourceAccessReturnsPublicShadowClass.__has_own_module__ == True
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_shadow_is_idempotent_for_same_source_class(cls):
		state = cls._patch_runtime()

		try:
			ShadowIsIdempotentForSameSourceClass = cls._source_class(
				state,
				'ShadowIsIdempotentForSameSourceClass',
				(
					'import o\n\n'
					'class ShadowIsIdempotentForSameSourceClass(o.T):\n'
					'\tpass\n'
				)
			)
			raw_cls    = cls._raw_source_class(state, 'ShadowIsIdempotentForSameSourceClass')
			shadow_one = raw_cls.__shadow__()
			shadow_two = raw_cls.__shadow__()

			assert shadow_one is ShadowIsIdempotentForSameSourceClass
			assert shadow_two is ShadowIsIdempotentForSameSourceClass
			assert o.__entities__[ShadowIsIdempotentForSameSourceClass.id] is ShadowIsIdempotentForSameSourceClass
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_shadow_preserves_source_namespace_through_inheritance(cls):
		state = cls._patch_runtime()

		try:
			ShadowPreservesSourceNamespaceThroughInheritance = cls._source_class(
				state,
				'ShadowPreservesSourceNamespaceThroughInheritance',
				(
					'import o\n\n'
					'class ShadowPreservesSourceNamespaceThroughInheritance(o.T):\n'
					'\t_hidden = 7\n\n'
					'\tdef ping(self):\n'
					'\t\treturn \'pong\'\n'
				)
			)
			x = ShadowPreservesSourceNamespaceThroughInheritance()

			assert ShadowPreservesSourceNamespaceThroughInheritance._hidden == 7
			assert x.ping() == 'pong'
			assert '_hidden' not in ShadowPreservesSourceNamespaceThroughInheritance.__dict__
			assert 'ping' not in ShadowPreservesSourceNamespaceThroughInheritance.__dict__
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_shadow_publishes_source_fields_and_field_props(cls):
		state = cls._patch_runtime()

		try:
			ShadowPublishesSourceFieldsAndFieldProps = cls._source_class(
				state,
				'ShadowPublishesSourceFieldsAndFieldProps',
				(
					'import o\n\n'
					'class ShadowPublishesSourceFieldsAndFieldProps(o.T):\n'
					'\tname: str\n'
					'\tage = o.F(int, default=7, description=\'Age\')\n'
				)
			)

			assert '_' in ShadowPublishesSourceFieldsAndFieldProps.__dict__
			assert ShadowPublishesSourceFieldsAndFieldProps.__annotations__['name'] == o.Str.__annotation__
			assert ShadowPublishesSourceFieldsAndFieldProps.__annotations__['age'] == o.Int.__annotation__
			assert ShadowPublishesSourceFieldsAndFieldProps.age == 7
			assert ShadowPublishesSourceFieldsAndFieldProps._.age.type is o.Int
			assert ShadowPublishesSourceFieldsAndFieldProps._.age.description == 'Age'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_shadow_inherits_annotation_without_owning(cls):
		state = cls._patch_runtime()

		try:
			ShadowInheritsAnnotationWithoutOwning = cls._source_class(
				state,
				'ShadowInheritsAnnotationWithoutOwning',
				(
					'import o\n\n'
					'class ShadowInheritsAnnotationWithoutOwning(o.T, list[str]):\n'
					'\tpass\n'
				)
			)
			raw_cls       = cls._raw_source_class(state, 'ShadowInheritsAnnotationWithoutOwning')
			embodied_base = raw_cls.__bases__[0]

			assert ShadowInheritsAnnotationWithoutOwning.__annotation__ == o.Annotation(list[str])
			assert ShadowInheritsAnnotationWithoutOwning.__dict__.get('__annotation__', o.Undefined) is o.Undefined
			assert embodied_base.__dict__['__annotation__'] == o.Annotation(list[str])
			assert o.__cast_map__[list[str]] is embodied_base
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_shadow_rebinds_cached_class_after_entity_eviction(cls):
		state = cls._patch_runtime()

		try:
			ShadowRebindsCachedClassAfterEntityEviction = cls._source_class(
				state,
				'ShadowRebindsCachedClassAfterEntityEviction',
				(
					'import o\n\n'
					'class ShadowRebindsCachedClassAfterEntityEviction(o.T):\n'
					'\tpass\n'
				)
			)
			entity_id = ShadowRebindsCachedClassAfterEntityEviction.id

			del o.__entities__[entity_id]

			reopened = o.T.ShadowRebindsCachedClassAfterEntityEviction

			assert reopened is ShadowRebindsCachedClassAfterEntityEviction
			assert o.__entities__[entity_id] is ShadowRebindsCachedClassAfterEntityEviction
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_shadow_keeps_source_marker_and_runtime_field_props(cls):
		state = cls._patch_runtime()

		try:
			ShadowKeepsSourceMarkerAndRuntimeFieldProps = cls._source_class(
				state,
				'ShadowKeepsSourceMarkerAndRuntimeFieldProps',
				(
					'import o\n\n'
					'class ShadowKeepsSourceMarkerAndRuntimeFieldProps(o.T):\n'
					'\tage = o.F(int, default=7, description=\'Age\')\n'
				)
			)
			entity_id  = ShadowKeepsSourceMarkerAndRuntimeFieldProps.id
			disk_field = ShadowKeepsSourceMarkerAndRuntimeFieldProps.__disk_class__.fields.get('age')

			ShadowKeepsSourceMarkerAndRuntimeFieldProps._.age.label = 'Years'

			assert disk_field.is_source() == True
			assert disk_field.get('label') == 'Years'

			del o.__entities__[entity_id]

			reopened = o.T.ShadowKeepsSourceMarkerAndRuntimeFieldProps

			assert reopened._.age.label == 'Years'
			assert reopened.__disk_class__.fields.get('age').is_source() == True
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_source_backed_get_returns_public_shadow_class(cls):
		state = cls._patch_runtime()

		try:
			SourceBackedGetReturnsPublicShadowClass = cls._source_class(
				state,
				'SourceBackedGetReturnsPublicShadowClass',
				(
					'import o\n\n'
					'class SourceBackedGetReturnsPublicShadowClass(o.T):\n'
					'\tpass\n'
				)
			)
			class_id = SourceBackedGetReturnsPublicShadowClass.id
			proto    = SourceBackedGetReturnsPublicShadowClass.__proto__

			del o.__entities__[class_id]

			by_id    = o.get(class_id)
			by_proto = o.get(proto)

			assert by_id is SourceBackedGetReturnsPublicShadowClass
			assert by_proto is SourceBackedGetReturnsPublicShadowClass
		finally:
			cls._restore_runtime(state)
