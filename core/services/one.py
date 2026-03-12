import os, struct, heapq, mmap, hashlib

import o



class One(o.Service):

	def initialize(self):
		self.IS_ACTIVE   = 1

		self.dir         = o.db.one
		self.max_type_id = 0

		self.names = {}  # type_id   : name
		self.ids   = {}  # type_name : id
		self.words = {}  # type_id   : size
		self.files = {}  # type_id   : file handle
		self.free  = {}  # type_id   : heapq[free ids]
		self.dirty = set()

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Creates type if not exists. Returns deterministic type id (Q)
	# ----------------------------------------------------------------------
	def define(self, type_name, type_id, type_word):
		type_word = '<B' + type_word.lstrip('<>')
		existing  = self.ids.get(type_name)

		if existing is None:

			type_path = os.path.join(self.dir.path, type_name)
			type_mode = 'r+b' if os.path.exists(type_path) else 'w+b'
			f         = open(type_path, type_mode)

			self.ids   [type_name] = type_id
			self.names [type_id]   = type_name
			self.words [type_id]   = struct.Struct(type_word)
			self.files [type_id]   = f
			self.free  [type_id]   = []

			# Collect ids of deleted records into heap
			# - - - - - - - - - - - - - - - - - - - -
			for id, data, is_active in self.iter(type_id):
				if not is_active:
					self.free[type_id].append(id)

			heapq.heapify(self.free[type_id])

		else:
			type_id = existing
			if type_word != self.words[type_id].format:
				raise IOError('Inconsistent word pattern')

		return type_id
		
	# Erases type data completely
	# ----------------------------------------------------------------------
	def undefine(self, type_name):
		type_id = self.ids.get(type_name, None)

		if type_id is not None:
			self.files[type_id].close()

			del self.ids   [type_name]
			del self.names [type_id]
			del self.words [type_id]
			del self.files [type_id]
			del self.free  [type_id]

			self.dirty.discard(type_id)

			type_path = os.path.join(self.dir.path, type_name)
			if os.path.exists(type_path):
				os.remove(type_path)
			return True
		return False

	# Read fixed-size record by instance_id and return payload if active
	# ----------------------------------------------------------------------
	def read(self, type_id, instance_id):
		f    = self.files[type_id]
		word = self.words[type_id]
		size = word.size

		f.seek(size * instance_id)
		raw = f.read(size)
		
		if len(raw) != size:
			raise IOError('Corrupted record')

		data = word.unpack(raw)
		if data[0] != self.IS_ACTIVE:
			raise ValueError('Record is not active')
		return data[1]

	# Write fixed-size record at instance_id or append new record if None
	# ----------------------------------------------------------------------
	def write(self, type_id, instance_id, *data):
		word = self.words[type_id]
		size = word.size
		f    = self.files[type_id]
		free = self.free[type_id]
		data = word.pack(self.IS_ACTIVE, *data)

		if instance_id is None:
			if free:
				instance_id = heapq.heappop(free)
			else:
				offset = f.seek(0, os.SEEK_END)
				instance_id = offset // size
		# else:
		# 	if instance_id in free:
		# 		raise ValueError(f'Found id {instance_id} in heap')

		f.seek(size * instance_id)
		f.write(data)
		self.dirty.add(type_id)
		return instance_id

	# Mark record as deleted by zeroing bytes and pushing id to free heap
	# ----------------------------------------------------------------------
	def delete(self, type_id, instance_id):
		size = self.words[type_id].size
		f    = self.files[type_id]
		free = self.free[type_id]
		deleted = False

		f.seek(size * instance_id)
		raw = f.read(size)

		if len(raw) != size:
			raise IOError('Corrupted record')

		if raw[0] == self.IS_ACTIVE:
			f.seek(size * instance_id)
			f.write(b'\x00' * size)
			heapq.heappush(free, instance_id)
			self.dirty.add(type_id)
			deleted = True

		return deleted

	# Iterate over all records sequentially yielding id, payload and active flag
	# ----------------------------------------------------------------------
	def iter(self, type_id):
		word = self.words[type_id]
		size = word.size
		f    = self.files[type_id]

		f.flush()

		if os.fstat(f.fileno()).st_size > 0:
			with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
				for i in range(len(mm) // size):
					offset = i * size
					data   = word.unpack_from(mm, offset)
					yield i, data[1], data[0]

	# Flush and fsync all dirty container files
	# ----------------------------------------------------------------------
	def commit(self):
		for type_id in self.dirty:
			f = self.files[type_id]
			f.flush()
			os.fsync(f.fileno())
		self.dirty.clear()
