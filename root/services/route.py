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
		owner_id = o.services.Memory.root_id

		if isinstance(value, dict) and type(value.get('id')) is int:
			owner_id = (owner_id, value['id'])

		self.zone.set(route, value, owner_id)

	# Remove route metadata.
	# ----------------------------------------------------------------------
	def unset(self, route):
		self.zone.unset(route, o.services.Memory.root_id)

	# Read the source route persisted for a prototype.
	# ----------------------------------------------------------------------
	def proto_to_route(self, proto):
		return o.services.Memory.get(f'{proto}.__route__', UNDEFINED)
