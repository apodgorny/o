import o

# ================================================================================
#                                CLASS TMeta
# ================================================================================

class TMeta(type(o.Module)):

	# When types are defined with class extending o.Schema,
	# override instantiation to produce correct class to enable
	# my_class_instance is o.T.MyClass
	# ----------------------------------------------------------------------
	def __call__(cls, *args, **kwargs):
		runtime_cls = o.types.get(cls.__name__)
		if runtime_cls is not None and runtime_cls is not cls:
			return runtime_cls(*args, **kwargs)
		return super().__call__(*args, **kwargs)

	# Instance existence check short-hand
	# ----------------------------------------------------------------------
	def __contains__(cls, id_or_key):
		return cls.has(id_or_key)

	# ----------------------------------------------------------------------
	def __setattr__(cls, name, value):
		if isinstance(value, T):
			key = String(name)
			Disk.link(ROOT_REF, key.ref, value.ref)
		else:
			super().__setattr__(name, value)

	# ----------------------------------------------------------------------
	def __getattr__(cls, name):
		key = String(name)
		ref = Disk.find_edge(ROOT_REF, key.ref)
		if ref is None:
			raise AttributeError(name)
		return load(ref)

	# ----------------------------------------------------------------------
	def __delattr__(cls, name):
		key = String(name)
		Disk.unlink(ROOT_REF, key.ref)

	# ----------------------------------------------------------------------
	def __contains__(cls, name):
		key = String(name)
		return Disk.find_edge(ROOT_REF, key.ref) is not None

	# ----------------------------------------------------------------------
	def __iter__(cls):
		for key_ref in Disk.iter_keys(ROOT_REF):
			yield key_ref


# ================================================================================
#                                    CLASS T
# ================================================================================


class T(o.Module, metaclass=TMeta):
	
	# Initialize schema
	# ----------------------------------------------------------------------
	def __init__(self, **data):
		self.fields = {}
		for fname, field in self.__class__.__fields__.items():
			self.fields[fname] = field.create(data.get(fname, o.undefined))

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	def write(self):
		pass

	def read(self):
		pass

	@classmethod
	def from_python_type(cls, python_type):
		t = o.Type(python_type).to_non_optional().get_origin().annotation
		return dict(
			int   = o.T.Int,
			str   = o.T.String,
			float = o.T.Float,
			bool  = o.T.Bool,
		).get(t, t)

	@classmethod
	def define(cls, type_name, **fields):

		# Process fields
		# - - - - - - - - - - - - - - - - - - - -
		__fields__ = {}

		for fname, f in fields.items():
			if not isinstance(f, o.F):
				raise TypeError(f'Field `{fname}` must be o.F()')
			f.name = fname
			__fields__[fname] = f

		# Create new schema class
		# - - - - - - - - - - - - - - - - - - - -
		new_class = type(
			type_name,
			(cls,),
			{
				'__fields__'   : __fields__,
				'__o_module__' : f'o.T.{type_name}'
			}
		)
		return new_class


class TAtom(T):
	
	# Initialize schema
	# ----------------------------------------------------------------------
	def __init__(self, **data):
		self.fields = {}
		for fname, field in self.__class__.__fields__.items():
			self.fields[fname] = field.create(data.get(fname, o.undefined))

class TMolecule(T):
	
	# Initialize schema
	# ----------------------------------------------------------------------
	def __init__(self, **data):
		self.fields = {}
		for fname, field in self.__class__.__fields__.items():
			self.fields[fname] = field.create(data.get(fname, o.undefined))

	