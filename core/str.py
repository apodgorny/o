import o


class Str(o.Atom):
	__annotation__ = str

	# Cast atomic bytes out
	# ----------------------------------------------------------------------
	def __cast_out__(self, value):
		return value.decode('utf-8')

	# Cast atomic value into bytes
	# ----------------------------------------------------------------------
	def __cast_in__(self, value):
		return value.encode('utf-8')
