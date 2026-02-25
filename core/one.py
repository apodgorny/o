import o


class One(o.Object):

	def __init__(self, word, id=None, data=None):
		if id is None and data is None:
			raise RuntimeError('Data and id can not both be None')

		o.services.One.define(self.__o_module__, self.__type_id__, word)
		self.__id__ = id

		if data is not None:
			self.__id__ = self.__write__(data)

	# ----------------------------------------------------------------------

	def __read__(self):
		return o.services.One.read(self.__type_id__, self.__id__)

	def __write__(self, data):
		return o.services.One.write(self.__type_id__, self.__id__, data)

	def __delete__(self):
		return o.services.One.delete(self.__type_id__, self.__id__)