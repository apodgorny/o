# ======================================================================
#   o.Field — minimal schema field definition
#
#	Defaults can be:
#	------------------------------------------
#	- Undefined = required / NOT NULL
#	- None      = optional / NULL
#	- Value     = optional / NOT NULL
#	------------------------------------------
#  if default -> optional
#
#
#  default       optional   nullable     required
#  -----------------------------------------------
#  undefined     ❌          ❌           ✅
#  None          ✅          ✅           ❌
#  Value ≠ None  ✅          ❌           ❌
#
#
#  required  = (default is undefined)
#  optional  = (default is not undefined)
#  nullable  = (default is None)
#
# ======================================================================

import o


class F(o.Module):

	def __init__(self, type, description=None, default=o.undefined, is_optional=False, name=None):
		tp = o.Type(type)
		self.name        = name
		self.type        = tp.to_non_optional()
		self.default     = default.copy() if hasattr(default, 'copy') else default
		self.is_optional = is_optional or tp.is_optional() or (default is not o.undefined)
		self.description = description

	# Validate field value
	# --------------------------------------------------------------
	def validate(self, value):
		tp = self.type
		
		# Undefined
		# - - - - - - - - - - - - - - - - - - - -
		if value is o.undefined:
			if self.default is not o.undefined:
				value = self.default
			elif self.is_optional:
				value = None
			else:
				raise TypeError(f'Field `{self.name}` is not optional and must not be undefined.')

		# None
		# - - - - - - - - - - - - - - - - - - - -
		elif value is None:
			if not self.is_optional:
				raise TypeError(f'Field `{self.name}` is not optional and must not be None.')

		# Value
		# - - - - - - - - - - - - - - - - - - - -
		else:

			# T or any o.Object
			# - - - - - - - - - - - - - - - - - - - -
			if isinstance(value, o.Object):
				if not (isinstance(tp.annotation, type) and issubclass(tp.annotation, o.Object)):
					raise TypeError(f'Field `{self.name}`: expected `{tp.annotation}`, got `{type(value)}`.')
				elif not isinstance(value, tp.annotation):
					raise TypeError(f'Field `{self.name}`: expected `{tp.annotation}`, got `{type(value)}`.')

			# Not o.Object
			# - - - - - - - - - - - - - - - - - - - -
			else:
				actual = o.Type.annotate(value)
				if actual not in tp:
					raise TypeError(
						f'Field `{self.name}`: expected `{tp.annotation}`, got `{actual.annotation}`.'
					)

		return value