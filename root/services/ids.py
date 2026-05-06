import o

UNDEFINED = o.Undefined


class Ids(o.Service):

	# Initialize service
	# ----------------------------------------------------------------------
	def initialize(self):
		self.zone = o.services.Memory.zone('ids/')

	# Store proto mapping and return id
	# ----------------------------------------------------------------------
	def set(self, proto):
		id = o.String.hash(proto, 15)
		self.zone.set(id, proto)
		return id

	# Resolve proto by id
	# ----------------------------------------------------------------------
	def get(self, id, default=UNDEFINED):
		proto = self.zone.get(id, default)
		return proto

	# Check id
	# ----------------------------------------------------------------------
	def has(self, id):
		result = self.zone.has(id)
		return result

	# Remove id mapping
	# ----------------------------------------------------------------------
	def unset(self, id):
		self.zone.unset(id)
