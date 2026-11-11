# ==============================================================================
# MEMORY SERVICE
# ==============================================================================
# Persist ontology state and its committed change identities in one LMDB store.
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
		self.changed_ids = set()

	# If we are already in a transaction, just return ourselves
	# ----------------------------------------------------------------------
	def __enter__(self):
		if self.tx is None:
			self.ctx         = self.memory.env.begin(write=self.write)
			self.tx          = self.ctx.__enter__()
			self.changed_ids = set()

		self.depth += 1
		return self

	# Commit change identities with data, or discard both after an error.
	# ----------------------------------------------------------------------
	def __exit__(self, exc_type, exc, tb):
		self.depth -= 1

		if self.ctx is not None and self.depth == 0:
			try:
				if self.write and exc_type is None and self.changed_ids:
					key   = f'changes/{self.tx.id():020d}'
					value = self.memory.to_bytes(sorted(self.changed_ids))
					self.tx.put(self.memory._key(key), value)
			except BaseException as error:
				self.ctx.__exit__(type(error), error, error.__traceback__)
				raise
			else:
				self.ctx.__exit__(exc_type, exc, tb)
			finally:
				if self.write:
					self.memory._write = None
				else:
					self.memory._read = None

				self.changed_ids.clear()
				self.tx  = None
				self.ctx = None

		return False

	# Delegation
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		return getattr(self.memory, name)

	# Record IDs affected by a direct memory write.
	# An unknown storage key conservatively invalidates the whole ontology.
	# ----------------------------------------------------------------------
	def _record_key(self, key, value=UNDEFINED):
		key = str(key)
		ids = self.changed_ids

		if key == 'o.T' or key.startswith('o.T.'):
			parts = key.split('.')
			proto_parts = parts[:2]

			for part in parts[2:]:
				if part and (part[0].isupper() or part.startswith('_') and part[1:].isdigit()):
					proto_parts.append(part)

					if part.startswith('_'):
						break
				else:
					break

			proto = '.'.join(proto_parts)
			ids.add(o.String.hash(proto, 15))

			if key == proto and len(proto_parts) > 2:
				ids.add(o.String.hash('.'.join(proto_parts[:-1]), 15))

			if '.__auth__/' in key:
				node_id = key.rsplit('/', 1)[-1]
				ids.add(int(node_id) if node_id.isdecimal() else 0)

		elif key.startswith(('ids/', 'garbage/refcounts/', 'garbage/items/', 'tree/parents/')):
			entity_id = key.rsplit('/', 1)[-1]
			ids.add(int(entity_id) if entity_id.isdecimal() else 0)

			if key.startswith('tree/parents/'):
				ids.add(value if type(value) is int else 0)

		elif key.startswith('routes/'):
			ids.add(self.memory.root_id)

			if isinstance(value, dict) and type(value.get('id')) is int:
				ids.add(value['id'])

		elif not key.startswith('changes/'):
			ids.add(0)

	# Store value and observe its owner only after the LMDB put succeeds.
	# ----------------------------------------------------------------------
	def set(self, key, value, owner_id=None):
		self.tx.put(self.memory._key(key), self.memory.to_bytes(value))

		if self.write:
			if owner_id is None:
				self._record_key(key, value)
			else:
				self.changed_ids.add(owner_id)

	# Remove a key and record its owner only if it existed.
	# ----------------------------------------------------------------------
	def unset(self, key, owner_id=None):
		deleted = self.tx.delete(self.memory._key(key))

		if deleted and self.write:
			if owner_id is None:
				self._record_key(key)
			else:
				self.changed_ids.add(owner_id)

	# Delete a prefix, reading individual owners only for mixed-owner zones.
	# A root instance zone may also hold authorization keys for other objects.
	# ----------------------------------------------------------------------
	def unset_all(self, key_prefix, owner_id=None):
		prefix = self.memory._key(key_prefix)
		cursor = self.tx.cursor()
		ok     = cursor.set_range(prefix)

		name = key_prefix.rstrip('.').rsplit('.', 1)[-1]
		scan = owner_id is None or not (name.startswith('_') and name[1:].isdigit())
		removed = False

		while ok:
			key = cursor.key()

			if not key.startswith(prefix):
				break

			cursor.delete()
			removed = True

			if self.write and (scan or b'.__auth__/' in key):
				self._record_key(key.decode('utf-8'))

			ok = cursor.set_range(prefix)

		if removed and self.write and owner_id is not None:
			self.changed_ids.add(owner_id)

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

	# Scan keys by prefix, optionally seeking past a known starting key.
	# ----------------------------------------------------------------------
	def _pairs(self, prefix='', start=None):
		key      = self.memory._key(prefix)
		seek     = self.memory._key(start) if start is not None else key
		cursor   = self.tx.cursor()
		has_item = cursor.set_range(seek) if seek else cursor.first()

		while has_item:
			key_bytes = cursor.key()

			if not key_bytes.startswith(key):
				break

			yield key_bytes.decode('utf-8'), cursor.value()
			has_item = cursor.next()

	# Seek to the first committed change after the given transaction ID.
	# ----------------------------------------------------------------------
	def changes(self, after_transaction=0):
		start = f'changes/{after_transaction + 1:020d}'

		for key, value in self._pairs('changes/', start):
			yield int(key.removeprefix('changes/')), set(self.memory.from_bytes(value))

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

	# Set value
	# ----------------------------------------------------------------------
	def set(self, key, value=None):
		self.cache[key] = value
		self.memory.set(self._key(key), value, self.owner_id)

	# Remove value
	# ----------------------------------------------------------------------
	def unset(self, key):
		self.cache[key] = UNDEFINED
		self.memory.unset(self._key(key), self.owner_id)

	# Clear zone
	# ----------------------------------------------------------------------
	def clear(self):
		self.cache.clear()
		self.memory.unset_all(self.prefix, self.owner_id)

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
	def set(self, key, value=None, owner_id=None):
		with self.write() as batch:
			batch.set(key, value, owner_id)

	# Remove key
	# ----------------------------------------------------------------------
	def unset(self, key, owner_id=None):
		with self.write() as batch:
			batch.unset(key, owner_id)

	# Unset all keys by prefix
	# ----------------------------------------------------------------------
	def unset_all(self, key_prefix, owner_id=None):
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

	# Return committed transaction changes, ordered by LMDB transaction ID.
	# ID zero is a conservative full-ontology invalidation signal.
	# ----------------------------------------------------------------------
	def changes(self, after_transaction=0):
		with self.read() as batch:
			yield from batch.changes(after_transaction)

	# Read the latest committed LMDB transaction ID for incremental polling.
	# ----------------------------------------------------------------------
	def revision(self):
		return self.env.info()['last_txnid']
