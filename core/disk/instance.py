# <class_path>/
# 	__fields__/
# 		<field_name>/
# 			<property_name>
# 			<property_name>
# 			<property_name>

# 	__subclasses__/
# 		<ClassName>/
# 		<ClassName>/
# 		<ClassName>/

# 	__instances__/
# 		__index__
# 		_0/
# 			__list__      # only if annotation.is_list
# 			__attributes__/ # optional named refs

# 		_1/
# 			__dict__      # only if annotation.is_dict
# 			__attributes__/ # optional named refs

# 		_2/
# 			__value__     # only if annotation.is_atomic
# 			__attributes__/ # optional named refs

# 		_3/
# 			# object: neither __list__ nor __dict__ nor __value__

import os, shutil

import o


class Instance(o.disk.Entity):

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Constructor
	# ----------------------------------------------------------------------
	def __init__(self, path, annotation=o.undefined):
		super().__init__(path)
		os.makedirs(self.path, exist_ok=True)

		self.annotation = o.Annotation(annotation)
		self.attributes = o.disk.Attributes(self.path)

		if annotation is o.undefined:
			if os.path.exists(os.path.join(self.path, o.disk.List.FILE)):
				self.list = o.disk.List(self.path)
			elif os.path.exists(os.path.join(self.path, o.disk.Dict.FILE)):
				self.dict = o.disk.Dict(self.path)
			elif os.path.exists(os.path.join(self.path, o.disk.Atomic.FILE)):
				self.atomic = o.disk.Atomic(self.path)
		else:
			if self.annotation.is_list:
				self.list = o.disk.List(self.path)
			elif self.annotation.is_dict:
				self.dict = o.disk.Dict(self.path)
			elif self.annotation.is_atomic:
				self.atomic = o.disk.Atomic(self.path)

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Delete instance room
	# ----------------------------------------------------------------------
	def delete(self):
		if os.path.exists(self.path):
			shutil.rmtree(self.path)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================
