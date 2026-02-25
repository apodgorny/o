import o


class Int(o.One):
	__python_type__ = int
	
	def __init__(self, value=None):
		super().__init__('q', value)
