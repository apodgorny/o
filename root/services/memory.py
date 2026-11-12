# ==============================================================================
# MEMORY SERVICE
# ==============================================================================
# Notify IPL immediately for writes and once after committed transactions.
# ==============================================================================

import os
import lmdb
import msgpack

import o

UNDEFINED = o.Undefined


class MemoryBatch:

	# Create batch
	# ----------------------------------------------------------------------
	def __init__(self, memory, write=True):
		self.memory      = memory
		self.write       = write
		self.ctx         = None
		self.tx          = None
		self.depth       = 0
		self.ipl         = None
		self.notified    = False

	# If we are already in a transaction, just return ourselves
	# ----------------------------------------------------------------------
	def __enter__(self):
		if self.tx is None:
			self.ctx         = self.memory.env.begin(write=self.write)
			self.tx          = self.ctx.__enter__()
			self.ipl         = self.memory.ipl if self.write else None
			self.notified    = False

		self.depth += 1
		return self

	# Confirm the transaction after its successful commit.
	# ----------------------------------------------------------------------
	def __exit__(self, exc_type, exc, tb):
		self.depth -= 1

		if self.ctx is not None and self.depth == 0:
			ipl = self.ipl if exc_type is None and self.notified else None

			try:
				self.ctx.__exit__(exc_type, exc, tb)
			finally:
				if self.write:
					self.memory._write = None
				else:
					self.memory._read = None

				self.ipl = None
				self.notified = False
				self.tx  = None
				self.ctx = None

			if ipl is not None:
				ipl.invalidate()

		return False

	# Delegation
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		return getattr(self.memory, name)

	# Store value and notify IPL after LMDB accepts the write.
	# owner_id is one ID or a tuple of IDs for multi-owner changes.
	# ----------------------------------------------------------------------
	def set(self, key, value, owner_id):
		self.tx.put(self.memory._key(key), self.memory.to_bytes(value))

		if self.ipl is not None:
			self.notified = True

			if type(owner_id) is int:
				self.ipl.pre_invalidate(owner_id)
			else:
				for id in owner_id:
					self.ipl.pre_invalidate(id)

	# Notify IPL only when a key was actually removed.
	# ----------------------------------------------------------------------
	def unset(self, key, owner_id):
		deleted = self.tx.delete(self.memory._key(key))

		if deleted and self.ipl is not None:
			self.notified = True

			if type(owner_id) is int:
				self.ipl.pre_invalidate(owner_id)
			else:
				for id in owner_id:
					self.ipl.pre_invalidate(id)

	# Delete a prefix and notify its known owners once before removal.
	# ----------------------------------------------------------------------
	def unset_all(self, key_prefix, owner_id):
		prefix = self.memory._key(key_prefix)
		cursor = self.tx.cursor()
		ok     = cursor.set_range(prefix)
		ipl    = self.ipl

		if ok and cursor.key().startswith(prefix) and ipl is not None:
			self.notified = True

			if type(owner_id) is int:
				ipl.pre_invalidate(owner_id)
			else:
				for id in owner_id:
					ipl.pre_invalidate(id)

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

	# Iterate stored keys by prefix.
	# ----------------------------------------------------------------------
	def _pairs(self, prefix=''):
		key      = self.memory._key(prefix)
		cursor   = self.tx.cursor()
		has_item = cursor.set_range(key) if key else cursor.first()

		while has_item:
			key_bytes = cursor.key()

			if not key_bytes.startswith(key):
				break

			yield key_bytes.decode('utf-8'), cursor.value()
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
		self.prefix   = prefix
		self.cache    = {}
		self.memory   = o.services.Memory
		self.owner_id = 0

		if prefix.startswith('o.T.') and prefix.endswith('.'):
			proto = prefix[:-1]

			if proto.endswith('._'):
				proto = proto[:-2]

			self.owner_id = o.String.hash(proto, 15)

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
	def set(self, key, value=None, owner_id=None):
		self.cache[key] = value
		self.memory.set(self._key(key), value, self.owner_id if owner_id is None else owner_id)

	# Remove value
	# ----------------------------------------------------------------------
	def unset(self, key, owner_id=None):
		self.cache[key] = UNDEFINED
		self.memory.unset(self._key(key), self.owner_id if owner_id is None else owner_id)

	# Clear zone
	# ----------------------------------------------------------------------
	def clear(self, owner_id=None):
		self.cache.clear()
		self.memory.unset_all(self.prefix, self.owner_id if owner_id is None else owner_id)

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
	ipl = None

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

	# Open LMDB with the durability policy supplied by o.start().
	# sync=False skips the commit-time disk flush; crashes may lose data.
	# Use sync=True if committed data must survive an OS crash or power loss.
	# ----------------------------------------------------------------------
	def initialize(self, sync: bool = False):
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
			sync     = sync,
		)

		self._read   = None
		self._write  = None
		self.root_id = o.String.hash('o.T', 15)

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
	def set(self, key, value, owner_id):
		with self.write() as batch:
			batch.set(key, value, owner_id)

	# Remove key
	# ----------------------------------------------------------------------
	def unset(self, key, owner_id):
		with self.write() as batch:
			batch.unset(key, owner_id)

	# Unset all keys by prefix
	# ----------------------------------------------------------------------
	def unset_all(self, key_prefix, owner_id):
		with self.write() as batch:
			batch.unset_all(key_prefix, owner_id)

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

