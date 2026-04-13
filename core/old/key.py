import o


class Key(o.One):

	def __init__(self, value=None):
		super().__init__(value, word='32s')

	def __cast_in__(self, value):
		text = None
		data = None

		if isinstance(value, str):
			text = value
		elif isinstance(value, bytes):
			text = value.decode('utf-8')
		else:
			raise TypeError(f'Expected `str` or `bytes`, got `{type(value)}`')

		if not text.isidentifier():
			raise ValueError(f'Key must be property-compatible: `{text}`')

		data = text.encode('utf-8')

		if len(data) > 32:
			raise ValueError('Key too long')

		data = data.ljust(32, b'\x00')

		return self.__write__(data)

	def __cast_out__(self):
		raw = self.__read__()
		return raw.rstrip(b'\x00').decode('utf-8')