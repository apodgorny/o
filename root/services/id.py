# ==============================================================================
# ID SERVICE
# ==============================================================================
# Persist deterministic mappings between ontology identifiers and prototypes.
# ==============================================================================

import o

UNDEFINED = o.Undefined


class Id(o.Service):

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Open the identifier mapping in the initialized memory store.
	# ----------------------------------------------------------------------
	def initialize(self):
		self.zone = o.services.Memory.zone('ids/')

	# Calculate an identifier without writing a proto mapping.
	# ----------------------------------------------------------------------
	def hash(self, proto):
		return o.String.hash(proto, 15)

	# Store the proto associated with a deterministic numeric id.
	# ----------------------------------------------------------------------
	def set(self, proto):
		id = self.hash(proto)
		self.zone.set(id, proto)
		return id

	# Resolve a previously stored numeric id to its prototype.
	# ----------------------------------------------------------------------
	def get(self, id, default=UNDEFINED):
		return self.zone.get(id, default)

	# Check whether the id has a persisted mapping.
	# ----------------------------------------------------------------------
	def has(self, id):
		return self.zone.has(id)

	# Remove an id mapping.
	# ----------------------------------------------------------------------
	def unset(self, id):
		self.zone.unset(id)
