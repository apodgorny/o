# ==============================================================================
# TRANSPORT DAEMON
# ==============================================================================
# Relay O invalidations between local processes without opening their LMDB.
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

	# Keep one set of socket connections and their buffered frames.
	# ----------------------------------------------------------------------
	def __init__(self, socket_path, idle_timeout=3.0):
		self.socket_path  = socket_path
		self.idle_timeout = idle_timeout
		self.selector     = selectors.DefaultSelector()
		self.clients      = {}
		self.listener     = None

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Bind the socket only after owning the daemon's process-wide lock.
	# ----------------------------------------------------------------------
	def _listen(self):
		if os.path.lexists(self.socket_path):
			os.unlink(self.socket_path)

		self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		self.listener.bind(self.socket_path)
		os.chmod(self.socket_path, 0o600)
		self.listener.listen(128)
		self.listener.setblocking(False)
		self.selector.register(self.listener, selectors.EVENT_READ)

	# Accept peers without allocating a thread for each connection.
	# ----------------------------------------------------------------------
	def _accept(self):
		connection, _ = self.listener.accept()
		connection.setblocking(False)
		self.clients[connection] = {
			'path'   : None,
			'input'  : bytearray(),
			'output' : bytearray(),
		}
		self.selector.register(connection, selectors.EVENT_READ)

	# Release the socket and its buffers together when a peer disappears.
	# ----------------------------------------------------------------------
	def _disconnect(self, connection):
		if connection in self.clients:
			self.clients.pop(connection)
			self.selector.unregister(connection)
			connection.close()

	# Buffer outgoing frames without allowing a slow peer unbounded memory.
	# ----------------------------------------------------------------------
	def _queue(self, connection, message):
		if connection in self.clients:
			output = self.clients[connection]['output']
			frame  = json.dumps(message, separators=(',', ':')).encode('utf-8') + b'\n'

			if len(output) + len(frame) > 1048576:
				self._disconnect(connection)
			else:
				output.extend(frame)
				self.selector.modify(connection, selectors.EVENT_READ | selectors.EVENT_WRITE)

	# Forward only well-formed invalidations to peers in the same ontology.
	# ----------------------------------------------------------------------
	def _message(self, connection, message):
		if not isinstance(message, list) or len(message) < 2:
			self._disconnect(connection)
		else:
			state = self.clients[connection]

			if message[0] == 'join' and len(message) == 2:
				path = message[1]

				if (
					state['path'] is not None
					or not isinstance(path, str)
					or not os.path.isabs(path)
					or os.path.realpath(path) != path
				):
					self._disconnect(connection)
				else:
					state['path'] = path
					self._queue(connection, ['ready', path])
			elif message[0] == 'change' and len(message) == 3:
				path = message[1]
				ids  = message[2]

				if (
					state['path'] is None
					or path != state['path']
					or not isinstance(ids, list)
					or not ids
					or any(type(id) is not int or id < 0 for id in ids)
				):
					self._disconnect(connection)
				else:
					ids = [0] if 0 in ids else sorted(set(ids))

					for peer, subscriber in tuple(self.clients.items()):
						if peer is not connection and subscriber['path'] == path:
							self._queue(peer, ['invalidate', path, ids])
			else:
				self._disconnect(connection)

	# Read complete JSON-line frames without treating partial reads as messages.
	# ----------------------------------------------------------------------
	def _read(self, connection):
		try:
			data = connection.recv(65536)
		except OSError:
			data = b''

		if not data:
			self._disconnect(connection)
		else:
			buffer = self.clients[connection]['input']
			buffer.extend(data)

			while connection in self.clients and b'\n' in buffer:
				frame, _, remainder = buffer.partition(b'\n')
				buffer[:] = remainder

				try:
					message = json.loads(frame)
				except (UnicodeDecodeError, ValueError):
					self._disconnect(connection)
				else:
					self._message(connection, message)

			if connection in self.clients and len(buffer) > 1048576:
				self._disconnect(connection)

	# Send the available bytes and resume a partial write on the next event.
	# ----------------------------------------------------------------------
	def _write(self, connection):
		output = self.clients[connection]['output']

		try:
			sent = connection.send(output)
		except BlockingIOError:
			sent = 0
		except OSError:
			sent = 0
			self._disconnect(connection)

		if connection in self.clients:
			del output[:sent]

			if not output:
				self.selector.modify(connection, selectors.EVENT_READ)

	# Leave no pathname behind when the last peer disconnects.
	# ----------------------------------------------------------------------
	def _close(self):
		for connection in tuple(self.clients):
			self._disconnect(connection)

		if self.listener is not None:
			self.selector.unregister(self.listener)
			self.listener.close()

		self.selector.close()

		if os.path.lexists(self.socket_path):
			os.unlink(self.socket_path)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Serve local peers until the socket has been unused for a short period.
	# ----------------------------------------------------------------------
	def run(self):
		lock_path = os.path.join(os.path.dirname(self.socket_path), 'daemon.lock')

		with open(lock_path, 'a+b') as lock:
			try:
				fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
			except BlockingIOError:
				return

			self._listen()
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

						if connection is self.listener:
							self._accept()
						else:
							if events & selectors.EVENT_READ:
								self._read(connection)

							if connection in self.clients and events & selectors.EVENT_WRITE:
								self._write(connection)
			finally:
				self._close()


# Run this infrastructure module without loading any O ontology.
# ----------------------------------------------------------------------
if __name__ == '__main__':
	Transport(sys.argv[1]).run()
