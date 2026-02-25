# ======================================================================
# Base class for custom schema types.
# A custom type defines how values are serialized and deserialized,
# but does not interpret their meaning.
# ======================================================================

import o


class CustomType(o.Module):

	# register custom type by class name
	# ------------------------------------------------------------------
	def __init_subclass__(cls, **kwargs):
		super().__init_subclass__(**kwargs)
		o.types[cls.__name__] = cls 

	# Convert in-memory value to a storable representation.
	# Must return a DB-safe value (e.g. bytes, str, int).
	# ------------------------------------------------------------------
	@classmethod
	def serialize(cls, value):
		return value

	# Convert stored representation back to in-memory value.
	# ------------------------------------------------------------------
	@classmethod
	def deserialize(cls, value):
		return value
