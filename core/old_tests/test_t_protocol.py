import o


class TestTProtocol(o.Test):

	@classmethod
	def test_reflected_numeric_operators(cls):
		x = o.Int(5)

		assert (2 + x) == 7
		assert (10 - x) == 5
		assert (3 * x) == 15
		assert (20 / x) == 4.0

	@classmethod
	def test_comparisons_against_python_values(cls):
		x = o.Int(5)

		assert (x == 5) == True
		assert (x != 4) == True
		assert (x > 4) == True
		assert (x >= 5) == True
		assert (x < 6) == True
		assert (x <= 5) == True

	@classmethod
	def test_object_attribute_protocol(cls):
		x = o.Object({'a': 1})

		assert x.a == 1
		assert x.__cast_out__() == {'a': 1}

		x.b = 2

		assert x.b == 2
		assert x.__cast_out__() == {'a': 1, 'b': 2}

		del x.a

		assert x.__cast_out__() == {'b': 2}

		try:
			x.a
			assert False
		except AttributeError:
			pass

	@classmethod
	def test_delegated_mutating_and_non_mutating_methods(cls):
		l = o.List([3, 1, 2])

		l.sort()

		assert l.__cast_out__() == [1, 2, 3]
		assert l.count(2) == 1
		assert l.__cast_out__() == [1, 2, 3]


if __name__ == '__main__':
	TestTProtocol.run()
