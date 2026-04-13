import os

import o


class Entity(o.Module):

	# Initialize disk entity
	# ----------------------------------------------------------------------
	def __init__(self, path_or_proto=None):
		if path_or_proto.startswith('o.T'):
			self.path = o.proto_to_path(path_or_proto)
		else:
			self.path = path_or_proto

		self.id = o.path_to_id(self.path)

		o.services.Registry.add(self.id, self.path)

	# Delete disk entity
	# ----------------------------------------------------------------------
	def __del__(self):
		id = self.__dict__.get('id')

		if id is not None:
			try:
				o.services.Registry.remove(id)
			except Exception:
				pass

	# Load disk entity by id
	# ----------------------------------------------------------------------
	@classmethod
	def load(cls, id):
		path        = o.id_to_path(id)
		entity      = o.undefined

		if path is not o.undefined:
			name        = os.path.basename(path)
			is_instance = o.is_instance_version(name)
			entity      = o.disk.Instance(path, o.undefined) if is_instance else o.disk.Class(path)

		return entity
