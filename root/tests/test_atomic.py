import o


class TestAtomic(o.Tester):
	RUNTIME_PREFIX = 'o_atomic_'

	# ----------------------------------------------------------------------
	@classmethod
	def test_atomic_roundtrip(cls):
		state = cls._patch_runtime()

		try:
			values = [
				(o.Int, 7),
				(o.Str, 'alex'),
				(o.Bool, True),
				(o.Float, 1.5),
				(o.Null, None),
			]

			for Type, value in values:
				x = Type(value)

				assert x.__zone__.prefix == f'{x.__proto__}.'
				assert x.__value__ == value
				assert x.__zone__.get('__value__') == value
				assert o.services.Memory.get(f'{x.__proto__}.__value__') == value
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_atomic_type_validation(cls):
		state = cls._patch_runtime()

		try:
			raised_int  = False
			raised_str  = False
			raised_bool = False

			try:
				o.Int('7')
			except TypeError:
				raised_int = True

			try:
				o.Str(7)
			except TypeError:
				raised_str = True

			try:
				o.Bool('True')
			except TypeError:
				raised_bool = True

			assert raised_int == True
			assert raised_str == True
			assert raised_bool == True
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestAtomic.run()
