import o


def to_human(s):
	return o.String.camel_to_snake(s).replace('_', ' ').replace('test', '').strip().capitalize()


class Test(o.Module):

	# ----------------------------------------------------------------------
	@classmethod
	def run(cls):
		run_all = cls is o.Test

		# Run all tests
		# - - - - - - - - - - - - - - - - - - - -
		if run_all:
			n = 0
			for test in o.tests:
				if test.name.startswith('test_'):
					t_cls = test.load()

					if isinstance(t_cls, type) and issubclass(t_cls, o.Test) and t_cls is not o.Test:
						t_cls.run()
					n += 1
			return n

		# Run current test class only
		# - - - - - - - - - - - - - - - - - - - -
		else:
			test_class_name = to_human(cls.__name__)

			print('=' * 70)
			print(f'{test_class_name}: {cls.__o_module__}')
			print('=' * 70)

			for name, member in cls.__dict__.items():
				if name.startswith('test_') and isinstance(member, classmethod):
					method = getattr(cls, name)
					method()
					print(f' ✅ {to_human(name)}')
			return 1
				


if __name__ == '__main__':
	n = o.Test.run()
	print(f'\n ✅ All {n} tests passed')
	print()
	o.Timer.report()