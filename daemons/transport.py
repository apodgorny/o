# ==============================================================================
# TRANSPORT DAEMON
# ==============================================================================
# Relay ontology invalidations among Unix socket peers sharing one LMDB path.
# ==============================================================================

import fcntl
import json
import os
import selectors
import socket
import sys

from time import monotonic


class Transport:

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Keep nonblocking socket peers and their receive/send buffers.
	# ----------------------------------------------------------------------
	def __init__(self, path, idle_timeout=3.0):
		self.path         = path
		self.idle_timeout = idle_timeout
		self.selector     = selectors.DefaultSelector()
		self.clients      = {}

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Remove a disconnected or misbehaving peer.
	# ----------------------------------------------------------------------
	def _drop(self, connection):
		if connection in self.clients:
			self.clients.pop(connection)
			self.selector.unregister(connection)
			connection.close()

	# Queue a frame without letting stalled clients consume unlimited RAM.
	# ----------------------------------------------------------------------
	def _queue(self, connection, frame):
		output = self.clients[connection]['output']

		if len(output) + len(frame) > 1048576:
			self._drop(connection)
		else:
			output.extend(frame)
			self.selector.modify(connection, selectors.EVENT_READ | selectors.EVENT_WRITE)

	# Accept a new connection without starting a dedicated thread.
	# ----------------------------------------------------------------------
	def _accept(self, listener):
		connection, _ = listener.accept()
		connection.setblocking(False)
		self.clients[connection] = {
			'path'   : None,
			'input'  : bytearray(),
			'output' : bytearray(),
		}
		self.selector.register(connection, selectors.EVENT_READ)

	# Validate one registration or invalidation and route it to matching peers.
	# ----------------------------------------------------------------------
	def _message(self, connection, frame):
		try:
			message = json.loads(frame)
		except (ValueError, UnicodeDecodeError):
			self._drop(connection)
		else:
			path = self.clients[connection]['path']

			if path is None:
				if isinstance(message, str) and os.path.isabs(message) and os.path.realpath(message) == message:
					self.clients[connection]['path'] = message
					self._queue(connection, b'true\n')
				else:
					self._drop(connection)
			elif message is None or (
				isinstance(message, list)
				and message
				and all(type(id) is int and id > 0 for id in message)
			):
				for peer, state in tuple(self.clients.items()):
					if peer is not connection and state['path'] == path:
						self._queue(peer, frame + b'\n')
			else:
				self._drop(connection)

	# Collect complete JSON-line frames; retain incomplete reads.
	# ----------------------------------------------------------------------
	def _read(self, connection):
		try:
			data = connection.recv(65536)
		except OSError:
			data = b''

		if not data:
			self._drop(connection)
		else:
			buffer = self.clients[connection]['input']
			buffer.extend(data)

			while connection in self.clients and b'\n' in buffer:
				frame, _, remainder = buffer.partition(b'\n')
				buffer[:] = remainder

				if len(frame) > 1048576:
					self._drop(connection)
				else:
					self._message(connection, frame)

			if connection in self.clients and len(buffer) > 1048576:
				self._drop(connection)

	# Resume a partial nonblocking write when the socket becomes writable.
	# ----------------------------------------------------------------------
	def _write(self, connection):
		output = self.clients[connection]['output']

		try:
			sent = connection.send(output)
		except BlockingIOError:
			sent = 0
		except OSError:
			sent = 0
			self._drop(connection)

		if connection in self.clients:
			del output[:sent]

			if not output:
				self.selector.modify(connection, selectors.EVENT_READ)

	# Serve until no clients remain for the idle grace period.
	# ----------------------------------------------------------------------
	def _serve(self):
		if os.path.lexists(self.path):
			os.unlink(self.path)

		listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		listener.bind(self.path)
		os.chmod(self.path, 0o600)
		listener.listen(128)
		listener.setblocking(False)
		self.selector.register(listener, selectors.EVENT_READ)
		empty_since = None

		try:
			while True:
				if self.clients:
					empty_since = None
				elif empty_since is None:
					empty_since = monotonic()
				elif monotonic() - empty_since >= self.idle_timeout:
					break

				for key, events in self.selector.select(timeout=0.1):
					connection = key.fileobj

					if connection is listener:
						self._accept(listener)
					else:
						if events & selectors.EVENT_READ:
							self._read(connection)

						if connection in self.clients and events & selectors.EVENT_WRITE:
							self._write(connection)
		finally:
			for connection in tuple(self.clients):
				self._drop(connection)

			self.selector.unregister(listener)
			listener.close()
			self.selector.close()
			os.unlink(self.path)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Own the socket exactly once per host user; redundant starters exit.
	# ----------------------------------------------------------------------
	def run(self):
		lock_path = os.path.join(os.path.dirname(self.path), 'daemon.lock')

		with open(lock_path, 'a+b') as lock:
			try:
				fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
			except BlockingIOError:
				acquired = False
			else:
				acquired = True

			if acquired:
				self._serve()


# Run independently of O's Almasi filesystem-resolved module tree.
# ----------------------------------------------------------------------
if __name__ == '__main__':
	Transport(sys.argv[1]).run()
