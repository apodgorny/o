import o

UNDEFINED = o.Undefined


class Atom(o.T):
	__is_atom__ = True

	# Initialize atomic value
	# ----------------------------------------------------------------------
	def __init__(self, value=UNDEFINED):
		origin = self.__annotation__.origin

		if value is UNDEFINED:
			raise TypeError(f'`{self.__class__.__proto__}` is missing a value')

		if not isinstance(value, origin):
			raise TypeError(
				f'`{self.__class__.__proto__}` expects `{origin}`, got `{type(value)}`'
			)

		self.__cast_in__(value)

	# Read atomic instance from memory
	# ----------------------------------------------------------------------
	@classmethod
	def __read__(cls, version):
		self  = super().__read__(version)
		value = o.services.Memory.get(f'{self.__proto__}.__value__', UNDEFINED)

		if value is not UNDEFINED:
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
