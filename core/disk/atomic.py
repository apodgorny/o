import os

import o


class Atomic(o.Module):

	FILE = '__value__'

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Constructor
	# ----------------------------------------------------------------------
	def __init__(self, instance_path):
		self.instance_path = instance_path
		self.path          = os.path.join(instance_path, self.FILE)
		self.data          = o.undefined

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Set atomic state
	# ----------------------------------------------------------------------
	def set(self, value):
		self.data = value

		with open(self.path, 'wb') as file:
			file.write(value)

	# Get atomic state
	# ----------------------------------------------------------------------
	def get(self):
		if self.data is o.undefined and os.path.exists(self.path):
			with open(self.path, 'rb') as file:
				self.data = file.read()

		return self.data
