# ==============================================================================
# TEST PERFORMANCE SYNC
# ==============================================================================
# Compare committed writes and notification latency with no delivery,
# in-process Sync, and host-local IPC.
# ==============================================================================

import argparse
import json
import os
import socket
import statistics
import subprocess
import sys
import tempfile
import time

from queue import Queue
from types import SimpleNamespace

import o


class TestPerformanceSync(o.Tester):

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Connect a second peer so IPC measures delivery through the relay.
	# ----------------------------------------------------------------------
	@classmethod
	def _peer(cls, transport, path):
		peer = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		peer.settimeout(5)
		peer.connect(transport.socket_path)
		peer.sendall(json.dumps(path).encode('utf-8') + b'\n')
		reader = peer.makefile('rb')
		assert json.loads(reader.readline()) is True

		return peer, reader

	# Measure each mode in an independent process and LMDB environment.
	# ----------------------------------------------------------------------
	@classmethod
	def _measure(cls, mode, size, latency_samples):
		with tempfile.TemporaryDirectory(prefix='o_perf_sync_') as directory:
			type(o).__app__ = SimpleNamespace(__lib_path__=directory)
			o.start(multiprocess=mode == 'ipc')

			memory = o.services.Memory
			sync   = o.services.Sync
			result = {}

			if mode == 'stub':
				memory.sync = SimpleNamespace(publish_change=lambda ids, local=True: None)

			# Wait for each notification, not merely its queue insertion.
			# --------------------------------------------------------------
			if mode != 'stub':
				latencies = []
				if mode == 'ipc':
					peer, reader = cls._peer(o.services.Transport, memory.path)
				else:
					arrivals = Queue()
					watched = set(range(1 << 60, (1 << 60) + latency_samples))
					sync.subscribe(watched, arrivals.put)

				try:
					for index in range(latency_samples):
						owner_id = (1 << 60) + index
						started  = time.perf_counter_ns()
						sync.publish_change([owner_id], local=True)

						if mode == 'ipc':
							while True:
								frame = reader.readline()
								assert frame, 'IPC peer disconnected before delivery'
								if json.loads(frame) == [owner_id]:
									break
						else:
							assert arrivals.get(timeout=5) == frozenset({owner_id})

						latencies.append((time.perf_counter_ns() - started) / 1000)
				finally:
					if mode == 'ipc':
						reader.close()
						peer.close()
					else:
						sync.unsubscribe(arrivals.put)

				result['delivery_latency'] = statistics.median(latencies)
			else:
				result['delivery_latency'] = None

			# A separate LMDB commit and owner notification per mutation.
			# --------------------------------------------------------------
			started = time.perf_counter_ns()

			for index in range(size):
				memory.set('sync/perf/single', index, 12345)

			result['write_single'] = (time.perf_counter_ns() - started) / (1000 * size)

			# One commit and one notification for the entire write batch.
			# --------------------------------------------------------------
			started = time.perf_counter_ns()

			with memory.write():
				for index in range(size):
					memory.set('sync/perf/batch', index, 12345)

			result['write_batch'] = (time.perf_counter_ns() - started) / (1000 * size)
			memory.env.close()

		return result

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Measure the current implementation without historical Sync internals.
	# ----------------------------------------------------------------------
	@classmethod
	def measure(cls, mode, size, latency_samples):
		return cls._measure(mode, size, latency_samples)


# Run paired modes in separate processes, alternating their order by round.
# ------------------------------------------------------------------------------
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--size', type=int, default=10000)
	parser.add_argument('--rounds', type=int, default=5)
	parser.add_argument('--latency-samples', type=int, default=100)
	parser.add_argument('--mode', choices=('all', 'stub', 'sync', 'ipc'), default='all')
	parser.add_argument('--_json', action='store_true', help=argparse.SUPPRESS)
	args = parser.parse_args()

	if args.size <= 0 or args.rounds <= 0 or args.latency_samples <= 0:
		parser.error('size, rounds and latency-samples must be positive')

	if args._json:
		print(json.dumps(TestPerformanceSync.measure(args.mode, args.size, args.latency_samples)))
	else:
		modes   = ('stub', 'sync', 'ipc') if args.mode == 'all' else (args.mode,)
		runner  = os.path.abspath(__file__)
		samples = {mode: {} for mode in modes}

		print(f'{args.rounds} rounds x {args.size} writes; {args.latency_samples} latency samples per round.', flush=True)

		for round_index in range(args.rounds):
			order = modes if round_index % 2 == 0 else tuple(reversed(modes))

			for mode in order:
				print(f'Round {round_index + 1}/{args.rounds}: {mode}', flush=True)
				completed = subprocess.run(
					[
						sys.executable, runner, '--_json',
						'--mode', mode,
						'--size', str(args.size),
						'--latency-samples', str(args.latency_samples),
					],
					capture_output = True,
					text           = True,
				)

				if completed.returncode:
					raise RuntimeError(f'{mode}: ' + completed.stdout + completed.stderr)

				for name, value in json.loads(completed.stdout.strip().splitlines()[-1]).items():
					if value is not None:
						samples[mode].setdefault(name, []).append(value)

		print()
		print('Microseconds per operation: median [min..max]. Lower is faster.')
		print('Mode       Separate commit       Batched write        Delivery latency')
		print('--------------------------------------------------------------------------')

		for mode in modes:
				values = samples[mode]
				columns = []

				for name in ('write_single', 'write_batch', 'delivery_latency'):
					if name in values:
						times = values[name]
						columns.append(f'{statistics.median(times):7.3f} [{min(times):7.3f}..{max(times):7.3f}]')
					else:
						columns.append('n/a')

				print(f'{mode:8}   {columns[0]:22} {columns[1]:22} {columns[2]}')

		print()
		print('stub = LMDB + owner tracking, no Sync delivery')
		print('sync = in-process Sync; ipc = Sync plus relay and a second socket peer')
		print('Delivery latency: local callback (sync) or peer frame receipt (ipc).')
