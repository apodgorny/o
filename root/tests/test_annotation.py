import math

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


if __name__ == '__main__':
	TestAnnotation.run()
