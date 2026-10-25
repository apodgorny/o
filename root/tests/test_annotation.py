import math
import types
import typing as t

import o


class TestAnnotation(o.Tester):

	# ----------------------------------------------------------------------
	@classmethod
	def test_basic_atomic_annotations(cls):
		assert o.Annotation(int).id == 'int'
		assert o.Annotation(str).id == 'str'
		assert o.Annotation(type(None)).id == 'None'
		assert o.Annotation(bool).is_bool == True
		assert o.Annotation(float).is_atomic == True

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_and_dict_annotations(cls):
		list_annotation = o.Annotation(list[int])
		dict_annotation = o.Annotation(dict[str, int])

		assert list_annotation.is_list == True
		assert list_annotation.key.annotation == int
		assert list_annotation.value.annotation == int
		assert list_annotation.id == 'list[int]'

		assert dict_annotation.is_dict == True
		assert dict_annotation.key.annotation == str
		assert dict_annotation.value.annotation == int
		assert dict_annotation.id == 'dict[str, int]'

	# ----------------------------------------------------------------------
	@classmethod
	def test_union_and_optional_annotations(cls):
		annotation = o.Annotation(int | str | None)

		assert annotation.is_union == True
		assert annotation.is_optional == True
		assert sorted([option.id for option in annotation.options]) == ['None', 'int', 'str']

	# ----------------------------------------------------------------------
	@classmethod
	def test_annotation_equality_and_hash(cls):
		left  = o.Annotation(int | str)
		right = o.Annotation(str | int)

		assert left == right
		assert hash(left) == hash(right)

	# ----------------------------------------------------------------------
	@classmethod
	def test_annotate_nested_values(cls):
		assert o.Annotation.annotate(7).annotation == int
		assert o.Annotation.annotate([1, 'x']).annotation == list[int | str]
		assert o.Annotation.annotate({'a': [1], 'b': [2, 3]}).annotation == dict[str, list[int]]

	# ----------------------------------------------------------------------
	@classmethod
	def test_invalid_list_and_dict_arity_raise(cls):
		raised_list = False
		raised_dict = False

		try:
			o.Annotation(list[int, str])
		except TypeError:
			raised_list = True

		try:
			o.Annotation(dict[int])
		except TypeError:
			raised_dict = True

		assert raised_list == True
		assert raised_dict == True

	# ----------------------------------------------------------------------
	@classmethod
	def test_invalid_json_numbers_raise(cls):
		for value in [math.nan, math.inf, -math.inf]:
			raised = False

			try:
				o.Annotation.annotate(value)
			except ValueError:
				raised = True

			assert raised == True

	# ----------------------------------------------------------------------
	@classmethod
	def test_cast_matches_annotation_shape(cls):
		assert o.Annotation(bool).cast('1') == True
		assert o.Annotation(bool).cast('0') == False
		assert o.Annotation(list[int]).cast(['1', 2]) == [1, 2]
		assert o.Annotation(dict[str, int]).cast({'a': '1'}) == {'a': 1}


	# Preserve supported annotation forms through their persistent expressions.
	# ----------------------------------------------------------------------
	@classmethod
	def test_to_source_round_trip(cls):
		annotations = (
			None, type(None), int, float, bool, str, bytes,
			list, dict, set, tuple, Ellipsis, t.Any,
			list[int], dict[str, list[int | None]], set[str],
			tuple[int, str], tuple[int, ...], int | str | None,
			t.List[int], t.Dict[str, int], t.Optional[int], t.Union[int, str],
			types.FunctionType, types.BuiltinFunctionType,
			types.MethodType, types.BuiltinMethodType,
		)
		for declaration in annotations:
			annotation = o.Annotation(declaration)
			before     = (str(annotation), annotation.id, hash(annotation))
			restored   = o.Annotation(annotation.to_source())
			assert restored.annotation == annotation.annotation
			assert restored == annotation
			assert hash(restored) == hash(annotation)
			assert (str(annotation), annotation.id, hash(annotation)) == before

	# Reopen stored containers of native classes using their canonical addresses.
	# ----------------------------------------------------------------------
	@classmethod
	def test_to_source_native_types_and_persistent_reload(cls):
		state = cls._patch_runtime()
		try:
			Person = o.T.extend('AnnotationSourcePerson')
			Child  = Person.extend('Child')

			annotations = (
				Person, Child, list[Person], dict[str, Child],
				list[dict[str, Child]], Person | None,
				list[Person | Child | None], tuple[Child, ...],
			)
			for declaration in annotations:
				annotation = o.Annotation(declaration)
				before     = (str(annotation), annotation.id, hash(annotation))
				restored   = o.Annotation(annotation.to_source())
				assert restored.annotation == declaration
				assert (str(annotation), annotation.id, hash(annotation)) == before
			assert o.Annotation(list[Person]).to_source() == 'list[o.T.AnnotationSourcePerson]'
			assert o.Annotation(dict[str, Child]).to_source() == 'dict[str, o.T.AnnotationSourcePerson.Child]'

			Collection = o.T.extend('AnnotationSourceCollection', people=o.F(list[Person]))
			container  = Collection._.people.type
			proto      = container.__proto__
			identity   = container.id

			assert o.services.Memory.get(proto + '.__annotation__') == 'list[o.T.AnnotationSourcePerson]'
			o.unregister_entity(container)
			o.unregister_entity(Person)
			reopened = o.get(identity)
			assert reopened.id == identity
			assert reopened.__proto__ == proto
			assert reopened.__annotation__.annotation == list[o.T.AnnotationSourcePerson]
			assert Collection._.people.type is reopened
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestAnnotation.run()
