import o


class Key(o.One):

	def __init__(self, value=None):
		super().__init__('32s', value)
