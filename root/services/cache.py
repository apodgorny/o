# ==============================================================================
# CACHE SERVICE
# ==============================================================================
# Track loaded entities and annotation mappings in one runtime-owned registry.
# ==============================================================================

import o


class Cache(o.Service):

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Create both registries before ontology classes begin loading.
	# ----------------------------------------------------------------------
	def initialize(self):
		self.entities = {}
		self.cast_map = {
			int        : 'o.T.Atom.Int',
			float      : 'o.T.Atom.Float',
			bool       : 'o.T.Atom.Bool',
			str        : 'o.T.Atom.Str',
			type(None) : 'o.T.Atom.Null',
			list       : 'o.T.List',
			dict       : 'o.T.Dict',
		}

	# Register a class or instance using both its id and proto.
	# ----------------------------------------------------------------------
	def register(self, entity):
		if entity.id not in self.entities:
			if isinstance(entity, type):
				if '__annotation__' in entity.__dict__:
					annotation = entity.__annotation__.annotation

					if annotation not in self.cast_map:
						self.cast_map[annotation] = entity.__proto__
					else:
						other_proto = self.cast_map[annotation]

						if other_proto != entity.__proto__:
							raise TypeError(f'Annotation `{annotation}` is already defined in `{other_proto}`')

			self.entities[entity.id]        = entity
			self.entities[entity.__proto__] = entity

	# Unregister both lookup keys and the annotation belonging to a class.
	# ----------------------------------------------------------------------
	def unregister(self, entity):
		if entity.id in self.entities:
			if isinstance(entity, type):
				if '__annotation__' in entity.__dict__:
					annotation = entity.__annotation__.annotation

					if annotation in self.cast_map:
						if self.cast_map[annotation] == entity.__proto__:
							del self.cast_map[annotation]

			del self.entities[entity.id]
			del self.entities[entity.__proto__]
