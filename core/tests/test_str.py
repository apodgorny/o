import o


class TestStr(o.Test):

	@classmethod
	def test_basic_roundtrip(cls):
		s = o.Str('hello')
		assert s.__cast_out__() == 'hello'
		assert str(s) == 'hello'

	@classmethod
	def test_default_none_becomes_empty_string(cls):
		s = o.Str()
		assert s.__cast_out__() == ''
		assert len(s) == 0

	@classmethod
	def test_init_requires_str(cls):
		try:
			o.Str(123)
			assert False
		except TypeError:
			pass

	@classmethod
	def test_len_iter_contains(cls):
		s = o.Str('abc')
		assert len(s) == 3
		assert list(iter(s)) == ['a', 'b', 'c']
		assert ('a' in s) == True
		assert ('z' in s) == False

	@classmethod
	def test_bool_conversion(cls):
		assert bool(o.Str('')) == False
		assert bool(o.Str('x')) == True

	@classmethod
	def test_getitem_positive(cls):
		s = o.Str('abc')
		assert s[1] == 'b'

	@classmethod
	def test_getitem_negative(cls):
		s = o.Str('abc')
		assert s[-1] == 'c'

	@classmethod
	def test_getitem_out_of_range(cls):
		s = o.Str('abc')
		try:
			_ = s[10]
			assert False
		except IndexError:
			pass

	@classmethod
	def test_getitem_non_int_typeerror(cls):
		s = o.Str('abc')
		try:
			_ = s[1.2]
			assert False
		except TypeError:
			pass

	@classmethod
	def test_slice_returns_str_object(cls):
		s = o.Str('abcdef')
		part = s[1:4]
		assert isinstance(part, o.Str)
		assert str(part) == 'bcd'

	@classmethod
	def test_slice_empty_when_out_of_range(cls):
		s = o.Str('abc')
		part = s[99:100]
		assert isinstance(part, o.Str)
		assert str(part) == ''

	@classmethod
	def test_slice_with_step(cls):
		s = o.Str('abcdef')
		part = s[::2]
		assert str(part) == 'ace'

	@classmethod
	def test_slice_negative_indices(cls):
		s = o.Str('abcdef')
		part = s[-4:-1]
		assert str(part) == 'cde'

	@classmethod
	def test_add_with_python_str(cls):
		s = o.Str('ab')
		out = s + 'cd'
		assert isinstance(out, o.Str)
		assert str(out) == 'abcd'
		assert str(s) == 'ab'

	@classmethod
	def test_add_with_o_str(cls):
		a = o.Str('ab')
		b = o.Str('cd')
		out = a + b
		assert isinstance(out, o.Str)
		assert str(out) == 'abcd'
		assert str(a) == 'ab'
		assert str(b) == 'cd'

	@classmethod
	def test_add_invalid_type_raises(cls):
		s = o.Str('ab')
		try:
			_ = s + 1
			assert False
		except TypeError:
			pass

	@classmethod
	def test_immutable_setitem(cls):
		s = o.Str('abc')
		try:
			s[0] = 'x'
			assert False
		except TypeError:
			pass

	@classmethod
	def test_immutable_delitem(cls):
		s = o.Str('abc')
		try:
			del s[0]
			assert False
		except TypeError:
			pass

	@classmethod
	def test_immutable_clear_magic(cls):
		s = o.Str('abc')
		try:
			s.__clear__()
			assert False
		except TypeError:
			pass

	@classmethod
	def test_eq_ne_with_python_str(cls):
		s = o.Str('abc')
		assert (s == 'abc') == True
		assert (s != 'abc') == False
		assert (s == 'ab') == False

	@classmethod
	def test_comparisons_like_python_str(cls):
		s = o.Str('b')
		assert (s > 'a') == True
		assert (s < 'c') == True
		assert (s >= 'b') == True
		assert (s <= 'b') == True

	@classmethod
	def test_repr_format(cls):
		s = o.Str('abc')
		assert repr(s) == "Str('abc')"

	@classmethod
	def test_forwarded_non_mutating_methods(cls):
		s = o.Str('Abc Abc')
		assert s.lower() == 'abc abc'
		assert s.upper() == 'ABC ABC'
		assert s.replace('Abc', 'x') == 'x x'
		assert s.count('Abc') == 2
		assert s.find('bc') == 1
		assert s.startswith('Ab') == True
		assert s.endswith('bc') == True
		assert str(s) == 'Abc Abc'

	@classmethod
	def test_split_returns_python_list(cls):
		s = o.Str('a,b,c')
		out = s.split(',')
		assert isinstance(out, list)
		assert out == ['a', 'b', 'c']
		assert str(s) == 'a,b,c'

	@classmethod
	def test_bind_reopen_by_id(cls):
		s1 = o.Str('hello')
		s2 = o.Str.bind(s1.__id__)
		assert str(s2) == 'hello'

	@classmethod
	def test_commit_persistence(cls):
		s1 = o.Str('hello')
		o.services.Many.commit()
		s2 = o.Str.bind(s1.__id__)
		assert str(s2) == 'hello'

	@classmethod
	def test_isolation_between_strings(cls):
		a = o.Str('a')
		b = o.Str('b')
		assert str(a) == 'a'
		assert str(b) == 'b'

	@classmethod
	def test_delete_removes_storage(cls):
		s = o.Str('abc')
		id_ = s.__id__
		s.__delete__()

		try:
			o.Str.bind(id_)
			assert False
		except KeyError:
			pass


if __name__ == '__main__':
	TestStr.run()
	print('\nAll tests passed')
