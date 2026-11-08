# ==============================================================================
# ROOT VALUE
# ==============================================================================
# Expose the persistent ontology root and its authorization policy snapshot.
# ==============================================================================

import o


class V(o.T):

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Define a field when assigning a previously unknown root attribute.
	# ----------------------------------------------------------------------
	def __setattr__(self, name, value):
		if not self.__class__.__has_field__(name):
			field_type = value.__class__ if isinstance(value, o.T) else type(value)
			setattr(self.__class__, name, o.F(field_type, default=None))

		super().__setattr__(name, value)

	# Remove a root field definition when its value is deleted.
	# ----------------------------------------------------------------------
	def __delattr__(self, name):
		super().__delattr__(name)
		delattr(self.__class__, name)

	# Retain the root independently of ordinary garbage collection.
	# ----------------------------------------------------------------------
	@classmethod
	def __read__(cls, version):
		self = super().__read__(version)

		object.__setattr__(self, '__refcount__', 1)

		return self

	# Expose a detached snapshot without creating tree ownership edges.
	# ----------------------------------------------------------------------
	@property
	def __auth__(self):
		if o.TREE_MODE:
			prefix = f'{self.__proto__}.__auth__/'
			rules  = {}

			with o.services.Memory.read() as memory:
				for key, policies in memory.items(prefix):
					rules[int(key[len(prefix):])] = policies
		else:
			raise RuntimeError('Auth requires tree mode')

		return rules
