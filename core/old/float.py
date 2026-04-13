import o


class Float(o.One):
	__annotation__ = float

	def __init__(self, value=None):
		super().__init__(value, word='d')