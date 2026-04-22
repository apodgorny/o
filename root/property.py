import o


class Property(o.Module):

	def __init__(self, getter):
		self.getter = getter
		self.name   = getter.__name__

	def __get__(self, obj, cls=None):
		value = self

		if obj is not None:
			value = self.getter(obj)
			setattr(obj, self.name, value)

		return value


o_property = Property
