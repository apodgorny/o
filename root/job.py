# ======================================================================
# Own persistent job data, ordered checkpoints and job files.
# ======================================================================

import inspect
import os
import shutil
import sys
import warnings
import weakref

import o


class Job(o.Module):

	_instances = weakref.WeakValueDictionary()

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

				os.makedirs(path)
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

	# Read application fields from the persistent data dictionary.
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		data = self._node()['data']

		if not name.startswith('_') and name in data:
			result = data[name]
		else:
			raise AttributeError(name)

		return result

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
		path = self._lib.join('jobs', self._id)
		os.makedirs(path, exist_ok=True)

		result = self._lib.Directory(self._lib, path, f'{self._lib.__name__}.jobs.{self._id}')
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
			if isinstance(name, str) and name:
				if name not in self._checkpoints:
					if callable(method):
						self._checkpoints[name] = method
					else:
						raise TypeError(f'Checkpoint {name} must be callable')
				else:
					raise ValueError(f'Duplicate checkpoint: {name}')
			else:
				raise ValueError('Checkpoint name must be a nonempty string')

	# Resume incomplete checkpoints and retain successful progress.
	# ----------------------------------------------------------------------
	async def run(self):
		if self.safeguard():
			self._running = True
			try:
				self._node()['status'] = 'running'
				for name, method in self._checkpoints.items():
					if name not in self._node()['completed']:
						await method()
						self._node()['completed'][name] = True
				self._node()['status'] = 'complete'
			finally:
				self._running = False
				if sys.exception() is not None:
					jobs = self._jobs()
					if jobs is not None and self._id in jobs:
						self._node()['status'] = 'failed'

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
