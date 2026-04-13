import o


class Bool(o.One):
	__annotation__ = bool

	def __init__(self, value=None):
		super().__init__(value, word='?')
