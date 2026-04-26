import o


class Atom(o.T):
	__is_atom__ = True

	# Initialize atomic value
	# ----------------------------------------------------------------------
	def __init__(self, value=o.Undefined):
		origin = self.__annotation__.origin

		if value is o.Undefined:
			raise TypeError(f'`{self.__class__.__proto__}` is missing a value')

		if not isinstance(value, origin):
			raise TypeError(
				f'`{self.__class__.__proto__}` expects `{origin}`, got `{type(value)}`'
			)

		self.__cast_in__(value)

	# Materialize atomic instance from disk
	# ----------------------------------------------------------------------
	@classmethod
	def __materialize__(cls, version):
		self  = super().__materialize__(version)
		value = self.__disk_instance__.atomic.get()

		if value is not o.Undefined:
			object.__setattr__(self, '__value__', value)
			value = self.__cast_out__()

		object.__setattr__(self, '__value__', value)

		return self

	# # Cast atomic value out
	# # ----------------------------------------------------------------------
	# def __cast_out__(self):
	# 	raise NotImplementedError

	# # Cast atomic value into bytes
	# # ----------------------------------------------------------------------
	# def __cast_in__(self, value):
	# 	raise NotImplementedError
