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
# 			__list__       # only if annotation.is_list
# 			__dict__       # only if annotation.is_dict
# 			__value__      # only if annotation.is_atomic
# 			__attributes__/ # optional named refs

# 		_1/
# 			__list__       # only if annotation.is_list

# 		_2/
# 			__dict__       # only if annotation.is_dict

# 		_3/
# 			__value__      # only if annotation.is_atomic

# 		_4/
# 			# object: neither __list__ nor __dict__ nor __value__


import os

import o

class Class(o.disk.Entity):

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Constructor
	# ----------------------------------------------------------------------
	def __init__(self, path, id=o.undefined):
		super().__init__(path, id=id)

		os.makedirs(self.path, exist_ok=True)

		self._annotation     = o.undefined
		self.annotation_path = os.path.join(self.path, '__annotation__')
		self._o_module       = o.undefined
		self.o_module_path   = os.path.join(self.path, '__o_module__')
		self.fields          = o.disk.Fields(self.path)
		self.subclasses      = o.disk.Subclasses(self.path)
		self.instances       = o.disk.Instances(self.path)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Class annotation
	# ----------------------------------------------------------------------
	@property
	def annotation(self):
		if self._annotation is o.undefined:
			if os.path.exists(self.annotation_path):
				with open(self.annotation_path, 'r') as file:
					self._annotation = o.Annotation(file.read()).annotation

		return self._annotation

	@annotation.setter
	def annotation(self, annotation):
		if annotation is not o.undefined and annotation != self._annotation:
			with open(self.annotation_path, 'w') as file:
				file.write(str(annotation))

			self._annotation = annotation

	# Class module
	# ----------------------------------------------------------------------
	@property
	def o_module(self):
		if self._o_module is o.undefined:
			if os.path.exists(self.o_module_path):
				with open(self.o_module_path, 'r') as file:
					self._o_module = file.read()

		return self._o_module

	@o_module.setter
	def o_module(self, o_module):
		if o_module is not o.undefined and o_module != self._o_module:
			with open(self.o_module_path, 'w') as file:
				file.write(o_module)

			self._o_module = o_module
