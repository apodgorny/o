# ======================================================================
# Exercise native persistent jobs in isolated application processes.
# ======================================================================

import os
import subprocess
import sys
import tempfile

import o


class TestJob(o.Tester):

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Keep creation, recovery, persistence and erasure within the Job contract.
	# ----------------------------------------------------------------------
	@classmethod
	def test_lifecycle(cls):
		with tempfile.TemporaryDirectory() as path:
			os.mkdir(os.path.join(path, 'root'))
			with open(os.path.join(path, 'app.py'), 'w') as output:
				output.write('import a\n\nclass App(a.A):\n\tpass\n')
			with open(os.path.join(path, 'root', 'trial.py'), 'w') as output:
				output.write('''import asyncio
import logging
import os
import o

class Trial(o.Job):
	def define(self):
		self.checkpoint('first', self._first)
		if os.environ.get('EXTRA'):
			self.checkpoint('added', self._added)
		self.checkpoint('second', self._second)

	async def _first(self):
		self.first_runs = getattr(self, 'first_runs', 0) + 1
		logging.info('first %s', self.id)
		await asyncio.sleep(0)

	async def _added(self):
		self.added = True

	async def _second(self):
		logging.info('second %s', self.id)
		if getattr(self, 'artifact', False):
			logging.info('output', extra={'artifact_name': 'output_Trial.json', 'artifact_data': {'result': 1}})
		logging.info('older started', extra={'event': 'agent_start', 'activity': 1, 'agent_name': 'Older'})
		logging.info('model started', extra={'event': 'model_start', 'activity': 1, 'model': 'Local'})
		logging.info('newer started', extra={'event': 'agent_start', 'activity': 2, 'agent_name': 'Newer'})
		logging.info('newer ended', extra={'event': 'agent_end', 'activity': 2})
		logging.info('older ended', extra={'event': 'agent_end', 'activity': 1})
		if self.fail is False:
			self.second_runs = getattr(self, 'second_runs', 0) + 1
		else:
			raise ValueError('recoverable')
''')
			source = '''import asyncio
import os
import sys
from unittest.mock import patch
import a, o
from lib.logger import LogRoute

updates = []
original_update = a.Spinner.update

def update(self, text):
	updates.append(text)
	original_update(self, text)

a.Spinner.update = update
o.start(os.path.join(sys.argv[1], 'ontology'))
import app

Trial = app.Trial

async def first():
	job = Trial()
	job.fail = True
	job.prompt = 'saved'
	assert job.id == '001'
	assert Trial(job.id) is job
	try:
		await job.run()
	except ValueError:
		pass
	assert job.status == 'failed'
	assert job.completed == ('first',)
	assert os.path.isfile(job.directory.join('checkpoints', '000_initial', 'snapshot.msgpack'))
	assert os.path.isfile(job.directory.join('checkpoints', '001_first', 'snapshot.msgpack'))
	before = job.directory.join('checkpoints', '002_second', 'log.txt')
	with open(before) as stream:
		failed_log = stream.read()
	assert 'Traceback' in failed_log and 'recoverable' in failed_log
	assert updates.count('Job_001::second → Older → Local') == 2
	job.rollback('first')
	assert not os.path.exists(os.path.dirname(before))
	job.fail = False
	await job.run()
	assert job.first_runs == 1 and job.second_runs == 1
	assert job.status == 'complete'
	with open(before) as stream:
		assert 'recoverable' not in stream.read()
	assert os.path.isdir(job.directory.join('checkpoints', '001_first'))
	other = Trial()
	other.fail = False
	await asyncio.gather(job.run(), other.run())
	assert other.id == '002'
	assert 'first 002' not in job.directory.read('log.txt')
	assert 'first 001' not in other.directory.read('log.txt')
	with patch.object(Trial, '_checkpoint_directory', side_effect=OSError('directory failure')):
		try:
			await other.run()
		except OSError:
			pass
	assert other.status == 'failed'
	with open(other.directory.join('log.txt')) as stream:
		job_log = stream.read()
	assert 'directory failure' in job_log and 'Traceback' in job_log
	third = Trial()
	third.fail = True
	original_emit = LogRoute.emit

	def fail_log(handler, record):
		if record.getMessage().startswith('Checkpoint second failed'):
			raise OSError('log failure')
		else:
			original_emit(handler, record)

	with patch.object(LogRoute, 'emit', fail_log):
		try:
			await third.run()
		except OSError as error:
			assert isinstance(error.__context__, ValueError)
			assert str(error.__context__) == 'recoverable'
		else:
			raise AssertionError('Log failure was swallowed')
	assert third.status == 'failed' and third.completed == ('first',)
	third.rollback('first')
	third.fail = False
	third.artifact = True
	with patch.object(a.Logger, '_artifact', side_effect=OSError('artifact failure')):
		try:
			await third.run()
		except OSError:
			pass
		else:
			raise AssertionError('Artifact failure was swallowed')
	assert third.status == 'failed' and third.completed == ('first',)
	third.erase()

async def reopened():
	job = Trial('001')
	assert job.prompt == 'saved'
	assert job.completed == ('first', 'second')
	await job.run()
	assert job.added is True
	assert job.first_runs == 1 and job.second_runs == 1
	assert os.path.isdir(job.directory.join('checkpoints', '002_second'))
	assert job.completed == ('first', 'second', 'added')
	last = Trial()
	assert last.id == '004'
	last.erase()
	job.erase()
	try:
		job.data
	except ReferenceError:
		pass
	else:
		raise AssertionError('Erased reference is still usable')
	assert '001' not in o.V.jobs
	Trial('002').erase()

asyncio.run(reopened() if os.environ.get('EXTRA') else first())
'''
			environment = dict(os.environ)
			environment['PYTHONPATH'] = os.pathsep.join((path, os.path.dirname(o.__lib_file__), os.path.join(os.path.dirname(os.path.dirname(o.__lib_file__)), 'almasi')))
			for extra in ('', '1'):
				environment['EXTRA'] = extra
				result = subprocess.run([sys.executable, '-c', source, path], env=environment, capture_output=True, text=True, timeout=30)
				assert result.returncode == 0, result.stdout + result.stderr
				if extra:
					assert 'first — skipped' in result.stdout and 'added — complete' in result.stdout
