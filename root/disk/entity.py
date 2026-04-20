import os

import o


class Entity(o.Module):

	# Initialize disk entity
	# ----------------------------------------------------------------------
	def __init__(self, path_or_proto=None, id=o.Undefined):
		if path_or_proto.startswith('o.T'):
			self.path  = o.proto_to_path(path_or_proto)
			self.id    = id if id is not o.Undefined else o.proto_to_id(path_or_proto)
		else:
			self.path  = path_or_proto
			self.id    = id if id is not o.Undefined else o.path_to_id(self.path)

		o.services.Registry.add(self.id, self.path)

	# Load disk entity by id
	# ----------------------------------------------------------------------
	@classmethod
	def load(cls, id):
		path        = o.id_to_path(id)
		entity      = o.Undefined

		if path is not o.Undefined:
			name        = os.path.basename(path)
			is_instance = o.is_instance_version(name)
			entity      = o.disk.Instance(path, o.Undefined, id=id) if is_instance else o.disk.Class(path, id=id)

		return entity
