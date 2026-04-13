# ======================================================================
#   o.F — field declaration
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

	def __init__(self, type, description=None, default=o.undefined, **kwargs):
		self.type    = type
		self.default = default.copy() if hasattr(default, 'copy') else default
		self.props   = {**kwargs, 'description' : description}
