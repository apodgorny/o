# ==============================================================================
# TEST TRANSPORT
# ==============================================================================
# Verify the host-local relay, scoped invalidations and O Sync integration.
# ==============================================================================

import json
import os
import queue
import select
import socket
import subprocess
import sys

from types import SimpleNamespace

import o


class TestTransport(o.Tester):

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Read one complete socket message, including a fragmented response.
	# ----------------------------------------------------------------------
	@classmethod
	def _frame(cls, connection):
		data = bytearray()

		while b'\n' not in data:
			part = connection.recv(65536)
			assert part
			data.extend(part)

		return json.loads(data.partition(b'\n')[0])

	# Open an independent socket peer and complete the ontology handshake.
	# ----------------------------------------------------------------------
	@classmethod
	def _peer(cls, path):
		connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		connection.settimeout(2.0)
		connection.connect(o.services.Transport.socket_path)
		connection.sendall(json.dumps(path).encode('utf-8') + b'\n')

		assert cls._frame(connection) is True
		return connection

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Enable IPC for these tests, then restore the default in-process mode.
	# ----------------------------------------------------------------------
	@classmethod
	def run(cls):
		o.start(multiprocess=True)

		try:
			return super().run()
		finally:
			o.start(multiprocess=False)
			assert o.services.Transport.send not in o.services.Sync._subscribers

	# A normal O.start() never creates a transport client.
	# ----------------------------------------------------------------------
	@classmethod
	def test_opt_in_default(cls):
		script = '''
import tempfile
import threading

from types import SimpleNamespace

import o

with tempfile.TemporaryDirectory(prefix='o_test_') as directory:
	type(o).__app__ = SimpleNamespace(__lib_path__=directory)
	o.start()

	assert not any(local_only for watched, local_only in o.services.Sync._subscribers.values())
	assert not any(thread.name == 'o-transport' for thread in threading.enumerate())
'''
		result = subprocess.run(
			[sys.executable, '-c', script],
			cwd            = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),
			capture_output = True,
			text           = True,
			timeout        = 15,
		)
		assert result.returncode == 0, result.stderr


	# O Sync publishes locally committed owner IDs to another process.
	# ----------------------------------------------------------------------
	@classmethod
	def test_local_delivery(cls):
		path = o.services.Transport.path
		peer = cls._peer(path)

		try:
			o.services.Sync.publish_change([780001, 780002], local=True)

			assert cls._frame(peer) == [780001, 780002]
		finally:
			peer.close()

	# Remote notifications invalidate cached O entities before callbacks.
	# ----------------------------------------------------------------------
	@classmethod
	def test_remote_cache_and_subscription(cls):
		path     = o.services.Transport.path
		peer     = cls._peer(path)
		received = queue.Queue()
		changed  = []
		owner_id = 780003
		entity   = SimpleNamespace(__invalidate__=lambda: changed.append(owner_id))
		cache    = o.services.Cache.entities
		original = cache.get(owner_id)
		callback = o.services.Sync.subscribe({owner_id}, received.put)

		try:
			cache[owner_id] = entity
			peer.sendall(json.dumps([owner_id]).encode('utf-8') + b'\n')

			assert received.get(timeout=2) == frozenset({owner_id})
			assert changed == [owner_id]

			# Incoming messages must never be sent back to the relay.
			# ----------------------------------------------------------
			peer.settimeout(0.1)

			try:
				echo = peer.recv(65536)
			except socket.timeout:
				echo = None

			assert echo is None
		finally:
			o.services.Sync.unsubscribe(callback)

			if original is None:
				cache.pop(owner_id, None)
			else:
				cache[owner_id] = original

			peer.close()

	# None invalidates every subscription and every local O cache.
	# ----------------------------------------------------------------------
	@classmethod
	def test_full_invalidation(cls):
		path     = o.services.Transport.path
		peer     = cls._peer(path)
		received = queue.Queue()
		changed  = []
		owner_id = 780006
		cache    = o.services.Cache.entities
		original = cache.get(owner_id)
		cache[owner_id] = SimpleNamespace(__invalidate__=lambda: changed.append(owner_id))
		callback = o.services.Sync.subscribe({owner_id}, received.put)

		try:
			peer.sendall(b'null\n')
			assert received.get(timeout=2) is None
			assert changed == [owner_id]
		finally:
			o.services.Sync.unsubscribe(callback)

			if original is None:
				cache.pop(owner_id, None)
			else:
				cache[owner_id] = original

			peer.close()

	# An unrelated ontology must never receive another ontology's changes.
	# ----------------------------------------------------------------------
	@classmethod
	def test_path_isolation(cls):
		path     = o.services.Transport.path
		other    = os.path.realpath(path + '-other')
		peer     = cls._peer(other)
		received = queue.Queue()
		callback = o.services.Sync.subscribe({780004}, received.put)

		try:
			peer.sendall(json.dumps([780004]).encode('utf-8') + b'\n')

			try:
				notification = received.get(timeout=0.15)
			except queue.Empty:
				notification = None

			assert notification is None
		finally:
			o.services.Sync.unsubscribe(callback)
			peer.close()


	# A second O process re-reads committed LMDB state after an IPC update.
	# ----------------------------------------------------------------------
	@classmethod
	def test_two_ontology_processes(cls):
		memory   = o.services.Memory
		owner_id = 780005
		key      = f'transport/integration/{os.getpid()}'
		script   = '''
import json
import queue
import sys

from types import SimpleNamespace

import o

type(o).__app__ = SimpleNamespace(__lib_path__=sys.argv[3])
o.start(multiprocess=True)

key      = sys.argv[1]
owner_id = int(sys.argv[2])
received = queue.Queue()

assert o.services.Memory.get(key) == 1
callback = o.services.Sync.subscribe({owner_id}, received.put)

print('READY', flush=True)
assert received.get(timeout=12) == frozenset({owner_id})
assert o.services.Memory.get(key) == 2
print('UPDATED', flush=True)
'''
		directory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
		memory.set(key, 1, owner_id)
		process = subprocess.Popen(
			[sys.executable, '-c', script, key, str(owner_id), o.__app__.__lib_path__],
			cwd    = directory,
			stdout = subprocess.PIPE,
			stderr = subprocess.PIPE,
			text   = True,
		)

		try:
			ready, _, _ = select.select([process.stdout], [], [], 15)
			assert ready and process.stdout.readline().strip() == 'READY'

			memory.set(key, 2, owner_id)
			stdout, stderr = process.communicate(timeout=15)

			assert process.returncode == 0, stderr
			assert 'UPDATED' in stdout
		finally:
			if process.poll() is None:
				process.kill()
				process.communicate()

			memory.unset(key, owner_id)



if __name__ == '__main__':
	TestTransport.run()
