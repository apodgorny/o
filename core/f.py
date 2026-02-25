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
# ======================================================================

import o


class F(o.Module):

	def __init__(self, type, description=None, default=o.undefined, is_optional=False, name=None):
		self.name        = name
		self.type        = o.T.from_python_type(type)
		self.default     = default
		self.is_optional = is_optional
		self.description = description

	# --------------------------------------------------------------
	@property
	def value(self):
		return self.type.read(type_id, instance_id)

	# --------------------------------------------------------------
	@value.setter
	def value(self, value):
		if self.default is not o.undefined:
			value = self.default
		elif self.is_optional:
			value = None
		else:
			raise TypeError(f'Field `{self.name}` is required')

		if not isinstance(value, self.type.cls):
			raise TypeError(
				f'Expected `{self.type.cls.__name__}`, got `{value.__class__.__name__}`'
			)

		self.type.write(type_id, instance_id, value)

	# --------------------------------------------------------------
	def create(self, value):
		new = self.__class__(
			name        = self.name,
			type        = self.type,
			description = self.description,
			default     = self.default,
			is_optional = self.is_optional
		)
		new.value = value
		return new
