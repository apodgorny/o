import o


class TestKey(o.Test):

	@classmethod
	def test_roundtrip_from_str(cls):
		x = o.Key('alpha')
		assert x.__cast_out__() == 'alpha'

	@classmethod
	def test_roundtrip_from_bytes(cls):
		x = o.Key(b'alpha')
		assert x.__cast_out__() == 'alpha'

	@classmethod
	def test_max_length_32_is_allowed(cls):
		text = 'a' * 32
		x = o.Key(text)

		assert x.__cast_out__() == text

	@classmethod
	def test_length_over_32_rejected(cls):
		try:
			o.Key('a' * 33)
			assert False
		except ValueError as e:
			assert 'Key too long' in str(e)

	@classmethod
	def test_property_compatible_validation(cls):
		for bad in ('a b', 'a-b', '1abc'):
			try:
				o.Key(bad)
				assert False
			except ValueError as e:
				assert 'property-compatible' in str(e)

	@classmethod
	def test_padding_is_stripped_on_cast_out(cls):
		x = o.Key('a')
		assert x.__cast_out__() == 'a'

	@classmethod
	def test_reopen_by_id(cls):
		x = o.Key('name')
		y = o.Key.instantiate(x.__id__)

		assert y is x
		assert y.__cast_out__() == 'name'

	@classmethod
	def test_delete_removes_storage(cls):
		x = o.Key('name')
		id_ = x.__id__

		x.__delete__()

		try:
			o.Key.instantiate(id_).__cast_out__()
			assert False
		except ValueError:
			pass


if __name__ == '__main__':
	TestKey.run()
