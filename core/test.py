import inspect

import o


class Test(o.Module):

	@classmethod
	def run(cls):
		for name in dir(cls):
			if name.startswith('test_'):
				method = getattr(cls, name)
				if callable(method):
					method()
					print(f'{cls.__name__}.{name} passed')