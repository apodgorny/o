import os

import o


class Subclasses(o.Module):

	DIR = '__subclasses__'

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Constructor
	# ----------------------------------------------------------------------
	def __init__(self, parent_path):
		self.parent_path = parent_path
		self.path        = os.path.join(parent_path, self.DIR)
		self.items       = {}

		os.makedirs(self.path, exist_ok=True)

		for name in os.listdir(self.path):
			path = os.path.join(self.path, name)

			if os.path.isdir(path) and len(name) > 0 and name[0].isupper():
				self.items[name] = None

	# Set subclass item
	# ----------------------------------------------------------------------
	def set(self, name):
		item = None

		if len(name) == 0 or not name[0].isupper():
			raise ValueError(f'Subclass name `{name}` must start with a capital letter')

		item = o.disk.Class(os.path.join(self.path, name))
		self.items[name] = item

		return item

	# Get subclass item
	# ----------------------------------------------------------------------
	def get(self, name):
		return self.items.get(name)

	# Check subclass item
	# ----------------------------------------------------------------------
	def has(self, name):
		return name in self.items
