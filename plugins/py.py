import os

import o


class Py(o.Plugin):

	EXTENSIONS = ['py']

	# Resolve python class file
	# ----------------------------------------------------------------------
	def __resolve__(self, name, parent_path, parent_route):
		path       = None
		class_name = None
		route      = None

		# bar.py /mypath/foo wl
		# - - - - - - - - - - - - - - - - - - - -
		try_path = os.path.join(parent_path, name)
		if os.path.isfile(try_path):
			class_name = self.lib.String.snake_to_camel(os.path.splitext(name)[0])
			path       = try_path

		# Bar /mypath/foo wl
		# - - - - - - - - - - - - - - - - - - - -
		else:
			module_name = self.lib.String.camel_to_snake(name)
			for ext in self.EXTENSIONS:
				try_path = os.path.join(parent_path, f'{module_name}.{ext}')
				if os.path.isfile(try_path):
					class_name = name
					path       = try_path
					break

		if class_name is not None:
			route = f'{parent_route}.{class_name}'

		return path, class_name, route

	# Resolve python carrier
	# ----------------------------------------------------------------------
	def __call__(self, name, parent_path, parent_route):
		file = None
		lib  = self.lib

		path, class_name, route = self.__resolve__(name, parent_path, parent_route)

		if path is not None:

			# - - - - - - - - - - - - - - - - - - - -
			# Load method
			# - - - - - - - - - - - - - - - - - - - -
			def load_method():
				cls = lib.Imports.get_class(lib, class_name, path, route)
				if not issubclass(cls, (lib.Module, lib.ModuleMeta)):
					raise Exception(f'Class `{path}` does not extend from `Module`')
				elif issubclass(cls, lib.Service):
					cls = cls()
				return cls
			
			# - - - - - - - - - - - - - - - - - - - -
			# Hash method
			# - - - - - - - - - - - - - - - - - - - -
			def hash_method():
				return os.path.getmtime(path)
			# - - - - - - - - - - - - - - - - - - - -

			file = self.lib.File(self.lib, path, route, load_method, hash_method)

		return file
