import o


class Key(o.One):

	def __init__(self, value=None):

		if isinstance(value, str):
			value = value.encode('utf-8')

		if isinstance(value, bytes):
			if len(value) > 32:
				raise ValueError('Key too long')
			value = value.ljust(32, b'\x00')

		super().__init__(value, word='32s')

	def __cast_out__(self):
		raw = self.__read__()
		return raw.rstrip(b'\x00').decode('utf-8')