import o


class Str(o.Atom):
	__annotation__ = str

	# Cast atomic bytes out
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		return str(self.__value__)

	# Cast atomic value into bytes
	# ----------------------------------------------------------------------
	def __cast_in__(self, value):
		object.__setattr__(self, '__value__', value)
		o.services.Memory.set(f'{self.__proto__}.__value__', value)
