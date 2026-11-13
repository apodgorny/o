# ==============================================================================
# TRANSPORT SERVICE
# ==============================================================================
# Connect an ontology to the host-local invalidation relay through a Unix socket.
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

	# Locate the daemon relative to the installed O source library.
	# ----------------------------------------------------------------------
	def _daemon_path(self):
		root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
		return os.path.join(root, 'daemons', 'transport.py')

	# Use a private host-local directory that can also be mounted in containers.
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

	# Exchange newline-delimited frames before exposing the connection.
	# ----------------------------------------------------------------------
	def _connect(self):
		connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		connection.settimeout(0.2)
		deadline = time.monotonic() + 4.0
		started  = False
		ready    = False

		while not self._closed.is_set() and not ready and time.monotonic() < deadline:
			try:
				connection.connect(self.socket_path)
				ready = True
			except (ConnectionRefusedError, FileNotFoundError):
				if not started:
					daemon = self._daemon_path()

					if not os.path.isfile(daemon):
						raise FileNotFoundError(f'O Transport daemon not installed: {daemon}')

					subprocess.Popen(
						[sys.executable, daemon, self.socket_path],
						stdin             = subprocess.DEVNULL,
						stdout            = subprocess.DEVNULL,
						stderr            = subprocess.DEVNULL,
						close_fds         = True,
						start_new_session = True,
					)
					started = True

				time.sleep(0.02)

		if not ready:
			connection.close()
			raise ConnectionError(f'O Transport daemon did not start: {self.socket_path}')

		try:
			connection.sendall(json.dumps(['join', self.path]).encode('utf-8') + b'\n')
			buffer = bytearray()

			while b'\n' not in buffer and len(buffer) <= 1048576:
				data = connection.recv(65536)

				if not data:
					raise ConnectionError('O Transport daemon closed during handshake')

				buffer.extend(data)

			frame, _, remainder = buffer.partition(b'\n')

			if json.loads(frame) != ['ready', self.path]:
				raise ConnectionError('O Transport daemon rejected ontology')

			connection.settimeout(0.2)

			with self._lock:
				if not self._closed.is_set():
					self._connection = connection
				else:
					connection.close()

			# Reconnects must notify subscribers; initial startup needs only a
			# synchronous cache refresh before O.start() returns.
			# --------------------------------------------------------------
			if not self._closed.is_set():
				if self._ever_connected:
					self.receive(frozenset({0}))
				else:
					o.services.Cache.invalidate_all()

				self._ever_connected = True
				self._connected.set()

		except Exception:
			connection.close()
			raise

		return remainder

	# Drop only the connection that was actually lost.
	# ----------------------------------------------------------------------
	def _disconnect(self, connection):
		with self._lock:
			if self._connection is connection:
				self._connection = None
				self._connected.clear()
				connection.close()

	# Receive frames, restoring the connection when the daemon disappears.
	# ----------------------------------------------------------------------
	def _run(self, first_buffer):
		buffer = bytearray(first_buffer)

		while not self._closed.is_set():
			with self._lock:
				connection = self._connection

			if connection is None:
				try:
					buffer = bytearray(self._connect())
				except (OSError, ConnectionError, ValueError):
					if not self._closed.wait(0.1):
						self._connected.clear()
			else:
				try:
					data = connection.recv(65536)
				except socket.timeout:
					data = None
				except OSError:
					data = b''

				if data == b'':
					self._disconnect(connection)
				elif data is not None:
					buffer.extend(data)

					if len(buffer) > 1048576:
						self._disconnect(connection)
					else:
						while b'\n' in buffer:
							frame, _, rest = buffer.partition(b'\n')
							buffer[:] = rest

							try:
								message = json.loads(frame)
							except (ValueError, UnicodeDecodeError):
								self._disconnect(connection)
								break

							if (
								isinstance(message, list)
								and len(message) == 3
								and message[0] == 'invalidate'
								and message[1] == self.path
								and isinstance(message[2], list)
								and message[2]
								and all(type(id) is int and id >= 0 for id in message[2])
							):
								self.receive(frozenset(message[2]))
							else:
								self._disconnect(connection)
								break

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Start an automatic daemon connection for a canonical LMDB path.
	# ----------------------------------------------------------------------
	def initialize(self, path, sync):
		self.path            = os.path.realpath(path)
		self.sync            = sync
		self.socket_path     = self._socket_path()
		self._connection     = None
		self._lock           = threading.Lock()
		self._connected      = threading.Event()
		self._closed         = threading.Event()
		self._ever_connected = False

		buffer = self._connect()
		self._worker = threading.Thread(target=self._run, args=(buffer,), name='o-transport', daemon=True)
		self._worker.start()
		atexit.register(self.close)

	# Send only changed owner IDs; disk values remain in LMDB.
	# ----------------------------------------------------------------------
	def send(self, ids):
		ids = frozenset(ids)

		if ids and all(type(id) is int and id >= 0 for id in ids):
			message = json.dumps(
				['change', self.path, [0] if 0 in ids else sorted(ids)],
				separators=(',', ':'),
			).encode('utf-8') + b'\n'

			with self._lock:
				connection = self._connection

				if connection is not None:
					try:
						connection.sendall(message)
					except OSError:
						self._connection = None
						self._connected.clear()
						connection.close()
		else:
			raise ValueError('Transport invalidations must contain non-negative integer IDs')

	# Forward remote invalidations to local Sync without republishing them.
	# ----------------------------------------------------------------------
	def receive(self, ids):
		self.sync.receive(ids)

	# Close the local client; the daemon exits after the last peer leaves.
	# ----------------------------------------------------------------------
	def close(self):
		self._closed.set()

		with self._lock:
			connection      = self._connection
			self._connection = None

		if connection is not None:
			connection.close()

		if hasattr(self, '_worker') and self._worker is not threading.current_thread():
			self._worker.join(timeout=1.0)
