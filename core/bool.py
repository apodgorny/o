import o


class Bool(o.One):
	__python_type__ = bool

	def __init__(self, value=None):
		super().__init__('?', value)
