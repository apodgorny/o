# ======================================================================
# Dual access smoke tests
# ======================================================================

import o


class Sample:
	@o.dual_property
	def kind(cls, self=None):
		if self is None:
			return f'class:{cls.__name__}'
		return f'instance:{cls.__name__}'

	@o.dual_method
	def who(cls, self=None, x=0, y=0):
		if self is None:
			return f'class:{cls.__name__}:{x + y}'
		return f'instance:{cls.__name__}:{x + y}'


# ----------------------------------------------------------------------
# dual_property
# ----------------------------------------------------------------------

assert Sample.kind       == 'class:Sample'
assert Sample().kind     == 'instance:Sample'


# ----------------------------------------------------------------------
# dual_method
# ----------------------------------------------------------------------

assert Sample.who(1, 2)      == 'class:Sample:3'
assert Sample().who(3, 4)    == 'instance:Sample:7'


print('dual_property ok')
print('dual_method ok')
