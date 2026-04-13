import o


class Null(o.Atom):
	__annotation__ = type(None)

	# Cast atomic bytes out
	# ----------------------------------------------------------------------
	def __cast_out__(self, value):
		return None

	# Cast atomic value into bytes
	# ----------------------------------------------------------------------
	def __cast_in__(self, value):
		return b''
