# ==============================================================================
# TRANSPORT SERVICE
# ==============================================================================
# Deliver O invalidations between local processes over Unix domain sockets.
# ==============================================================================

import atexit
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time

import o


class Transport(o.Service):

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Locate the stand-alone daemon beside the Almasi O root directory.
	# ----------------------------------------------------------------------
	def _daemon_path(self):
		root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
		return os.path.join(root, 'daemons', 'transport.py')

	# Keep one private socket directory per host user.
	# ----------------------------------------------------------------------
	def _socket_path(self):
		directory = os.environ.get('O_TRANSPORT_DIR')

		if directory is None:
			directory = os.path.join(tempfile.gettempdir(), f'o-transport-{os.getuid()}')

		directory = os.path.realpath(directory)
		os.makedirs(directory, mode=0o700, exist_ok=True)
		state = os.stat(directory)

		if state.st_uid != os.getuid() or state.st_mode & 0o077:
			raise PermissionError(f'Insecure O transport directory: {directory}')

		return os.path.join(directory, 'transport.sock')

	# Start the relay once if absent, then register this ontology.
	# ----------------------------------------------------------------------
	def _connect(self):
		connection = None
		started    = False
		deadline   = time.monotonic() + 4.0

		while connection is None and not self._closed.is_set() and time.monotonic() < deadline:
			candidate = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
			candidate.settimeout(1.0)

			try:
				candidate.connect(self.socket_path)
			except (FileNotFoundError, ConnectionRefusedError):
				candidate.close()

				if not started:
					subprocess.Popen(
						[sys.executable, self._daemon_path(), self.socket_path],
						stdin             = subprocess.DEVNULL,
						stdout            = subprocess.DEVNULL,
						stderr            = subprocess.DEVNULL,
						close_fds         = True,
						start_new_session = True,
					)
					started = True

				time.sleep(0.02)
			else:
				connection = candidate

		if connection is None:
			raise ConnectionError(f'Cannot connect to O Transport: {self.socket_path}')

		try:
			reader = connection.makefile('rb')
			connection.sendall(json.dumps(self.path).encode('utf-8') + b'\n')

			if json.loads(reader.readline(1048577)) is not True:
				raise ConnectionError('O Transport rejected ontology')

			connection.settimeout(None)
		except Exception:
			connection.close()
			raise

		return connection, reader

	# Receive invalidations without retransmitting them.
	# ----------------------------------------------------------------------
	def _run(self, connection, reader):
		while not self._closed.is_set():
			if connection is None:
				try:
					connection, reader = self._connect()
				except (OSError, ValueError, ConnectionError):
					self._closed.wait(0.2)
				else:
					with self._lock:
						self._connection = connection

					# A disconnected writer may have missed notifying peers.
					# ------------------------------------------------------
					self.sync.receive(None)
					self.send(None)
			else:
				try:
					frame = reader.readline(1048577)

					if not frame or len(frame) > 1048576:
						raise ConnectionError('Invalid O Transport frame')

					ids = json.loads(frame)

					if ids is not None:
						if not isinstance(ids, list) or not ids or any(type(id) is not int or id <= 0 for id in ids):
							raise ValueError('Invalid O Transport IDs')

						ids = frozenset(ids)

					self.sync.receive(ids)
				except (OSError, ValueError, ConnectionError):
					with self._lock:
						if self._connection is connection:
							self._connection = None

					reader.close()
					connection.close()
					connection = None

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Join the relay before startup returns; reconnect in a background thread.
	# ----------------------------------------------------------------------
	def initialize(self, path, sync):
		self.path        = os.path.realpath(path)
		self.sync        = sync
		self.socket_path = self._socket_path()
		self._lock       = threading.Lock()
		self._closed     = threading.Event()

		connection, reader = self._connect()
		self._connection  = connection
		o.services.Cache.invalidate_all()
		self._worker = threading.Thread(
			target = self._run,
			args   = (connection, reader),
			name   = 'o-transport',
			daemon = True,
		)
		self._worker.start()
		atexit.register(self.close)

	# Send one owner-ID set, or None for full invalidation.
	# ----------------------------------------------------------------------
	def send(self, ids):
		if ids is None:
			payload = None
		elif isinstance(ids, (set, frozenset)) and ids and all(type(id) is int and id > 0 for id in ids):
			payload = sorted(ids)
		else:
			raise ValueError('Transport expects None or a nonempty set of positive IDs')

		message = json.dumps(payload, separators=(',', ':')).encode('utf-8') + b'\n'

		with self._lock:
			connection = self._connection

			if connection is not None:
				try:
					connection.sendall(message)
				except OSError:
					self._connection = None
					connection.close()

	# Disconnect; the relay will exit when its final client is gone.
	# ----------------------------------------------------------------------
	def close(self):
		self._closed.set()

		with self._lock:
			connection      = self._connection
			self._connection = None

		if connection is not None:
			try:
				connection.shutdown(socket.SHUT_RDWR)
			except OSError:
				pass

			connection.close()

		if hasattr(self, '_worker') and self._worker is not threading.current_thread():
			self._worker.join(timeout=1.0)
