import o


class Null(o.One):
	__python_type__ = type(None)

	def __init__(self, value=None):
		super().__init__(0, word='B')

	def __cast_out__(self):
		return None