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

	@classmethod
	def get(cls, proto):
		id         = o.proto_to_id(proto)
		disk_class = o.__disk_classes__.get(id, o.Undefined)

		if disk_class is o.Undefined:
			disk_class = cls(proto, id=id)
			o.__disk_classes__[id] = disk_class

		return disk_class

	# Constructor
	# ----------------------------------------------------------------------
	def __init__(self, path, id=o.Undefined):
		super().__init__(path, id=id)

		os.makedirs(self.path, exist_ok=True)

		self._annotation     = o.Undefined
		self.annotation_path = os.path.join(self.path, '__annotation__')
		self._route       = o.Undefined
		self.route_path   = os.path.join(self.path, '__route__')
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
		if self._annotation is o.Undefined:
			if os.path.exists(self.annotation_path):
				with open(self.annotation_path, 'r') as file:
					self._annotation = o.Annotation(file.read()).annotation

		return self._annotation

	@annotation.setter
	def annotation(self, annotation):
		if annotation is not o.Undefined and annotation != self._annotation:
			with open(self.annotation_path, 'w') as file:
				file.write(str(annotation))

			self._annotation = annotation

	# Class module
	# ----------------------------------------------------------------------
	@property
	def route(self):
		if self._route is o.Undefined:
			if os.path.exists(self.route_path):
				with open(self.route_path, 'r') as file:
					self._route = file.read()

		return self._route

	@route.setter
	def route(self, route):
		if route is not o.Undefined and route != self._route:
			with open(self.route_path, 'w') as file:
				file.write(route)

			self._route = route
