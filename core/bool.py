import o


class Bool(o.Atom):
	__annotation__ = bool

	# Cast atomic bytes out
	# ----------------------------------------------------------------------
	def __cast_out__(self, value):
		return value == b'1'

	# Cast atomic value into bytes
	# ----------------------------------------------------------------------
	def __cast_in__(self, value):
		return b'1' if value else b'0'
