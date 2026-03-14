import o


class Str(o.Many):
	__annotation__ = str

	# ------------------------------------------------------------------
	def __init__(self, data=None):
		data = '' if data is None else data
		super().__init__(data, word='I')

	def __hash__(self):
		return hash(self.__cast_out__())

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS - ITEM-WISE
	# ======================================================================

	# ----------------------------------------------------------------------
	def __get__(self, index):
		if not isinstance(index, int):
			raise TypeError(index)

		try:
			return self.__items__[index][0]
		except IndexError:
			raise IndexError(index)

	# ----------------------------------------------------------------------
	def __set__(self, index, value):
		raise TypeError('Str is immutable')

	# ----------------------------------------------------------------------
	def __unset__(self, index):
		raise TypeError('Str is immutable')

	# ======================================================================
	# CUSTOM FRAMEWORK METHODS - SELF-WISE
	# ======================================================================

	# ----------------------------------------------------------------------
	def __cast_in__(self, data):
		if not isinstance(data, str):
			raise TypeError('Str expects str')

		self.__items__ = [(ord(c),) for c in data]

	# ----------------------------------------------------------------------
	def __cast_out__(self):
		return ''.join(chr(code[0]) for code in self.__items__)

	# ----------------------------------------------------------------------
	def __read__(self):
		self.__items__ = super().__read__()

	# ----------------------------------------------------------------------
	def __write__(self):
		return super().__write__()

	# ----------------------------------------------------------------------
	def __delete__(self):
		return super().__delete__()

	# ----------------------------------------------------------------------
	def __clear__(self):
		raise TypeError('Str is immutable')

	# ======================================================================
	# PYTHON INTERFACE
	# ======================================================================

	# ----------------------------------------------------------------------
	def __getitem__(self, index):

		if isinstance(index, slice):
			start, stop, step = index.indices(len(self))
			codes = self.__items__[start:stop:step]
			return ''.join(chr(code[0]) for code in codes)

		return chr(self.__get__(index))

	# ----------------------------------------------------------------------
	def __len__(self):
		return len(self.__items__)

	# ----------------------------------------------------------------------
	def __iter__(self):
		for code in self.__items__:
			yield chr(code[0])

	# ----------------------------------------------------------------------
	def __str__(self):
		return self.__cast_out__()

	# ----------------------------------------------------------------------
	def __repr__(self):
		return f"Str({self.__cast_out__()!r})"

	# ----------------------------------------------------------------------
	def __add__(self, other):

		if isinstance(other, str):
			other = Str(other)

		if not isinstance(other, Str):
			return NotImplemented

		return self.__cast_out__() + other.__cast_out__()
