import os
import shutil

import o


class Fields(o.Module):

	DIR = '__fields__'

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Constructor
	# ----------------------------------------------------------------------
	def __init__(self, class_path):
		self.class_path = class_path
		self.path       = os.path.join(class_path, self.DIR)
		self.__items__  = {}

		os.makedirs(self.path, exist_ok=True)

		for name in os.listdir(self.path):
			path = os.path.join(self.path, name)

			if os.path.isdir(path):
				self.__items__[name] = o.disk.Field(self.path, name)

	# Iterate field names
	# ----------------------------------------------------------------------
	def __iter__(self):
		return iter(self.__items__)

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Get field path
	# ----------------------------------------------------------------------
	def _get_field_path(self, field_name):
		return os.path.join(self.path, field_name)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Set field manager
	# ----------------------------------------------------------------------
	def set(self, field_name):
		if any(char.isupper() for char in field_name):
			raise ValueError(f'Field name `{field_name}` must not contain uppercase letters')

		field = self.__items__.get(field_name)

		if field is None:
			field = o.disk.Field(self.path, field_name)
			self.__items__[field_name] = field

		return field

	# Get field manager
	# ----------------------------------------------------------------------
	def get(self, field_name):
		return self.__items__.get(field_name)

	# Check field manager
	# ----------------------------------------------------------------------
	def has(self, field_name):
		return field_name in self.__items__

	# Iterate field managers
	# ----------------------------------------------------------------------
	def items(self):
		return self.__items__.items()

	# Delete all field managers
	# ----------------------------------------------------------------------
	def delete(self):
		if os.path.exists(self.path):
			shutil.rmtree(self.path)

		self.__items__ = {}
		os.makedirs(self.path)
