import o


class Bytes(o.One):

	def __init__(self, size, value=None):
		super().__init__(value, word=f'{size}s')