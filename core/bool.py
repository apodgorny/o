import o


class Bool(o.Atom):
	__annotation__ = bool

	# Cast atomic bytes out
	# ----------------------------------------------------------------------
	def __cast_out__(self):
		value = self.__value__

		if isinstance(value, bytes):
			value = value == b'1'

		return value

	# Cast atomic value into bytes
	# ----------------------------------------------------------------------
	def __cast_in__(self, value):
		object.__setattr__(self, '__value__', value)
		self.__disk_instance__.atomic.set(b'1' if value else b'0')
