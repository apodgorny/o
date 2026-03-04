import o


import o


class TestTypeAnnotate(o.Test):

	@classmethod
	def test_atomic(cls):
		t = o.Type.annotate(5)
		assert t.annotation == int


	@classmethod
	def test_simple_list(cls):
		t = o.Type.annotate([1, 2, 3])
		assert t.annotation == list[int]


	@classmethod
	def test_nested_list(cls):
		t = o.Type.annotate([[1], [2]])
		assert t.annotation == list[list[int]]


	@classmethod
	def test_dict_simple(cls):
		t = o.Type.annotate({1: 2, 3: 4})
		assert t.annotation == dict[int, int]


	@classmethod
	def test_dict_nested(cls):
		t = o.Type.annotate({1: [2], 3: [4]})
		assert t.annotation == dict[int, list[int]]


	@classmethod
	def test_list_not_homogenous_atomic(cls):
		try:
			o.Type.annotate([1, 2.0])
			assert False
		except Exception:
			assert True


	@classmethod
	def test_list_not_homogenous_nested(cls):
		try:
			o.Type.annotate([[1], [2.0]])
			assert False
		except Exception:
			assert True


	@classmethod
	def test_list_mixed_depth(cls):
		try:
			o.Type.annotate([1, [2]])
			assert False
		except Exception:
			assert True


	@classmethod
	def test_dict_value_not_homogenous(cls):
		try:
			o.Type.annotate({1: 2, 3: "4"})
			assert False
		except Exception:
			assert True


	@classmethod
	def test_dict_key_not_homogenous(cls):
		try:
			o.Type.annotate({1: 2, "3": 4})
			assert False
		except Exception:
			assert True


	@classmethod
	def test_empty_list(cls):
		t = o.Type.annotate([])
		assert t.annotation == list


	@classmethod
	def test_empty_dict(cls):
		t = o.Type.annotate({})
		assert t.annotation == dict

	
if __name__ == '__main__':
	TestTypeAnnotate.run()
	print('\nAll tests passed')
