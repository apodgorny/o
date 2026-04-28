import os

import lmdb
import msgpack

import o

UNDEFINED = o.Undefined


class MemoryWrite:

	# Create write scope
	# ----------------------------------------------------------------------
	def __init__(self, memory):
		self.memory = memory

	# Enter write scope
	# ----------------------------------------------------------------------
	def __enter__(self):
		memory = self.memory
		depth  = memory.__dict__.get('_write_depth', 0)

		if depth == 0:
			memory._write_scope = memory.env.begin(write=True)
			memory._write_txn   = memory._write_scope.__enter__()

		memory._write_depth = depth + 1

		return memory

	# Exit write scope
	# ----------------------------------------------------------------------
	def __exit__(self, exc_type, exc, tb):
		memory = self.memory
		depth  = memory.__dict__.get('_write_depth', 1) - 1
		result = False

		memory._write_depth = depth

		if depth == 0:
			memory._write_scope.__exit__(exc_type, exc, tb)

			if '_write_txn' in memory.__dict__:
				del memory.__dict__['_write_txn']

			if '_write_scope' in memory.__dict__:
				del memory.__dict__['_write_scope']

		return result


class MemoryRead:

	# Create read scope
	# ----------------------------------------------------------------------
	def __init__(self, memory):
		self.memory = memory

	# Enter read scope
	# ----------------------------------------------------------------------
	def __enter__(self):
		memory = self.memory
		depth  = memory.__dict__.get('_read_depth', 0)

		if depth == 0 and '_write_txn' not in memory.__dict__:
			memory._read_scope = memory.env.begin()
			memory._read_txn   = memory._read_scope.__enter__()

		memory._read_depth = depth + 1

		return memory

	# Exit read scope
	# ----------------------------------------------------------------------
	def __exit__(self, exc_type, exc, tb):
		memory = self.memory
		depth  = memory.__dict__.get('_read_depth', 1) - 1
		result = False

		memory._read_depth = depth

		if depth == 0 and '_read_scope' in memory.__dict__:
			memory._read_scope.__exit__(exc_type, exc, tb)

			if '_read_txn' in memory.__dict__:
				del memory.__dict__['_read_txn']

			if '_read_scope' in memory.__dict__:
				del memory.__dict__['_read_scope']

		return result


class Memory(o.Service):

	# ======================================================================
	# CLASS PUBLIC METHODS
	# ======================================================================

	# Encode value into LMDB bytes
	# ----------------------------------------------------------------------
	@classmethod
	def to_bytes(cls, value):
		return msgpack.packb(value, use_bin_type=True)

	# Decode LMDB bytes into value
	# ----------------------------------------------------------------------
	@classmethod
	def from_bytes(cls, data):
		return msgpack.unpackb(data, raw=False, strict_map_key=False)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Initialize memory store
	# ----------------------------------------------------------------------
	def initialize(self):
		path = os.path.realpath(os.path.join(o.__path__, o.DATA_DIR))

		if 'env' in self.__dict__:
			self.env.close()

		os.makedirs(os.path.dirname(path), exist_ok=True)

		self.path = path
		self.size = o.MEMORY_SIZE
		self.env  = lmdb.open(
			path,
			create   = True,
			lock     = True,
			map_size = self.size,
			max_dbs  = 1,
			subdir   = True,
		)

		if '_write_depth' in self.__dict__:
			del self.__dict__['_write_depth']

		if '_write_txn' in self.__dict__:
			del self.__dict__['_write_txn']

		if '_write_scope' in self.__dict__:
			del self.__dict__['_write_scope']

		if '_read_depth' in self.__dict__:
			del self.__dict__['_read_depth']

		if '_read_txn' in self.__dict__:
			del self.__dict__['_read_txn']

		if '_read_scope' in self.__dict__:
			del self.__dict__['_read_scope']

	# Open write scope
	# ----------------------------------------------------------------------
	def write(self):
		scope = MemoryWrite(self)
		return scope

	# Open read scope
	# ----------------------------------------------------------------------
	def read(self):
		scope = MemoryRead(self)
		return scope

	# Store value
	# ----------------------------------------------------------------------
	def set(self, key, value):
		key_bytes = str(key).encode('utf-8')
		data      = self.to_bytes(value)
		txn       = self.__dict__.get('_write_txn', UNDEFINED)

		if txn is UNDEFINED:
			with self.env.begin(write=True) as txn:
				txn.put(key_bytes, data)
		else:
			txn.put(key_bytes, data)

	# Remove key
	# ----------------------------------------------------------------------
	def unset(self, key):
		key_bytes = str(key).encode('utf-8')
		txn       = self.__dict__.get('_write_txn', UNDEFINED)

		if txn is UNDEFINED:
			with self.env.begin(write=True) as txn:
				txn.delete(key_bytes)
		else:
			txn.delete(key_bytes)

	# Resolve stored value
	# ----------------------------------------------------------------------
	def get(self, key, default=UNDEFINED):
		key_bytes = str(key).encode('utf-8')
		txn       = self.__dict__.get('_write_txn', UNDEFINED)
		value     = default
		data      = None

		if txn is UNDEFINED:
			txn = self.__dict__.get('_read_txn', UNDEFINED)

		if txn is UNDEFINED:
			with self.env.begin() as txn:
				data = txn.get(key_bytes)
		else:
			data = txn.get(key_bytes)

		if data is not None:
			value = self.from_bytes(data)

		return value

	# Check whether key exists
	# ----------------------------------------------------------------------
	def has(self, key):
		key_bytes = str(key).encode('utf-8')
		txn       = self.__dict__.get('_write_txn', UNDEFINED)
		result    = False

		if txn is UNDEFINED:
			txn = self.__dict__.get('_read_txn', UNDEFINED)

		if txn is UNDEFINED:
			with self.env.begin() as txn:
				result = txn.get(key_bytes) is not None
		else:
			result = txn.get(key_bytes) is not None

		return result

	# Iterate stored items by prefix
	# ----------------------------------------------------------------------
	def items(self, prefix=''):
		prefix_bytes = str(prefix).encode('utf-8')
		txn          = self.__dict__.get('_write_txn', UNDEFINED)

		if txn is UNDEFINED:
			txn = self.__dict__.get('_read_txn', UNDEFINED)

		if txn is UNDEFINED:
			with self.env.begin() as txn:
				cursor   = txn.cursor()
				has_item = cursor.set_range(prefix_bytes) if prefix_bytes else cursor.first()

				while has_item:
					key_bytes   = cursor.key()
					value_bytes = cursor.value()

					if prefix_bytes and not key_bytes.startswith(prefix_bytes):
						break

					yield key_bytes.decode('utf-8'), self.from_bytes(value_bytes)
					has_item = cursor.next()
		else:
			cursor   = txn.cursor()
			has_item = cursor.set_range(prefix_bytes) if prefix_bytes else cursor.first()

			while has_item:
				key_bytes   = cursor.key()
				value_bytes = cursor.value()

				if prefix_bytes and not key_bytes.startswith(prefix_bytes):
					break

				yield key_bytes.decode('utf-8'), self.from_bytes(value_bytes)
				has_item = cursor.next()
