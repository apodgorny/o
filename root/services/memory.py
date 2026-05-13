import os
import lmdb
import msgpack

import o

UNDEFINED = o.Undefined


class MemoryBatch:

	# Create batch
	# ----------------------------------------------------------------------
	def __init__(self, memory, write=True):
		self.memory = memory
		self.write  = write
		self.ctx    = None
		self.tx     = None
		self.depth  = 0

	# If we are already in a transaction, just return ourselves
	# ----------------------------------------------------------------------
	def __enter__(self):
		self.depth += 1
		if self.tx is not None:
			return self
		
		self.ctx = self.memory.env.begin(write=self.write)
		self.tx  = self.ctx.__enter__()
		return self

	# Only the opener of the context manager should close it.
	# ----------------------------------------------------------------------
	def __exit__(self, exc_type, exc, tb):
		self.depth -= 1
		if self.ctx and self.depth == 0:
			try:
				self.ctx.__exit__(exc_type, exc, tb)
			finally:
				if self.write : self.memory._write = None
				else          : self.memory._read  = None

				self.tx  = None
				self.ctx = None
		return False
	
	# Delegation
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		return getattr(self.memory, name)

	# Store value
	# ----------------------------------------------------------------------
	def set(self, key, value):
		self.tx.put(self.memory._key(key), self.memory.to_bytes(value))

	# Remove key
	# ----------------------------------------------------------------------
	def unset(self, key):
		self.tx.delete(self.memory._key(key))

	# Unset all keys by prefix
	# ----------------------------------------------------------------------
	def unset_all(self, key_prefix):
		prefix = self.memory._key(key_prefix)
		cursor = self.tx.cursor()
		ok     = cursor.set_range(prefix)

		while ok:
			key = cursor.key()

			if not key.startswith(prefix):
				break

			cursor.delete()
			ok = cursor.set_range(prefix)

	# Resolve stored value
	# ----------------------------------------------------------------------
	def get(self, key, default=UNDEFINED):
		value = default
		data  = self.tx.get(self.memory._key(key))

		if data is not None:
			value = self.memory.from_bytes(data)

		return value

	# Check whether key exists
	# ----------------------------------------------------------------------
	def has(self, key):
		key_bytes = self.memory._key(key)
		result    = False

		with self.tx.cursor() as cur:
			result = cur.set_key(key_bytes)

		return result

	# Iterate stored pairs by prefix
	# ----------------------------------------------------------------------
	def _pairs(self, prefix=''):
		key      = self.memory._key(prefix)
		cursor   = self.tx.cursor()
		has_item = cursor.set_range(key) if key else cursor.first()

		while has_item:
			key_bytes   = cursor.key()
			value_bytes = cursor.value()

			if not key_bytes.startswith(key):
				break

			yield key_bytes.decode('utf-8'), value_bytes
			has_item = cursor.next()

	# Iterate stored items by prefix
	# ----------------------------------------------------------------------
	def items(self, prefix=''):
		for key, value_bytes in self._pairs(prefix):
			yield key, self.memory.from_bytes(value_bytes)

	# Iterate stored keys by prefix
	# ----------------------------------------------------------------------
	def keys(self, prefix=''):
		for key, value in self._pairs(prefix):
			yield key


class Zone:

	# Constructor
	# ----------------------------------------------------------------------
	def __init__(self, prefix):
		self.prefix = prefix
		self.cache  = {}
		self.memory = o.services.Memory

	# Get memory key
	# ----------------------------------------------------------------------
	def _key(self, key):
		return f'{self.prefix}{key}'

	# Get value
	# ----------------------------------------------------------------------
	def get(self, key, default=UNDEFINED):
		if key not in self.cache:
			self.cache[key] = self.memory.get(self._key(key), UNDEFINED)

		value = self.cache[key]

		if value is UNDEFINED:
			value = default

		return value

	# Check value
	# ----------------------------------------------------------------------
	def has(self, key):
		if key not in self.cache:
			self.cache[key] = self.memory.get(self._key(key), UNDEFINED)

		return self.cache[key] is not UNDEFINED

	# Set value
	# ----------------------------------------------------------------------
	def set(self, key, value=None):
		self.cache[key] = value
		self.memory.set(self._key(key), value)

	# Remove value
	# ----------------------------------------------------------------------
	def unset(self, key):
		self.cache[key] = UNDEFINED
		self.memory.unset(self._key(key))

	# Clear zone
	# ----------------------------------------------------------------------
	def clear(self):
		self.cache.clear()
		self.memory.unset_all(self.prefix)

	# Iterate zone items
	# ----------------------------------------------------------------------
	def items(self, prefix=''):
		offset = len(self.prefix)

		for key, value in self.memory.items(self._key(prefix)):
			key = key[offset:]
			self.cache[key] = value

			yield key, value

	# Iterate zone keys
	# ----------------------------------------------------------------------
	def keys(self, prefix=''):
		offset = len(self.prefix)

		for key in self.memory.keys(self._key(prefix)):
			yield key[offset:]


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
	# PRIVATE METHODS
	# ======================================================================

	# Encode key
	# ----------------------------------------------------------------------
	def _key(self, key):
		return str(key).encode('utf-8')

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

		self._read  = None
		self._write = None

	# Open read batch
	# ----------------------------------------------------------------------
	def read(self):
		if self._read is None:
			self._read = MemoryBatch(self, False)
		return self._read
	
	# Open write batch
	# ----------------------------------------------------------------------
	def write(self):
		if self._write is None:
			self._write = MemoryBatch(self, True)
		return self._write

	# Get memory zone
	# ----------------------------------------------------------------------
	def zone(self, prefix):
		return Zone(prefix)

	# Store value
	# ----------------------------------------------------------------------
	def set(self, key, value=None):
		with self.write() as batch:
			batch.set(key, value)

	# Remove key
	# ----------------------------------------------------------------------
	def unset(self, key):
		with self.write() as batch:
			batch.unset(key)

	# Unset all keys by prefix
	# ----------------------------------------------------------------------
	def unset_all(self, key_prefix):
		with self.write() as batch:
			batch.unset_all(key_prefix)

	# Resolve stored value
	# ----------------------------------------------------------------------
	def get(self, key, default=UNDEFINED):
		with self.read() as batch:
			value = batch.get(key, default)
		
		return value

	# Check whether key exists
	# ----------------------------------------------------------------------
	def has(self, key):
		with self.read() as batch:
			result = batch.has(key)

		return result

	# Iterate stored items by prefix
	# ----------------------------------------------------------------------
	def items(self, prefix=''):
		with self.read() as batch:
			yield from batch.items(prefix)

	# Iterate stored keys by prefix
	# ----------------------------------------------------------------------
	def keys(self, prefix=''):
		with self.read() as batch:
			yield from batch.keys(prefix)
