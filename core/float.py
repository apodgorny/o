import o


class Float(o.One):
	__python_type__ = float

	def __init__(self, value=None):
		super().__init__('d', value)