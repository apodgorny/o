import o


class Int(o.Atom):
	__annotation__ = int

	# Cast atomic bytes out
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		return int(self.__value__)

	# Cast atomic value into bytes
	# ----------------------------------------------------------------------
	def __cast_in__(self, value):
		object.__setattr__(self, '__value__', value)
		self.__disk_instance__.atomic.set(str(value).encode('utf-8'))
