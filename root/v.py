import o


class V(o.T):

	# Inspect the persisted authorization policies without exposing mutation.
	# ----------------------------------------------------------------------
	@property
	def __auth__(self):
		if not o.TREE_MODE:
			raise RuntimeError('Auth requires tree mode')

		prefix = f'{self.__proto__}.__auth__/'
		rules  = {}

		with o.services.Memory.read() as memory:
			for key, policies in memory.items(prefix):
				rules[int(key[len(prefix):])] = policies

		return rules

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
