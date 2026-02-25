import typing as t

import o


class Type(o.Module):

	# Initialization
	# ----------------------------------------------------------------------
	def __init__(self, annotation):
		if not isinstance(annotation, type) and t.get_origin(annotation) is None:
			annotation = type(annotation)
		self.annotation = annotation

	# Representation
	# ----------------------------------------------------------------------
	def __repr__(self):
		return f'<{self.__o_module__} \'{self.annotation.__name__}\'>'

	# Get annotation origin
	# ----------------------------------------------------------------------
	def get_origin(self):
		origin = t.get_origin(self.annotation)
		if origin is None:
			origin = self.annotation
		return origin

	# Get annotation args
	# ----------------------------------------------------------------------
	def get_args(self):
		return t.get_args(self.annotation)

	# Is annotation union
	# ----------------------------------------------------------------------
	def is_union(self):
		origin = self.get_origin()
		return (
			origin is t.Union or
			(hasattr(t, 'UnionType') and origin is t.UnionType)
		)

	# Is origin a list
	# ----------------------------------------------------------------------
	def is_list(self):
		return self.get_origin() in (list, t.List)

	# Is origin a dict
	# ----------------------------------------------------------------------
	def is_dict(self):
		return self.get_origin() in (dict, t.Dict)

	# Is type a dict with args
	# ----------------------------------------------------------------------
	def is_nested_dict(self):
		args = self.get_args()
		return self.is_dict() and len(args) == 2 and args[0] is str

	# Is type a list with args
	# ----------------------------------------------------------------------
	def is_nested_list(self):
		args = self.get_args()
		return self.is_list() and len(args) == 1

	# Is annotation optional
	# ----------------------------------------------------------------------
	def is_optional(self):
		return self.is_union() and type(None) in self.get_args()

	# Is Annotated
	# ----------------------------------------------------------------------
	def is_annotated(self):
		tp = self.to_non_optional()
		return tp.get_origin() is t.Annotated

	# Atomic — int, str, float, bool, complex
	# ----------------------------------------------------------------------
	def is_atomic(self):
		tp = self.to_non_optional()
		return tp.annotation in (int, str, float, bool, complex)

	# Checks whether a type is a list of atomic values
	# ----------------------------------------------------------------------
	def is_atomic_list(self):
		tp   = self.to_non_optional()
		args = tp.get_args()
		return tp.is_nested_list() and Type(args[0]).is_atomic()

	# Checks whether a type is a dict[str, atomic]
	# ----------------------------------------------------------------------
	def is_atomic_dict(self):
		tp     = self.to_non_optional()
		args   = tp.get_args()
		return tp.is_nested_dict() and Type(args[1]).is_atomic()

	# Checks whether a type is a subclass of cls
	# ----------------------------------------------------------------------
	def is_subclass(self, cls):
		annotation = self.to_non_optional().annotation
		return isinstance(annotation, type) and issubclass(annotation, cls)

	# Checks whether a type contains subclass of cls type wrapped inside
	# ----------------------------------------------------------------------
	def contains_subclass(self, cls):
		return self.unravel_subclass(cls) is None

	# Checks whether a type represents a nested subclass of cls and returns it
	# ----------------------------------------------------------------------
	def unravel_subclass(self, cls):
		tp   = self.to_non_optional()
		args = tp.get_args()

		if tp.is_subclass(cls)                                    : return tp
		if tp.is_nested_list() and Type(args[0]).is_subclass(cls) : return Type(args[0])
		if tp.is_nested_dict() and Type(args[1]).is_subclass(cls) : return Type(args[1])

		return None

	# Wraps type into optional 
	# ----------------------------------------------------------------------
	def to_optional(self):
		annotation = self.annotation
		if not self.is_optional():
			annotation = t.Optional[self.annotation]
		return Type(annotation)

	# Unwraps type from optional
	# ----------------------------------------------------------------------
	def to_non_optional(self):
		annotation = self.annotation
		origin     = self.get_origin()

		if self.is_union():
			args = [a for a in self.get_args() if a is not type(None)]
			if len(args) == 1:
				annotation = Type(args[0]).to_non_optional().annotation

		elif origin is list:
			args = self.get_args()
			annotation = list[
				Type(args[0]).to_non_optional().annotation
			]

		elif origin is dict:
			args = self.get_args()
			annotation = dict[
				Type(args[0]).to_non_optional().annotation,
				Type(args[1]).to_non_optional().annotation
			]

		return Type(annotation)

	# Wraps type into optional 
	# ----------------------------------------------------------------------
	def to_string(self):
		return self.annotation.__name__

