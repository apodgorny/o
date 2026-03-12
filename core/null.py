import o


class Null(o.One):
	__annotation__ = type(None)

	def __init__(self, value=None):
		super().__init__(value, word='B')

	def __cast_in__(self, value):
		if value is not None:
			raise TypeError(f'Expected `None`, got `{type(value)}`')

		return self.__write__(0)

	def __cast_out__(self):
		return None