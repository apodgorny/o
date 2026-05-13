import o


class V(o.T):

	# ----------------------------------------------------------------------
	def __setattr__(self, name, value):
		if not self.__class__.__has_field__(name):
			field_type = value.__class__ if isinstance(value, o.T) else type(value)
			setattr(self.__class__, name, o.F(field_type, default=None))

		super().__setattr__(name, value)

	# ----------------------------------------------------------------------
	def __delattr__(self, name):
		super().__delattr__(name)
		delattr(self.__class__, name)

	# ----------------------------------------------------------------------
	@classmethod
	def __read__(cls, version):
		self = super().__read__(version)

		object.__setattr__(self, '__refcount__', 1)

		return self
