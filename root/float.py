import o


class Float(o.Atom):
	__annotation__ = float

	# Cast atomic bytes out
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		return float(self.__value__)

	# Cast atomic value into bytes
	# ----------------------------------------------------------------------
	def __cast_in__(self, value):
		object.__setattr__(self, '__value__', value)
		self.__zone__.set('__value__', value)
