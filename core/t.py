import o


class T(o.Node):
	
	# Initialize schema
	# ----------------------------------------------------------------------
	def __init__(self, **data):

		# Create empty container
		# - - - - - - - - - - - - - - - - - - - -
		self.__id__ = o.services.Many.create('QHQ')
		self.__items__ = []
		self.__index__ = {}

		# Validate unknown fields
		# - - - - - - - - - - - - - - - - - - - -
		for name in data:
			if name not in self.__class__.__fields__:
				raise TypeError(f'Unknown field `{name}` in {self.__o_module__}.')

		# Validate and set fields
		# - - - - - - - - - - - - - - - - - - - -
		for fname, field in self.__class__.__fields__.items():
			fvalue = data.get(fname, o.undefined)
			value  = field.validate(fvalue)
			setattr(self, fname, value)

		self.__write__()

	# Collect definition fields
	# ----------------------------------------------------------------------
	def __init_subclass__(cls, *args, **kwargs):

		# Inherit parent fields
		# - - - - - - - - - - - - - - - - - - - -
		cls.__fields__ = cls.__bases__[0].__fields__.copy()

		# Add fields declared as annotation
		# - - - - - - - - - - - - - - - - - - - -
		for name, ftype in cls.__annotations__.items():
			default = o.undefined

			if name in cls.__dict__:
				default = cls.__dict__[name]
				delattr(cls, name)

			cls.__fields__[name] = o.F(
				name        = name,
				type        = ftype,
				description = None,
				default     = default
			)
			
		# Add fields declared as o.F
		# - - - - - - - - - - - - - - - - - - - -
		for name, value in list(cls.__dict__.items()):
			if isinstance(value, o.F):
				value.name = name
				cls.__fields__[name] = value
				delattr(cls, name)

		cls.__annotations__.clear()
		cls.register()

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	@classmethod
	def define(cls, type_name, **fields):

		# Process fields
		# - - - - - - - - - - - - - - - - - - - -
		__fields__ = {}

		for fname, f in fields.items():
			if isinstance(f, o.F):
				f.name = fname
				__fields__[fname] = f
			else:
				__fields__[fname] = o.F(
					name        = fname,
					type        = f,
					description = None,
					default     = o.undefined,
				)

		# Create new schema class
		# - - - - - - - - - - - - - - - - - - - -
		new_class = type(
			type_name,
			(cls,),
			{}
		)
		new_class.register()
		new_class.__fields__ = __fields__

		return new_class

	# ----------------------------------------------------------------------
	def __repr__(self):
		cls     = self.__class__
		parent  = None
		t_found = False

		for base in cls.__mro__:
			if not t_found:
				if base is o.T:
					t_found = True
			else:
				if base is not o.T:
					parent = base
					break

		if parent:
			return f'<{self.__o_module__} ({parent.__o_module__}) id={self.__id__}>'
		return f'<{self.__o_module__} id={self.__id__}>'