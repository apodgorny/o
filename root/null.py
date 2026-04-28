import o


class Null(o.Atom):
	__annotation__ = type(None)

	# Cast atomic bytes out
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		return None

	# Cast atomic value into bytes
	# ----------------------------------------------------------------------
	def __cast_in__(self, value):
		object.__setattr__(self, '__value__', value)
		o.services.Memory.set(f'{self.__proto__}.__value__', value)
