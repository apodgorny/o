# ==============================================================================
# O VS SQLITE PERFORMANCE TEST
# ==============================================================================
# Compare equivalent user-visible operations with per-operation commits.
# LMDB sync=False and SQLite WAL synchronous=OFF; neither is crash-durable.
# Fixture construction is excluded from timed regions.
# ==============================================================================

import argparse
import os
import platform
import sqlite3
import sys
import tempfile
import time
from types import SimpleNamespace

import o


KEYS = ('a', 'b', 'c', 'd', 'e')


# Time one complete workload, excluding its fixture.
# ------------------------------------------------------------------------------
def measure(run):
	started = time.perf_counter_ns()
	run()
	return (time.perf_counter_ns() - started) / 1e9


# Create SQLite tables representing the same five-element containers.
# ------------------------------------------------------------------------------
def sqlite_fixtures(db):
	db.execute('CREATE TABLE list_values (idx INTEGER PRIMARY KEY, value INTEGER NOT NULL)')
	db.execute('CREATE TABLE dict_values (key TEXT PRIMARY KEY, value INTEGER NOT NULL)')
	db.executemany(
		'INSERT INTO list_values (idx, value) VALUES (?, ?)',
		((i, i + 1) for i in range(5)),
	)
	db.executemany(
		'INSERT INTO dict_values (key, value) VALUES (?, ?)',
		zip(KEYS, range(1, 6)),
	)


# Run a single workload against o. All fixtures precede the timer.
# ------------------------------------------------------------------------------
def run_o(name, n, root):
	if name == 'list_getitem':
		x = o.List([1, 2, 3, 4, 5])

		def run():
			for i in range(n):
				x[i % 5]

	elif name == 'list_setitem':
		x = o.List([1, 2, 3, 4, 5])

		def run():
			for i in range(n):
				x[i % 5] = i

	elif name == 'dict_getitem':
		x = o.Dict(dict(zip(KEYS, range(1, 6))))

		def run():
			for i in range(n):
				x[KEYS[i % 5]]

	elif name == 'dict_setitem':
		x = o.Dict(dict(zip(KEYS, range(1, 6))))

		def run():
			for i in range(n):
				x[KEYS[i % 5]] = i

	elif name == 'object_attr_get_set':
		cls = root.extend('ASqlPerfAttr', x=int, y=int)
		x   = cls(x=1, y=2)

		def run():
			for i in range(n):
				x.x
				x.y
				x.x = i
				x.y = i + 1

	elif name == 'object_create':
		cls = root.extend('ASqlPerfCreate', x=int, y=int)

		def run():
			for i in range(n):
				cls(x=i, y=i + 1)

	elif name == 'define':
		def run():
			for i in range(n):
				type_name = f'ASqlPerfDefine{i}'
				attempt   = 0

				while hasattr(root, type_name):
					attempt   += 1
					type_name = f'ASqlPerfDefine{i}_{attempt}'

				root.extend(type_name, x=int, y=int)

	else:
		raise ValueError(name)

	return measure(run)


# Run the corresponding SQLite workload in autocommit mode.
# Every UPDATE / INSERT / CREATE TABLE is an independent transaction.
# ------------------------------------------------------------------------------
def run_sqlite(name, n, db):
	if name in ('list_getitem', 'list_setitem'):
		db.execute('DROP TABLE IF EXISTS list_values')
		db.execute('CREATE TABLE list_values (idx INTEGER PRIMARY KEY, value INTEGER NOT NULL)')
		db.executemany(
			'INSERT INTO list_values (idx, value) VALUES (?, ?)',
			((i, i + 1) for i in range(5)),
		)

	elif name in ('dict_getitem', 'dict_setitem'):
		db.execute('DROP TABLE IF EXISTS dict_values')
		db.execute('CREATE TABLE dict_values (key TEXT PRIMARY KEY, value INTEGER NOT NULL)')
		db.executemany(
			'INSERT INTO dict_values (key, value) VALUES (?, ?)',
			zip(KEYS, range(1, 6)),
		)

	elif name == 'object_attr_get_set':
		db.execute('CREATE TABLE attr_object (id INTEGER PRIMARY KEY, x INTEGER, y INTEGER)')
		db.execute('INSERT INTO attr_object (id, x, y) VALUES (1, 1, 2)')

	elif name == 'object_create':
		db.execute('CREATE TABLE created_objects (id INTEGER PRIMARY KEY, x INTEGER, y INTEGER)')

	if name == 'list_getitem':
		def run():
			for i in range(n):
				db.execute('SELECT value FROM list_values WHERE idx = ?', (i % 5,)).fetchone()

	elif name == 'list_setitem':
		def run():
			for i in range(n):
				db.execute('UPDATE list_values SET value = ? WHERE idx = ?', (i, i % 5))

	elif name == 'dict_getitem':
		def run():
			for i in range(n):
				db.execute('SELECT value FROM dict_values WHERE key = ?', (KEYS[i % 5],)).fetchone()

	elif name == 'dict_setitem':
		def run():
			for i in range(n):
				db.execute('UPDATE dict_values SET value = ? WHERE key = ?', (i, KEYS[i % 5]))

	elif name == 'object_attr_get_set':
		def run():
			for i in range(n):
				db.execute('SELECT x FROM attr_object WHERE id = 1').fetchone()
				db.execute('SELECT y FROM attr_object WHERE id = 1').fetchone()
				db.execute('UPDATE attr_object SET x = ? WHERE id = 1', (i,))
				db.execute('UPDATE attr_object SET y = ? WHERE id = 1', (i + 1,))

	elif name == 'object_create':
		def run():
			for i in range(n):
				db.execute('INSERT INTO created_objects (x, y) VALUES (?, ?)', (i, i + 1))

	elif name == 'define':
		def run():
			for i in range(n):
				db.execute(f'CREATE TABLE ASqlPerfDefine{i} (x INTEGER, y INTEGER)')

	else:
		raise ValueError(name)

	return measure(run)


# Run each pair on isolated stores with equivalent durability policies.
# ------------------------------------------------------------------------------
def compare(size, include_create):
	cases = [
		'list_getitem',
		'list_setitem',
		'dict_getitem',
		'dict_setitem',
		'object_attr_get_set',
	]
	if include_create:
		cases.append('object_create')
	cases.append('define')

	with tempfile.TemporaryDirectory(prefix='o_sqlite_compare_') as directory:
		type(o).__app__ = SimpleNamespace(__lib_path__=directory)
		o.start(sync=False)
		env = o.services.Memory.env

		try:
			if env.flags().get('sync') is False:
				db = sqlite3.connect(
					os.path.join(directory, 'sqlite.db'),
					isolation_level=None,
				)
			else:
				raise RuntimeError('LMDB sync=False was not applied')

			try:
				mode = db.execute('PRAGMA journal_mode=WAL').fetchone()[0]
				db.execute('PRAGMA synchronous=OFF')
				sync = db.execute('PRAGMA synchronous').fetchone()[0]
				if mode.lower() == 'wal' and sync == 0:
					root = o.T.extend('ASqlPerfRun')
				else:
					raise RuntimeError('SQLite WAL synchronous=OFF was not applied')

				print(f'Python {sys.version.split()[0]}, SQLite {sqlite3.sqlite_version}, {platform.platform()}')
				print(f'n={size}, LMDB sync=False, SQLite WAL synchronous=OFF, autocommit')
				print('Fixture construction excluded. One commit per write statement; no outer transaction.')
				print('Ratio = SQLite time / o time (larger means o is faster).')
				print()
				print(f'''{'Operation':22} {'o (us/iter)':>14} {'SQLite (us/iter)':>17} {'SQLite / o':>12}''')
				print('-' * 70)

				for name in cases:
					o_seconds      = run_o(name, size, root)
					sqlite_seconds = run_sqlite(name, size, db)
					o_us           = o_seconds * 1e6 / size
					sqlite_us      = sqlite_seconds * 1e6 / size
					ratio          = sqlite_us / o_us
					print(f'{name:22} {o_us:14.3f} {sqlite_us:17.3f} {ratio:11.2f}x', flush=True)

				print()
				print('Notes: SQLite uses native indexed rows; o persists typed entities and relationships.')
				print('Define compares o class extension with SQLite CREATE TABLE, not identical metadata.')
				print('No guarantees of persistence across OS crash/power loss with these settings.')

			finally:
				db.close()

		finally:
			env.close()


# Run on fresh databases.
# ------------------------------------------------------------------------------
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--size', type=int, default=5000)
	parser.add_argument('--include-create', action='store_true')
	args = parser.parse_args()

	if args.size <= 0:
		parser.error('--size must be positive')

	compare(args.size, args.include_create)
