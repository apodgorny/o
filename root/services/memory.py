# ==============================================================================
# MEMORY SERVICE
# ==============================================================================
# Record changed owner IDs during writes; confirm after LMDB commits.
# ==============================================================================

import os
import lmdb
import msgpack

import o

UNDEFINED = o.Undefined


class MemoryBatch:



	# Create batch with lazily tracked rollback caches.
	# ----------------------------------------------------------------------
	def __init__(self, memory, write=True):
		self.memory   = memory
		self.write    = write
		self.ctx      = None
		self.tx       = None
		self.depth    = 0
		self.sync     = None
		self.ids      = None
		self.failed   = False
		self.zones    = None

	# Join an existing transaction or open a new outer transaction.
	# ----------------------------------------------------------------------
	def __enter__(self):
		if self.tx is None:
			self.ctx      = self.memory.env.begin(write=self.write)
			self.tx       = self.ctx.__enter__()
			self.sync     = self.memory.sync if self.write else None
			self.ids      = [] if self.sync is not None else None
			self.failed   = False
			self.zones    = None

		self.depth += 1
		return self

	# Commit once, or roll back every change after any nested failure.
	# Clear cached zone values whenever LMDB does not commit.
	# ----------------------------------------------------------------------
	def __exit__(self, exc_type, exc, tb):
		self.depth -= 1

		if exc_type is not None:
			self.failed = True

		if self.ctx is not None and self.depth == 0:
			aborted   = self.failed
			committed = False
			sync      = self.sync
			ids       = self.ids

			try:
				if aborted:
					self.ctx.__exit__(RuntimeError, RuntimeError('Transaction aborted'), None)
				else:
					self.ctx.__exit__(exc_type, exc, tb)
					committed = exc_type is None
			finally:
				if not committed and self.zones is not None:
					for zone in self.zones:
						zone.cache.clear()

				if self.write:
					self.memory._write = None
				else:
					self.memory._read = None

				self.sync     = None
				self.ids      = None
				self.failed   = False
				self.zones    = None
				self.tx       = None
				self.ctx      = None


			if committed and (ids is None or ids):
				try:
					sync.publish_change(ids, local=True)
				except Exception as error:
					raise RuntimeError('LMDB committed; Sync publication failed') from error

			if aborted and exc_type is None:
				raise RuntimeError('Transaction aborted after an earlier failure')

		return False

	# Track a zone only when another scope owns the open write transaction.
	# ----------------------------------------------------------------------
	def _track_zone(self, zone):
		if self.zones is None:
			self.zones = set()

		self.zones.add(zone)

	# Delegation
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		return getattr(self.memory, name)


	# Send every affected ID; each write operation owns its notification.
	# ----------------------------------------------------------------------
	def _notify(self, owner_id):
		if owner_id is None:
			self.ids = None
		elif type(owner_id) is int:
			if self.ids is not None:
				self.ids.append(owner_id)
		else:
			ids = tuple(owner_id)

			if not ids:
				raise ValueError('owner_id iterable must contain at least one ID')

			if self.ids is not None:
				self.ids.extend(ids)

	# Store a value, aborting the transaction when a write or notification fails.
	# ----------------------------------------------------------------------
	def set(self, key, value, owner_id):
		try:
			self.tx.put(self.memory._key(key), self.memory.to_bytes(value))

			if self.sync is not None:
				self._notify(owner_id)
		except Exception:
			self.failed = True
			raise

	# Remove an existing key and notify Sync about its changed owner.
	# ----------------------------------------------------------------------
	def unset(self, key, owner_id):
		try:
			deleted = self.tx.delete(self.memory._key(key))

			if deleted and self.sync is not None:
				self._notify(owner_id)
		except Exception:
			self.failed = True
			raise

	# Notify all known owners before deleting their stored prefix.
	# ----------------------------------------------------------------------
	def unset_all(self, key_prefix, owner_id):
		try:
			prefix = self.memory._key(key_prefix)
			cursor = self.tx.cursor()
			ok     = cursor.set_range(prefix)

			if ok and cursor.key().startswith(prefix) and self.sync is not None:
				self._notify(owner_id)

			while ok:
				key = cursor.key()

				if not key.startswith(prefix):
					break

				cursor.delete()
				ok = cursor.set_range(prefix)
		except Exception:
			self.failed = True
			raise

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
		self.owner_id = None

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



	# Store a zone value, preserving its cache through commit confirmation.
	# ----------------------------------------------------------------------
	def set(self, key, value=None, owner_id=None):
		try:
			with self.memory.write() as batch:
				if batch.depth > 1:
					batch._track_zone(self)

				batch.set(self._key(key), value, self.owner_id if owner_id is None else owner_id)
				self.cache[key] = value
		except Exception:
			self.cache.pop(key, None)
			raise

	# Remove a zone key; failed writes cannot leave a stale cached value.
	# ----------------------------------------------------------------------
	def unset(self, key, owner_id=None):
		try:
			with self.memory.write() as batch:
				if batch.depth > 1:
					batch._track_zone(self)

				batch.unset(self._key(key), self.owner_id if owner_id is None else owner_id)
				self.cache[key] = UNDEFINED
		except Exception:
			self.cache.pop(key, None)
			raise

	# Clear a zone prefix and discard cached reads of its former contents.
	# ----------------------------------------------------------------------
	def clear(self, owner_id=None):
		try:
			with self.memory.write() as batch:
				if batch.depth > 1:
					batch._track_zone(self)

				batch.unset_all(self.prefix, self.owner_id if owner_id is None else owner_id)
		finally:
			self.cache.clear()

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
		self.sync    = o.services.Sync

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

	# Store a value with its affected ID or iterable of IDs.
	# None requests full Sync invalidation for unknown owners.
	# ----------------------------------------------------------------------
	def set(self, key, value, owner_id):
		with self.write() as batch:
			batch.set(key, value, owner_id)

	# Remove a key and notify its affected owners when present.
	# ----------------------------------------------------------------------
	def unset(self, key, owner_id):
		with self.write() as batch:
			batch.unset(key, owner_id)

	# Delete a prefix; report every affected owner or None.
	# ----------------------------------------------------------------------
	def unset_all(self, key_prefix, owner_id):
		with self.write() as batch:
			batch.unset_all(key_prefix, owner_id)


	# Resolve the current transaction's value, including pending writes.
	# ----------------------------------------------------------------------
	def get(self, key, default=UNDEFINED):
		batch = self._write

		if batch is not None and batch.tx is not None:
			value = batch.get(key, default)
		else:
			with self.read() as batch:
				value = batch.get(key, default)

		return value

	# Check existence against pending writes before committed storage.
	# ----------------------------------------------------------------------
	def has(self, key):
		batch = self._write

		if batch is not None and batch.tx is not None:
			result = batch.has(key)
		else:
			with self.read() as batch:
				result = batch.has(key)

		return result

	# Iterate stored items with read-your-writes consistency.
	# ----------------------------------------------------------------------
	def items(self, prefix=''):
		batch = self._write

		if batch is not None and batch.tx is not None:
			yield from batch.items(prefix)
		else:
			with self.read() as batch:
				yield from batch.items(prefix)

	# Iterate stored keys with read-your-writes consistency.
	# ----------------------------------------------------------------------
	def keys(self, prefix=''):
		batch = self._write

		if batch is not None and batch.tx is not None:
			yield from batch.keys(prefix)
		else:
			with self.read() as batch:
				yield from batch.keys(prefix)

