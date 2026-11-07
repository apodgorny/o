# ==============================================================================
# ROUTE SERVICE
# ==============================================================================
# Persist source routes and resolve prototype source metadata.
# ==============================================================================

import o

UNDEFINED = o.Undefined


class Route(o.Service):

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Open the source-route mapping after memory initialization.
	# ----------------------------------------------------------------------
	def initialize(self):
		self.zone = o.services.Memory.zone('routes/')

	# Get metadata for a registered source route.
	# ----------------------------------------------------------------------
	def get(self, route, default=UNDEFINED):
		return self.zone.get(route, default)

	# Check whether a route is registered.
	# ----------------------------------------------------------------------
	def has(self, route):
		return self.zone.has(route)

	# Register route metadata.
	# ----------------------------------------------------------------------
	def set(self, route, value):
		self.zone.set(route, value)

	# Remove route metadata.
	# ----------------------------------------------------------------------
	def unset(self, route):
		self.zone.unset(route)

	# Read the source route persisted for a prototype.
	# ----------------------------------------------------------------------
	def proto_to_route(self, proto):
		return o.services.Memory.get(f'{proto}.__route__', UNDEFINED)
