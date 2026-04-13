import o


class TestAtomicTypes(o.Test):

	@classmethod
	def test_bool_roundtrip_truthiness_and_delete(cls):
		x = o.Bool(True)
		y = o.Bool.instantiate(x.__id__)

		assert bool(x) == True
		assert y is x

		x.__write__(False)

		assert bool(x) == False
		assert bool(y) == False

		x.__delete__()

		try:
			bool(x)
			assert False
		except ValueError:
			pass

	@classmethod
	def test_float_roundtrip_and_arithmetic(cls):
		x = o.Float(1.5)
		y = o.Float.instantiate(x.__id__)

		assert float(x) == 1.5
		assert float(y) == 1.5
		assert (x + 0.5) == 2.0
		assert (2.0 - x) == 0.5

		x.__write__(2.5)

		assert float(x) == 2.5
		assert float(y) == 2.5

	@classmethod
	def test_null_roundtrip_truthiness_and_delete(cls):
		x = o.Null()
		y = o.Null.instantiate(x.__id__)
		id_ = x.__id__

		assert x.__cast_out__() is None
		assert y is x
		assert bool(x) == False

		x.__delete__()

		try:
			o.services.One.read(o.Null.__type_id__, id_)
			assert False
		except ValueError:
			pass


if __name__ == '__main__':
	TestAtomicTypes.run()
