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

	# Reconcile public class room from hidden source class
	# ----------------------------------------------------------------------
	@classmethod
	def reconcile(cls, source_cls):
		name             = source_cls.__name__
		base_cls         = source_cls.__parent__
		proto            = f'{base_cls.__proto__}.{name}'
		field_names      = set()
		disk_field       = None
		disk_class       = cls.get(proto)
		source_fields    = getattr(source_cls, '__source_fields__', {})
		disk_class.route = source_cls.__route__

		# Collect current source field names
		# - - - - - - - - - - - - - - - - - - - -
		for field_name in source_fields:
			field_names.add(field_name)

		# Remove stale source-backed fields
		# - - - - - - - - - - - - - - - - - - - -
		for field_name, disk_field in list(disk_class.fields.items()):
			if disk_field.has('__is_source__') and field_name not in field_names:
				for prop_name, _ in list(disk_field.properties):
					disk_field.remove(prop_name)

				disk_field.remove('__is_source__')

				if os.path.exists(disk_field.path):
					os.rmdir(disk_field.path)

				del disk_class.fields.__items__[field_name]

		# Upsert current source-backed fields
		# - - - - - - - - - - - - - - - - - - - -
		for field_name, props in source_fields.items():
			disk_field = disk_class.fields.set(field_name)

			for prop_name, prop_value in props.items():
				if prop_name == 'default':
					if prop_value is not o.Undefined:
						disk_field.set(prop_name, prop_value)
				else:
					disk_field.set(prop_name, prop_value)

			if (
				'default' not in props
				or props.get('default', o.Undefined) is o.Undefined
			) and disk_field.has('default'):
				disk_field.remove('default')

			open(os.path.join(disk_field.path, '__is_source__'), 'wb').close()

		return disk_class

	# Get cached or create class
	# ----------------------------------------------------------------------
	@classmethod
	def get(cls, proto):
		id         = o.proto_to_id(proto)
		disk_class = o.__disk_classes__.get(id, o.Undefined)

		if disk_class is o.Undefined:
			disk_class = cls(proto, id=id)
			o.__disk_classes__[id] = disk_class

		return disk_class

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Constructor
	# ----------------------------------------------------------------------
	def __init__(self, path, id=o.Undefined):
		super().__init__(path, id=id)

		os.makedirs(self.path, exist_ok=True)

		self._annotation     = o.Undefined
		self.annotation_path = os.path.join(self.path, '__annotation__')
		self._route          = o.Undefined
		self.route_path      = os.path.join(self.path, '__route__')
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
