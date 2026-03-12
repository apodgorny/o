import o


class TestAnnotation(o.Test):

	# ----------------------------------------------------------------------
	@classmethod
	def test_basic(cls):
		a = o.Annotation(int)

		assert a.annotation is int
		assert a.origin is int
		assert a.is_none is False
		assert a.is_union is False
		assert a.is_optional is False
		assert a.is_list is False
		assert a.is_dict is False
		assert a.is_set is False
		assert a.is_tuple is False
		assert a.is_atomic is True
		assert a.key is None
		assert a.value is None
		assert a.is_homogenous is True
		assert a.id == 'int'
		assert repr(a) == 'int'
		assert str(a) == 'int'

	# ----------------------------------------------------------------------
	@classmethod
	def test_none(cls):
		a = o.Annotation(None)

		assert a.is_none is True
		assert a.is_union is False
		assert a.is_optional is False
		assert a.is_atomic is True
		assert a.id == 'None'

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_typed(cls):
		a = o.Annotation(list[int])

		assert a.origin is list
		assert a.is_list is True
		assert a.is_dict is False
		assert a.is_atomic is False
		assert a.key == o.Annotation(int)
		assert a.value == o.Annotation(int)
		assert a.is_homogenous is True
		assert a.id == 'list[int]'

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_untyped(cls):
		a = o.Annotation(list)

		assert a.origin is list
		assert a.is_list is True
		assert a.key == o.Annotation(int)
		assert a.value is None
		assert a.is_homogenous is True
		assert a.id == 'list'

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_typed(cls):
		a = o.Annotation(dict[str, int])

		assert a.origin is dict
		assert a.is_dict is True
		assert a.is_list is False
		assert a.is_atomic is False
		assert a.key == o.Annotation(str)
		assert a.value == o.Annotation(int)
		assert a.is_homogenous is True
		assert a.id == 'dict[str, int]'

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_untyped(cls):
		a = o.Annotation(dict)

		assert a.origin is dict
		assert a.is_dict is True
		assert a.key is None
		assert a.value is None
		assert a.is_homogenous is True
		assert a.id == 'dict'

	# ----------------------------------------------------------------------
	@classmethod
	def test_union(cls):
		a = o.Annotation(int | str)

		assert a.is_union is True
		assert a.is_optional is False
		assert a.is_homogenous is False
		assert a.options == {o.Annotation(int), o.Annotation(str)}
		assert a.id == 'int | str'

	# ----------------------------------------------------------------------
	@classmethod
	def test_optional(cls):
		a = o.Annotation(int | None)

		assert a.is_union is True
		assert a.is_optional is True
		assert a.is_homogenous is False
		assert a.options == {o.Annotation(int), o.Annotation(None)}
		assert a.id == 'None | int'

	# ----------------------------------------------------------------------
	@classmethod
	def test_nested_union_flattening(cls):
		a = o.Annotation((int | str) | None)

		assert a.is_union is True
		assert a.is_optional is True
		assert a.options == {
			o.Annotation(int),
			o.Annotation(str),
			o.Annotation(None),
		}
		assert a.id == 'None | int | str'

	# ----------------------------------------------------------------------
	@classmethod
	def test_equality_hash(cls):
		a = o.Annotation(list[int])
		b = o.Annotation(list[int])
		c = o.Annotation(list[str])

		assert a == b
		assert a != c
		assert hash(a) == hash(b)

	# ----------------------------------------------------------------------
	@classmethod
	def test_from_annotation_instance(cls):
		inner = o.Annotation(dict[str, int])
		outer = o.Annotation(inner)

		assert outer == inner
		assert outer.annotation == inner.annotation
		assert outer.id == 'dict[str, int]'

	# ----------------------------------------------------------------------
	@classmethod
	def test_annotate_atomic(cls):
		a = o.Annotation.annotate(123)

		assert a == o.Annotation(int)

	# ----------------------------------------------------------------------
	@classmethod
	def test_annotate_none(cls):
		a = o.Annotation.annotate(None)

		assert a == o.Annotation(None)

	# ----------------------------------------------------------------------
	@classmethod
	def test_annotate_empty_list(cls):
		a = o.Annotation.annotate([])

		assert a == o.Annotation(list)
		assert a.id == 'list'

	# ----------------------------------------------------------------------
	@classmethod
	def test_annotate_typed_list(cls):
		a = o.Annotation.annotate([1, 2, 3])

		assert a == o.Annotation(list[int])
		assert a.id == 'list[int]'

	# ----------------------------------------------------------------------
	@classmethod
	def test_annotate_union_list(cls):
		a = o.Annotation.annotate([1, 'x', None])

		assert a == o.Annotation(list[int | str | None])
		assert a.id == 'list[None | int | str]'

	# ----------------------------------------------------------------------
	@classmethod
	def test_annotate_empty_dict(cls):
		a = o.Annotation.annotate({})

		assert a == o.Annotation(dict)
		assert a.id == 'dict'

	# ----------------------------------------------------------------------
	@classmethod
	def test_annotate_typed_dict(cls):
		a = o.Annotation.annotate({'a': 1, 'b': 2})

		assert a == o.Annotation(dict[str, int])
		assert a.id == 'dict[str, int]'

	# ----------------------------------------------------------------------
	@classmethod
	def test_annotate_union_dict(cls):
		a = o.Annotation.annotate({
			'a': 1,
			2: 'b',
		})

		assert a == o.Annotation(dict[str | int, int | str])
		assert a.id == 'dict[int | str, int | str]'

	# ----------------------------------------------------------------------
	@classmethod
	def test_annotate_nested_dict_list(cls):
		a = o.Annotation.annotate({
			'a': [1, 2],
			'b': ['x'],
		})

		assert a == o.Annotation(dict[str, list[int] | list[str]])
		assert a.id == 'dict[str, list[int] | list[str]]'

	# ----------------------------------------------------------------------
	@classmethod
	def test_invalid_list_arity(cls):
		try:
			o.Annotation(list[int, str])
			assert False
		except TypeError as e:
			assert 'Invalid list annotation' in str(e)

	# ----------------------------------------------------------------------
	@classmethod
	def test_invalid_dict_arity(cls):
		try:
			o.Annotation(dict[str])
			assert False
		except TypeError as e:
			assert 'Invalid dict annotation' in str(e)

	# ----------------------------------------------------------------------
	@classmethod
	def test_none_value(cls):
		a = o.Annotation.annotate(None)

		assert a == o.Annotation(None)
		assert a.id == 'None'
		assert a.is_none is True

	# ----------------------------------------------------------------------
	@classmethod
	def test_none_type(cls):
		a = o.Annotation(type(None))

		assert a == o.Annotation(None)
		assert a.id == 'None'
		assert a.is_none is True

	# ----------------------------------------------------------------------
	@classmethod
	def test_nan_raises(cls):
		try:
			o.Annotation.annotate(float('nan'))
			assert False
		except ValueError as e:
			assert 'Invalid JSON number' in str(e)

	# ----------------------------------------------------------------------
	@classmethod
	def test_positive_infinity_raises(cls):
		try:
			o.Annotation.annotate(float('inf'))
			assert False
		except ValueError as e:
			assert 'Invalid JSON number' in str(e)

	# ----------------------------------------------------------------------
	@classmethod
	def test_negative_infinity_raises(cls):
		try:
			o.Annotation.annotate(float('-inf'))
			assert False
		except ValueError as e:
			assert 'Invalid JSON number' in str(e)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_with_nan_raises(cls):
		try:
			o.Annotation.annotate([1.0, float('nan')])
			assert False
		except ValueError as e:
			assert 'Invalid JSON number' in str(e)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_with_infinity_raises(cls):
		try:
			o.Annotation.annotate([1.0, float('inf')])
			assert False
		except ValueError as e:
			assert 'Invalid JSON number' in str(e)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_with_nan_value_raises(cls):
		try:
			o.Annotation.annotate({'a': float('nan')})
			assert False
		except ValueError as e:
			assert 'Invalid JSON number' in str(e)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_with_infinity_value_raises(cls):
		try:
			o.Annotation.annotate({'a': float('-inf')})
			assert False
		except ValueError as e:
			assert 'Invalid JSON number' in str(e)

	# ----------------------------------------------------------------------
	@classmethod
	def test_valid_float_still_works(cls):
		a = o.Annotation.annotate(1.25)

		assert a == o.Annotation(float)
		assert a.id == 'float'


if __name__ == '__main__':
	TestAnnotation.run()