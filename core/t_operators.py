import operator

import o


UNARY_OPERATORS = {
	'__pos__'    : operator.pos,
	'__neg__'    : operator.neg,
	'__abs__'    : operator.abs,
	'__invert__' : operator.invert,
}

COMPARISON_OPERATORS = {
	'__lt__' : operator.lt,
	'__le__' : operator.le,
	'__eq__' : operator.eq,
	'__ne__' : operator.ne,
	'__gt__' : operator.gt,
	'__ge__' : operator.ge,
}

BINARY_OPERATORS = {
	'__add__'      : operator.add,
	'__sub__'      : operator.sub,
	'__mul__'      : operator.mul,
	'__matmul__'   : operator.matmul,
	'__truediv__'  : operator.truediv,
	'__floordiv__' : operator.floordiv,
	'__mod__'      : operator.mod,
	'__pow__'      : operator.pow,
	'__lshift__'   : operator.lshift,
	'__rshift__'   : operator.rshift,
	'__and__'      : operator.and_,
	'__xor__'      : operator.xor,
	'__or__'       : operator.or_,
}

REFLECTED_OPERATORS = {
	'__radd__'      : operator.add,
	'__rsub__'      : operator.sub,
	'__rmul__'      : operator.mul,
	'__rmatmul__'   : operator.matmul,
	'__rtruediv__'  : operator.truediv,
	'__rfloordiv__' : operator.floordiv,
	'__rmod__'      : operator.mod,
	'__rpow__'      : operator.pow,
	'__rlshift__'   : operator.lshift,
	'__rrshift__'   : operator.rshift,
	'__rand__'      : operator.and_,
	'__rxor__'      : operator.xor,
	'__ror__'       : operator.or_,
}


class TOperators(o.Module):

	# Get Python-visible operator value
	# ----------------------------------------------------------------------
	def _get_operator_value(self):
		value = o.undefined

		if isinstance(self, o.Atom):
			value = self.__value__
		elif isinstance(self, o.List):
			value = list(self)
		elif isinstance(self, o.Dict):
			value = dict(self.items())

		if value is o.undefined:
			raise TypeError(f'`{self.__class__.__proto__}` does not support operators')

		return value

	# Normalize operator operand
	# ----------------------------------------------------------------------
	@classmethod
	def _get_operand_value(cls, value):
		result = value

		if isinstance(value, o.T):
			result = value._get_operator_value()

		return result

	# Bind operator surface to target class
	# ----------------------------------------------------------------------
	@classmethod
	def bind(cls, target):
		names = [
			'_get_operator_value',
			'_get_operand_value',
			*UNARY_OPERATORS,
			*BINARY_OPERATORS,
			*REFLECTED_OPERATORS,
			*COMPARISON_OPERATORS,
		]

		for name in names:
			setattr(target, name, getattr(cls, name))


def _make_unary_operator(name, op):
	def method(self):
		value  = self._get_operator_value()
		result = op(value)

		return result

	method.__name__ = name

	return method


def _make_binary_operator(name, op):
	def method(self, other):
		left   = self._get_operator_value()
		right  = self._get_operand_value(other)
		result = op(left, right)

		return result

	method.__name__ = name

	return method


def _make_reflected_operator(name, op):
	def method(self, other):
		left   = self._get_operand_value(other)
		right  = self._get_operator_value()
		result = op(left, right)

		return result

	method.__name__ = name

	return method


for name, op in UNARY_OPERATORS.items():
	setattr(TOperators, name, _make_unary_operator(name, op))

for name, op in BINARY_OPERATORS.items():
	setattr(TOperators, name, _make_binary_operator(name, op))

for name, op in REFLECTED_OPERATORS.items():
	setattr(TOperators, name, _make_reflected_operator(name, op))

for name, op in COMPARISON_OPERATORS.items():
	setattr(TOperators, name, _make_binary_operator(name, op))
