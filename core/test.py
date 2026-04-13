import o


def to_human(s):
	if s.lower() == 'test':
		return 'Test'
	return o.String.camel_to_snake(s).replace('_', ' ').replace('test', '').strip().capitalize()


class Test(o.Module):

	# ----------------------------------------------------------------------
	@classmethod
	def run(cls):
		run_all = cls is o.Test
		result  = None

		# Run all tests
		# - - - - - - - - - - - - - - - - - - - -
		if run_all:
			test_count   = 0
			method_count = 0

			for test in o.tests:
				if test.name.startswith('test'):
					t_cls = test.load()

					if isinstance(t_cls, type) and issubclass(t_cls, o.Test) and t_cls is not o.Test:
						method_count += t_cls.run()
						test_count   += 1

			result = test_count, method_count

		# Run current test class only
		# - - - - - - - - - - - - - - - - - - - -
		else:
			test_class_name = to_human(cls.__name__)
			method_count    = 0

			print('=' * 70)
			print(f'{test_class_name}: {cls.__o_module__}')
			print('=' * 70)

			for name, member in cls.__dict__.items():
				if name.startswith('test') and isinstance(member, classmethod):
					method = getattr(cls, name)
					method()
					method_count += 1
					print(f' ✅ {to_human(name)}')

			result = method_count

		return result


if __name__ == '__main__':
	test_count, method_count = o.Test.run()
	print(f'\n ✅ All {test_count} tests passed ({method_count} methods ran)')
	print()
	o.Timer.report()
