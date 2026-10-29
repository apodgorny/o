# ======================================================================
# Verify checkpoint rollback and restart across persistent o objects.
# ======================================================================

import os
import subprocess
import sys
import tempfile

import o


class TestJobRollback(o.Tester):

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Recover a failed checkpoint and replay after a manual rollback.
	# ----------------------------------------------------------------------
	@classmethod
	def test_rollback(cls):
		with tempfile.TemporaryDirectory() as path:
			os.mkdir(os.path.join(path, 'root'))
			with open(os.path.join(path, 'app.py'), 'w') as stream:
				stream.write('import a\n\nclass App(a.A):\n\tpass\n')
			with open(os.path.join(path, 'root', 'trial.py'), 'w') as stream:
				stream.write('''import os
import o

Actor = o.T.extend('RollbackActor', name=str)

class Trial(o.Job):
	def define(self):
		self.checkpoint('one', self._one)
		self.checkpoint('two', self._two)
		self.checkpoint('three', self._three)

	async def _one(self):
		assert 'value' not in self.data
		self.data['actor'] = Actor(name='Mira')
		self.data['value'] = 'one'
		if os.path.exists(os.environ['FAIL_ONE']):
			self.data['value'] = 'partial-first'
			raise ValueError('first checkpoint failed')

	async def _two(self):
		assert self.data['value'] == 'one'
		self.data['value'] = 'partial'
		if os.path.exists(os.environ['FAIL_TWO']):
			raise ValueError('failed on purpose')
		self.data['value'] = 'two'

	async def _three(self):
		self.data['value'] = 'three'
''')
			source = '''import asyncio
import os
import sys

import o

o.start(os.path.join(sys.argv[1], 'ontology'))
import app

async def verify():
	job = app.Trial()
	job.prompt = 'original'
	os.environ['FAIL_ONE'] = os.path.join(sys.argv[1], 'fail-one')
	fail = os.path.join(sys.argv[1], 'fail-two')
	with open(fail, 'w') as stream:
		stream.write('fail')

	try:
		await job.run()
	except ValueError:
		pass
	else:
		raise AssertionError('Checkpoint two should fail')

	assert job.completed == ('one',)
	assert job.status == 'failed'
	assert job.data['value'] == 'partial'
	root = job.directory.get_path()
	initial = os.path.join(root, 'checkpoints', '000_initial', 'snapshot.msgpack')
	first = os.path.join(root, 'checkpoints', '001_one', 'snapshot.msgpack')
	second = os.path.join(root, 'checkpoints', '002_two', 'snapshot.msgpack')
	third = os.path.join(root, 'checkpoints', '003_three', 'snapshot.msgpack')
	log = os.path.join(root, 'checkpoints', '002_two', 'log.txt')
	assert os.path.isfile(initial) and os.path.isfile(first)
	assert not os.path.exists(second)
	with open(log) as stream:
		failed_log = stream.read()
	assert 'failed on purpose' in failed_log

	os.unlink(fail)
	await job.run()
	assert job.completed == ('one', 'two', 'three')
	assert job.status == 'complete'
	assert job.data['value'] == 'three'
	assert job.data['actor'].name == 'Mira'
	assert os.path.isfile(second) and os.path.isfile(third)
	with open(log) as stream:
		assert stream.read().startswith(failed_log)

	job.rollback('one')
	assert job.status == 'created'
	assert job.completed == ('one',)
	assert job.data['value'] == 'one'
	assert job.data['actor'].name == 'Mira'
	assert os.path.isfile(second) and os.path.isfile(third)
	with open(os.path.join(root, 'log.txt')) as stream:
		assert 'rolled back to completed checkpoint one' in stream.read()

	await job.run()
	assert job.completed == ('one', 'two', 'three')
	assert job.data['value'] == 'three'
	job.erase()

	job = app.Trial()
	job.prompt = 'seed'
	with open(os.environ['FAIL_ONE'], 'w') as stream:
		stream.write('fail')
	try:
		await job.run()
	except ValueError:
		pass
	else:
		raise AssertionError('First checkpoint should fail')
	assert job.completed == ()
	assert job.status == 'failed'
	assert job.data['value'] == 'partial-first'
	os.unlink(os.environ['FAIL_ONE'])
	await job.run()
	assert job.completed == ('one', 'two', 'three')
	assert job.data['value'] == 'three'
	assert job.prompt == 'seed'
	job.erase()

asyncio.run(verify())
'''
			environment = dict(os.environ)
			environment['PYTHONPATH'] = os.pathsep.join((
				path, os.path.dirname(o.__lib_file__),
				os.path.join(os.path.dirname(os.path.dirname(o.__lib_file__)), 'almasi'),
			))
			result = subprocess.run([sys.executable, '-c', source, path], env=environment, capture_output=True, text=True, timeout=30)
			assert result.returncode == 0, result.stdout + result.stderr


if __name__ == '__main__':
	TestJobRollback.run()
