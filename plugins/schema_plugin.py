import os


class SchemaPlugin:
	def match(self, path):
		full_path = f'{path}.foo'
		return os.path.exists(full_path)

	def load(self, path, lib):
		full_path = f'{path}.foo'
		with open(full_path, 'r') as f:
			return f.read()
