import o


class Int(o.One):
	__annotation__ = int
	
	def __init__(self, value=None):
		super().__init__(value, word='q')
