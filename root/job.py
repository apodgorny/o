# ======================================================================
# Own persistent job data, ordered checkpoints and job files.
# ======================================================================

import inspect
import logging
import os
import shutil
import sys
import time
import warnings
import weakref

import a, o


class Job(a.Logger):

	_instances = weakref.WeakValueDictionary()

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Keep one live instance for each job and subclass.
	# ----------------------------------------------------------------------
	def __new__(cls, job_id=None):
		lib  = cls._library()
		jobs = cls._jobs(create=job_id is None)

		if job_id is None:
			with o.services.Memory.write():
				counter = int(getattr(o.V, 'job_counter', 0))
				while True:
					counter += 1
					job_id   = f'{counter:03d}'
					path     = lib.join('jobs', job_id)
					if job_id not in jobs and not os.path.lexists(path):
						break

				lib.mkdir('jobs', job_id)
				o.V.job_counter = counter
				jobs[job_id] = {
					'status'    : 'created',
					'completed' : {},
					'data'      : {},
				}

		if jobs is not None and job_id in jobs:
			key      = (cls, lib.__path__, job_id)
			instance = Job._instances.get(key)

			if instance is None:
				instance = super().__new__(cls)
				object.__setattr__(instance, '_id', job_id)
				object.__setattr__(instance, '_lib', lib)
				object.__setattr__(instance, '_key', key)
				object.__setattr__(instance, '_running', False)
				Job._instances[key] = instance
		else:
			raise KeyError(f'Unknown job: {job_id}')

		return instance

	# Register the workflow once for each live instance.
	# ----------------------------------------------------------------------
	def __init__(self, job_id=None):
		if not self.__dict__.get('_initialized', False):
			object.__setattr__(self, '_checkpoints', {})
			try:
				if self.safeguard():
					result = self.define()
					if not inspect.isawaitable(result):
						object.__setattr__(self, '_initialized', True)
					else:
						raise TypeError('Job.define() must be synchronous')
			finally:
				if sys.exception() is not None:
					Job._instances.pop(self._key, None)

	# Store application fields directly in the persistent data dictionary.
	# ----------------------------------------------------------------------
	def __setattr__(self, name, value):
		if name.startswith('_'):
			object.__setattr__(self, name, value)
		elif not hasattr(type(self), name):
			self._node()['data'][name] = value
		else:
			raise AttributeError(f'Reserved Job attribute: {name}')

	# Remove an application field through the ontology lifecycle.
	# ----------------------------------------------------------------------
	def __delattr__(self, name):
		data = self._node()['data']

		if not name.startswith('_') and not hasattr(type(self), name) and name in data:
			del data[name]
		else:
			raise AttributeError(name)

	# Read application fields from the persistent data dictionary.
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		data = self._node()['data']

		if not name.startswith('_') and name in data:
			result = data[name]
		else:
			raise AttributeError(name)

		return result

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Resolve the application that owns the job subclass.
	# ----------------------------------------------------------------------
	@classmethod
	def _library(cls):
		module = sys.modules.get(cls.__module__)
		lib    = getattr(module, '__lib__', None)

		if lib is not None:
			result = lib
		else:
			raise RuntimeError('Job subclass must be loaded through Almasi')

		return result

	# Access the persistent collection, creating it for a new job.
	# ----------------------------------------------------------------------
	@staticmethod
	def _jobs(create=False):
		if create and not hasattr(o.V, 'jobs'):
			o.V.jobs = {}

		result = o.V.jobs if hasattr(o.V, 'jobs') else None
		return result

	# Resolve the job's live ontology node.
	# ----------------------------------------------------------------------
	def _node(self):
		jobs = self._jobs()

		if jobs is not None and self._id in jobs:
			result = jobs[self._id]
		else:
			raise ReferenceError(f'Job {self._id} has been erased')

		return result

	# Reflect agent activity in the active checkpoint's existing spinner.
	# ----------------------------------------------------------------------
	def _log_event(self, record):
		spinner = self.__dict__.get('_progress_spinner')
		if spinner is not None:
			event    = getattr(record, 'event', None)
			activity = getattr(record, 'activity', None)
			if event == 'agent_start':
				self._agents[activity] = (record.agent_name, getattr(record, 'model', None))
			elif event == 'agent_end':
				self._agents.pop(activity, None)
			elif event == 'model_start':
				agent = self._agents.get(activity, (None, None))[0]
				self._agents[activity] = (agent, record.model)
			elif event == 'model_end':
				if activity in self._agents:
					agent = self._agents[activity][0]
					if agent is None:
						self._agents.pop(activity)
					else:
						self._agents[activity] = (agent, None)

			labels = [self._progress_label]
			if self._agents:
				labels.extend(value for value in next(reversed(self._agents.values())) if value)
			spinner.update(' → '.join(labels))

	# Checkpoint names must also be safe directory components.
	# ----------------------------------------------------------------------
	@staticmethod
	def _is_checkpoint_name(name):
		result = isinstance(name, str) and bool(name) and os.path.basename(name) == name and name not in ('.', '..')
		return result

	# Reuse a checkpoint directory by name when workflow positions change.
	# ----------------------------------------------------------------------
	def _checkpoint_directory(self, index, name):
		directory = self.directory.mkdir('checkpoints')
		matches   = [child.get_name() for child in directory if child.is_directory() and child.get_name().partition('_')[2] == name]
		folder    = matches[0] if matches else f'{index:03d}_{name}'
		result    = directory.mkdir(folder)
		return result

	# Resolve a checkpoint's snapshot file.
	# ----------------------------------------------------------------------
	def _snapshot_path(self, index, name):
		if index == 0:
			directory = self.directory.mkdir('checkpoints', '000_initial')
		else:
			directory = self._checkpoint_directory(index, name)
		result = os.path.join(directory.get_path(), 'snapshot.msgpack')
		return result

	# Save a fully typed copy of the job data atomically.
	# ----------------------------------------------------------------------
	def _save_snapshot(self, index, name):
		path = self._snapshot_path(index, name)
		temp = path + '.tmp'
		data = o.services.Memory.to_bytes(self.data.serialize())
		try:
			with open(temp, 'wb') as stream:
				stream.write(data)
				stream.flush()
				os.fsync(stream.fileno())
			os.replace(temp, path)
		finally:
			if os.path.exists(temp):
				os.unlink(temp)

	# Restore job data and mark later checkpoints incomplete.
	# ----------------------------------------------------------------------
	def _restore_snapshot(self, index, name):
		path = self._snapshot_path(index, name)
		with open(path, 'rb') as stream:
			spec = o.services.Memory.from_bytes(stream.read())
		data = o.T.deserialize(spec)
		if not isinstance(data, o.Dict):
			raise TypeError('Job snapshot must contain an o.Dict')

		keep = set(list(self._checkpoints)[:index])
		with o.services.Memory.write():
			node = self._node()
			node['data'] = data
			for checkpoint in list(node['completed']):
				if checkpoint not in keep:
					del node['completed'][checkpoint]

	# Recover the latest contiguous successful checkpoint after failure.
	# ----------------------------------------------------------------------
	def _recover(self):
		index = 0
		name  = 'initial'
		for position, checkpoint in enumerate(self._checkpoints, 1):
			if checkpoint in self._node()['completed']:
				index = position
				name  = checkpoint
			else:
				break
		self._restore_snapshot(index, name)
		logging.info('Job %s recovered after checkpoint %s', self.id, name)

	# Record timing and failures without changing checkpoint identity.
	# ----------------------------------------------------------------------
	async def _run_checkpoint(self, index, name, method):
		label = f'Job_{self.id}::{name}'
		with self.logging(self._checkpoint_directory(index, name)):
			if name in self._node()['completed']:
				logging.info('Checkpoint %s skipped', name)
				a.Spinner.skipped(label)
			else:
				self._agents           = {}
				self._progress_label   = label
				self._progress_spinner = a.Spinner(
					text          = label,
					done_label    = f'✔ {label} — complete',
					failure_label = f'✘ {label} — failed',
				)
				started = time.monotonic()
				logging.info('Checkpoint %s started', name)
				try:
					async with self._progress_spinner:
						try:
							await method()
							self._save_snapshot(index, name)
							self._node()['completed'][name] = True
						finally:
							if sys.exception() is None:
								logging.info('Checkpoint %s complete; seconds=%.3f', name, time.monotonic() - started)
							else:
								logging.exception('Checkpoint %s failed; seconds=%.3f', name, time.monotonic() - started)
				finally:
					self._progress_spinner = None
					self._agents           = {}






	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Identify the persisted job.
	# ----------------------------------------------------------------------
	@property
	def id(self):
		return self._id

	# Access the job's persistent application data.
	# ----------------------------------------------------------------------
	@property
	def data(self):
		result = self._node()['data']
		return result

	# Access the physical directory owned by this job.
	# ----------------------------------------------------------------------
	@property
	def directory(self):
		self._node()
		result = self._lib.mkdir('jobs', self._id)
		return result

	# Read the persisted execution status.
	# ----------------------------------------------------------------------
	@property
	def status(self):
		result = self._node()['status']
		return result

	# List completed checkpoints in their stored order.
	# ----------------------------------------------------------------------
	@property
	def completed(self):
		result = tuple(self._node()['completed'].keys())
		return result

	# Prevent overlapping work on the same job.
	# ----------------------------------------------------------------------
	def safeguard(self):
		result = not self._running
		if not result:
			warnings.warn('Job is already running', RuntimeWarning, stacklevel=2)
		return result

	# Register checkpoints in execution order.
	# ----------------------------------------------------------------------
	def checkpoint(self, name, method):
		if self.safeguard():
			if self._is_checkpoint_name(name):
				if name not in self._checkpoints:
					if callable(method):
						self._checkpoints[name] = method
					else:
						raise TypeError(f'Checkpoint {name} must be callable')
				else:
					raise ValueError(f'Duplicate checkpoint: {name}')
			else:
				raise ValueError('Checkpoint name must be a nonempty string')

	# Resume checkpoints with scoped file logs and one progress display.
	# ----------------------------------------------------------------------
	async def run(self):
		if self.safeguard():
			self._running = True
			try:
				with self.logging(self.directory):
					try:
						if self.status in ('failed', 'running'):
							self._recover()
						elif not self.completed and not os.path.isfile(self._snapshot_path(0, 'initial')):
							self._save_snapshot(0, 'initial')
						self._node()['status'] = 'running'
						logging.info('Job %s started', self.id)
						for index, (name, method) in enumerate(self._checkpoints.items(), 1):
							await self._run_checkpoint(index, name, method)
						self._node()['status'] = 'complete'
						logging.info('Job %s complete', self.id)
					finally:
						if sys.exception() is not None:
							logging.exception('Job %s failed', self.id)
			finally:
				self._running = False
				if sys.exception() is not None:
					jobs = self._jobs()
					if jobs is not None and self._id in jobs:
						self._node()['status'] = 'failed'

	# Restore a successful checkpoint and leave execution paused.
	# ----------------------------------------------------------------------
	def rollback(self, name):
		if not self.safeguard():
			raise RuntimeError('Cannot rollback a running job')
		if name == 'initial':
			index = 0
		elif name in self._checkpoints:
			if name not in self._node()['completed']:
				raise ValueError(f'Checkpoint has no successful snapshot: {name}')
			index = list(self._checkpoints).index(name) + 1
		else:
			raise KeyError(f'Unknown checkpoint: {name}')
		with self.logging(self.directory):
			self._restore_snapshot(index, name)
			self._node()['status'] = 'created'
			target = 'initial state' if index == 0 else f'completed checkpoint {name}'
			logging.warning('Job %s rolled back to %s', self.id, target)

	# Erase the job's files and unlink its persistent branch.
	# ----------------------------------------------------------------------
	def erase(self):
		self._node()
		path = self._lib.join('jobs', self._id)

		if not os.path.islink(path):
			if os.path.isdir(path):
				shutil.rmtree(path)
			del self._jobs()[self._id]
			o.services.Garbage.collect()
			Job._instances.pop(self._key, None)
		else:
			raise ValueError(f'Refusing to erase symbolic link: {path}')
