import o

UNDEFINED = o.Undefined


class Routes(o.Service):

	# Initialize service
	# ----------------------------------------------------------------------
	def initialize(self):
		self.zone = o.services.Memory.zone('routes/')

	# Resolve route metadata
	# ----------------------------------------------------------------------
	def get(self, route, default=UNDEFINED):
		return self.zone.get(route, default)

	# Check route metadata
	# ----------------------------------------------------------------------
	def has(self, route):
		return self.zone.has(route)

	# Store route metadata
	# ----------------------------------------------------------------------
	def set(self, route, value):
		self.zone.set(route, value)

	# Remove route metadata
	# ----------------------------------------------------------------------
	def unset(self, route):
		self.zone.unset(route)
