import time
from tqdm import tqdm

import o


class TestPerformanceSetattr(o.Tester):

	# Trigger object setattr
	# ----------------------------------------------------------------------
	@classmethod
	def trigger_object_setattr(cls, n, root_cls):
		APerfAttr = root_cls.extend('APerfAttr', x=int, y=int)
		x         = APerfAttr(x=1, y=2)

		for i in tqdm(range(n), desc='object_setattr'):
			x.x = i
			x.y = i + 1

	# Performance test
	# ----------------------------------------------------------------------
	@classmethod
	def test_performance(cls):
		size      = 5000
		n_attr    = size
		run_id    = time.time_ns()
		root_name = f'APerfRun{run_id}'
		PerfRoot  = o.T.extend(root_name)

		o.Timer.reset()
		# with o.services.Memory.write():
			# cls.trigger_object_setattr(n_attr, PerfRoot)

		cls.trigger_object_setattr(n_attr, PerfRoot)

		print()
		print(f'n_attr = {n_attr}')
		print()

		o.Timer.report()


if __name__ == '__main__':
	TestPerformanceSetattr.test_performance()
