import o


class TestBuiltins(o.Tester):
	RUNTIME_PREFIX = 'o_builtins_'

	# ----------------------------------------------------------------------
	@classmethod
	def test_atomic_builtin_method_returns_python_value(cls):
		state = cls._patch_runtime()

		try:
			x      = o.Str('alex')
			result = x.upper()

			assert result == 'ALEX'
			assert x.__value__ == 'alex'
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_builtin_method_mutates_in_place(cls):
		state = cls._patch_runtime()

		try:
			x      = o.List([3, 1, 2])
			result = x.sort()

			assert result is None
			assert list(x) == [1, 2, 3]
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_builtin_method_mutates_and_returns_python_value(cls):
		state = cls._patch_runtime()

		try:
			x      = o.List([1, 2, 3])
			result = x.pop()

			assert result == 3
			assert list(x) == [1, 2]
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_builtin_method_mutates_and_returns_python_value(cls):
		state = cls._patch_runtime()

		try:
			x      = o.Dict({'a': 1, 'b': 2})
			result = x.pop('a')

			assert result == 1
			assert dict(x.items()) == {'b': 2}
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestBuiltins.run()
