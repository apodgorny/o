import os, struct

import o



class Many(o.Service):

	def initialize(self):
		self.dir    = o.db.many
		self.words  = {}   # id : struct
		self.files  = {}   # id : file handle
		self.dirty  = set()
		self.max_id = self._scan_max_id()

	def _scan_max_id(self):
		max_id = 0
		for name in os.listdir(self.dir.path):
			if name.isdigit():
				id_ = int(name)
				if id_ > max_id:
					max_id = id_
		return max_id

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Create container file for id and register struct format
	# ----------------------------------------------------------------------
	def create(self, word):
		self.max_id += 1

		id   = self.max_id
		word = '<' + word.lstrip('<>')
		path = os.path.join(self.dir.path, str(id))
		mode = 'r+b' if os.path.exists(path) else 'w+b'

		self.files[id] = open(path, mode)
		self.words[id] = struct.Struct(word)

		return id

	# Delete container file and remove internal references
	# ----------------------------------------------------------------------
	def delete(self, id):
		f = self.files.get(id, None)

		if f is not None:
			f.close()
			del self.files[id]
			del self.words[id]

		path = os.path.join(self.dir.path, str(id))
		if os.path.exists(path):
			os.remove(path)

		self.dirty.discard(id)
		return True

	# Read entire container file and unpack sequential records
	# ----------------------------------------------------------------------
	def read(self, id):
		f    = self.files[id]
		word = self.words[id]
		size = word.size

		f.seek(0)
		raw = f.read()

		if raw:
			if len(raw) % size != 0:
				raise IOError('Corrupted many file')

			return [
				word.unpack_from(raw, i)
				for i in range(0, len(raw), size)
			]
		return []

	# Write full list of items by truncating and rewriting file
	# ----------------------------------------------------------------------
	def write(self, id, items):
		f    = self.files[id]
		word = self.words[id]

		data = b''.join(
			word.pack(*item)
			for item in items
		)

		f.seek(0)
		f.truncate(0)
		f.write(data)

		self.dirty.add(id)
		return True

	# Clear container by truncating file to zero length
	# ----------------------------------------------------------------------
	def clear(self, id):
		f = self.files[id]
		f.seek(0)
		f.truncate(0)
		self.dirty.add(id)
		return True

	# Flush and fsync all dirty container files
	# ----------------------------------------------------------------------
	def commit(self):
		for id in self.dirty:
			f = self.files[id]
			f.flush()
			os.fsync(f.fileno())

		self.dirty.clear()
		return True
