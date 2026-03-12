import o


class TestTypeAnnotate(o.Test):

	@classmethod
	def test_atomic(cls):
		t = o.Annotation.annotate(5)
		assert t.annotation == int

	@classmethod
	def test_simple_list(cls):
		t = o.Annotation.annotate([1, 2, 3])
		assert t.annotation == list[int]

	@classmethod
	def test_nested_list(cls):
		t = o.Annotation.annotate([[1], [2]])
		assert t.annotation == list[list[int]]

	@classmethod
	def test_dict_simple(cls):
		t = o.Annotation.annotate({1: 2, 3: 4})
		assert t.annotation == dict[int, int]

	@classmethod
	def test_dict_nested(cls):
		t = o.Annotation.annotate({1: [2], 3: [4]})
		assert t.annotation == dict[int, list[int]]

	@classmethod
	def test_list_not_homogenous_atomic_allowed_as_union(cls):
		t = o.Annotation.annotate([1, 2.0])

		assert t.is_list
		assert t.value is not None
		assert t.value.is_union
		assert {option.id for option in t.value.options} == {'int', 'float'}

	@classmethod
	def test_list_not_homogenous_nested_allowed_as_union(cls):
		t = o.Annotation.annotate([[1], [2.0]])

		assert t.is_list
		assert t.value is not None
		assert t.value.is_union
		assert all(option.is_list for option in t.value.options)

	@classmethod
	def test_list_mixed_depth_allowed_as_union(cls):
		t = o.Annotation.annotate([1, [2]])

		assert t.is_list
		assert t.value is not None
		assert t.value.is_union
		assert {option.id for option in t.value.options} == {'int', 'list[int]'}

	@classmethod
	def test_dict_value_not_homogenous_allowed_as_union(cls):
		t = o.Annotation.annotate({1: 2, 3: '4'})

		assert t.is_dict
		assert t.value is not None
		assert t.value.is_union
		assert {option.id for option in t.value.options} == {'int', 'str'}

	@classmethod
	def test_dict_key_not_homogenous_allowed_as_union(cls):
		t = o.Annotation.annotate({1: 2, '3': 4})

		assert t.is_dict
		assert t.key is not None
		assert t.key.is_union
		assert {option.id for option in t.key.options} == {'int', 'str'}

	@classmethod
	def test_empty_list(cls):
		t = o.Annotation.annotate([])
		assert t.annotation == list

	@classmethod
	def test_empty_dict(cls):
		t = o.Annotation.annotate({})
		assert t.annotation == dict


if __name__ == '__main__':
	TestTypeAnnotate.run()
	print('\nAll tests passed')
