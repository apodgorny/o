import inspect

import o


def to_human(s):
	return o.String.camel_to_snake(s).replace('_', ' ').replace('test', '').strip().capitalize()

class Test(o.Module):

	@classmethod
	def run(cls):
		for test in o.tests:
			t_cls = test.load()
			if isinstance(t_cls, type) and issubclass(t_cls, o.Test):
				test_class_name = to_human(t_cls.__name__)
				print('=' * 70)
				print(f'{test_class_name}: {t_cls.__o_module__}')
				print('=' * 70)
				for name, member in t_cls.__dict__.items():
					if not name.startswith('_') and isinstance(member, classmethod):
						method = getattr(t_cls, name)
						method()
						print(f' ✅ {to_human(name)}')

if __name__ == '__main__':
	o.Test.run()
	print('\n ✅ All tests passed')