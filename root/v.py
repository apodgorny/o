import o


class V(o.T):

	# ----------------------------------------------------------------------
	@classmethod
	def __read__(cls, version):
		self = super().__read__(version)

		object.__setattr__(self, '__refcount__', 1)

		return self
