import o


class Int(o.Atom):
	__annotation__ = int

	# Cast atomic bytes out
	# ----------------------------------------------------------------------
	def __cast_out__(self, value):
		return int(value.decode('utf-8'))

	# Cast atomic value into bytes
	# ----------------------------------------------------------------------
	def __cast_in__(self, value):
		return str(value).encode('utf-8')
