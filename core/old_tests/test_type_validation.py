import o


class TestTypeValidation(o.Test):

	@classmethod
	def test_union_id_is_canonical_order(cls):
		a = o.Annotation(int | str)
		b = o.Annotation(str | int)

		assert a.id == b.id
		assert a.id == 'int | str'

	@classmethod
	def test_annotation_equality_for_equivalent_unions(cls):
		a = o.Annotation(int | str)
		b = o.Annotation(str | int)
		assert a == b

	@classmethod
	def test_homogenous_list_is_marked_homogenous(cls):
		t = o.Annotation(list[int])
		assert t.is_homogenous == True

	@classmethod
	def test_union_list_is_marked_non_homogenous(cls):
		t = o.Annotation(list[int | float])
		assert t.is_homogenous == False

	@classmethod
	def test_inferred_heterogenous_list_is_union_not_ordered_sequence(cls):
		t1 = o.Annotation.annotate([1, 2.0, '3'])
		t2 = o.Annotation.annotate(['3', 1, 2.0])

		assert t1.is_list
		assert t1.value is not None
		assert t1.value.is_union
		assert t1 == t2
		assert t1.id == t2.id

	@classmethod
	def test_inferred_heterogenous_dict_is_union_for_keys_and_values(cls):
		t = o.Annotation.annotate({1: 'a', '2': 3})

		assert t.is_dict
		assert t.key is not None
		assert t.value is not None
		assert t.key.is_union
		assert t.value.is_union
		assert {option.id for option in t.key.options} == {'int', 'str'}
		assert {option.id for option in t.value.options} == {'int', 'str'}

	@classmethod
	def test_optional_detection(cls):
		t = o.Annotation(int | None)
		assert t.is_union
		assert t.is_optional

	@classmethod
	def test_determinism_for_same_structure(cls):
		t1 = o.Annotation.annotate([1, {'x': 2.0}])
		t2 = o.Annotation.annotate([1, {'x': 2.0}])
		assert t1.id == t2.id
		assert t1 == t2


if __name__ == '__main__':
	TestTypeValidation.run()
	print('\nAll tests passed')
