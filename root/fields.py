import o


class Fields(o.Module):

	# Iterate bound field names
	# ----------------------------------------------------------------------
	def __iter__(self):
		if '__owner_id__' not in self.__dict__:
			raise RuntimeError('Namespace object is not bound to class')

		owner = o.__entities__[self.__owner_id__]

		return iter(owner.__disk_class__.fields)

	# Get bound field view
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		if '__owner_id__' not in self.__dict__:
			raise RuntimeError('Namespace object is not bound to class')
			
		field = None
		owner = o.__entities__[self.__owner_id__]

		if owner.__disk_class__.fields.has(name):
			field = o.Field(owner, name)

		if field is None:
			raise AttributeError(name)

		return field

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Iterate bound field views
	# ----------------------------------------------------------------------
	def items(self):
		if '__owner_id__' not in self.__dict__:
			raise RuntimeError('Namespace object is not bound to class')

		owner = o.__entities__[self.__owner_id__]

		return (
			(name, o.Field(owner, name))
			for name in owner.__disk_class__.fields
		)

	# Bind fields to class
	# ----------------------------------------------------------------------
	def bind(self, cls):
		self.__owner_id__ = cls.id

		if '__fields__' in self.__dict__:

			# Source definition is authoritative
			# - - - - - - - - - - - - - - - - - - - -
			cls.__disk_class__.fields.delete()

			for name, props in self.__fields__.items():
				field = o.Field(cls, name)
				field.__write__(props)
				field.__publish__(props)

			del self.__fields__
		else:
			for name in cls.__disk_class__.fields:
				field = o.Field(cls, name)
				field.__publish__(field.__read__())

		setattr(cls, '_', self)

	# Create or load own field layer
	# ----------------------------------------------------------------------
	def add(self, name, type_id, default=o.Undefined, props=None):
		fields = self.__dict__.get('__fields__')

		if fields is None:
			fields = {}
			self.__fields__ = fields

		fields[name] = {
			'type'       : type_id,
			'default'    : default,
			** (props or {}),
		}
