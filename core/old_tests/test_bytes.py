import o


class TestBytes(o.Test):

	@classmethod
	def test_constructor_rejects_two_positional_arguments(cls):
		try:
			o.Bytes(4, b'ab')
			assert False
		except TypeError as e:
			assert 'Too many positional arguments' in str(e)


if __name__ == '__main__':
	TestBytes.run()
