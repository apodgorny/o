import typing as t

import o


class Type(o.Module):

	# Initialization
	# ----------------------------------------------------------------------
	def __init__(self, annotation):
		if isinstance(annotation, Type):
			self.annotation = annotation.annotation
		elif isinstance(annotation, (type, t.GenericAlias)) or t.get_origin(annotation) is not None:
			self.annotation = annotation
		else:
			self.annotation = Type.annotate(annotation).annotation

		self._nesting = None

	# Representation
	# ----------------------------------------------------------------------
	def __repr__(self):
		return f'<{self.__o_module__} \'{self.annotation.__name__}\'>'

	# ======================================================================
	# CLASS METHODS
	# ======================================================================

	@classmethod
	def is_same_origin(cls, a, b):
		a = Type(a).get_outer()
		b = Type(b).get_outer()
		return a.annotation == b.annotation

	@classmethod
	def get_deepest(cls, a, b):
		a, b = Type(a), Type(b)
		if a.get_nesting() < b.get_nesting():
			return b
		return a

	@classmethod
	def annotate(cls, value):
		tp = None

		if isinstance(value, Type):
			tp = value

		elif isinstance(value, (type, t.GenericAlias)) or t.get_origin(value) is not None:
			tp = Type(value)

		elif isinstance(value, dict):
			if not value:
				tp = Type(dict)
			else:
				is_first = True
				for k, v in value.items():
					kt = cls.annotate(k)
					vt = cls.annotate(v)

					if is_first:
						kt_best  = Type(kt)
						vt_best  = Type(vt)
						is_first = False
					else:
						kt_best = Type.get_deepest(kt_best, kt)
						vt_best = Type.get_deepest(vt_best, vt)

					if not Type.is_same_origin(kt, type(k)) or not Type.is_same_origin(vt, type(v)):
						raise TypeError('Dict is not homogenous')

				tp = Type(dict[kt_best.annotation, vt_best.annotation])

		elif isinstance(value, list):
			if not value:
				tp = Type(list)
			else:
				is_first = True
				for v in value:
					vt = cls.annotate(v)
					if is_first:
						vt_best  = Type(vt)
						is_first = False
					else:
						vt_best = Type.get_deepest(vt_best, vt)

					if not Type.is_same_origin(vt, type(v)):
						raise TypeError('List is not homogenous')

				tp = Type(list[vt_best.annotation])

		elif isinstance(value, (int, str, float, bool, complex)):
			tp = Type(type(value))
		else:
			raise TypeError('Unsupported type')

		return tp

	# ======================================================================
	# GET METHODS
	# ======================================================================

	# Get outer type
	# ----------------------------------------------------------------------
	def get_outer(self):
		outer = t.get_origin(self.annotation)
		if outer is None:
			outer = self.annotation
		outer = Type(outer)
		return outer

	# Get inner type
	# ----------------------------------------------------------------------
	def get_inner(self):
		tp = self.to_non_optional()

		while True:
			args = tp.get_args()
			if tp.is_nested_list() and len(args) == 1:
				tp = Type(args[0]).to_non_optional()
			elif tp.is_nested_dict() and len(args) == 2:
				tp = Type(args[1]).to_non_optional()
			else:
				break

		return tp

	# Get annotation args
	# ----------------------------------------------------------------------
	def get_args(self):
		return t.get_args(self.annotation)

	# Checks whether annotation contains nested container deeper than 1 level
	# ----------------------------------------------------------------------
	def get_nesting(self):
		if self._nesting is None:
			tp    = self.to_non_optional()
			depth = 0

			if tp.is_nested_list():
				args = tp.get_args()
				if len(args) != 1:
					depth = 2
				else:
					inner = Type(args[0]).to_non_optional()
					if inner.is_list() or inner.is_dict():
						depth = 2
					else:
						depth = 1 + inner.get_nesting()

			elif tp.is_nested_dict():
				args = tp.get_args()
				if len(args) != 2:
					depth = 2
				else:
					key = Type(args[0]).to_non_optional()
					val = Type(args[1]).to_non_optional()
					if val.is_list() or val.is_dict():
						depth = 2
					else:
						depth = 1 + max(key.get_nesting(), val.get_nesting())
			self._nesting = depth

		return self._nesting

	# ======================================================================
	# IS METHODS
	# ======================================================================

	# Is annotation union
	# ----------------------------------------------------------------------
	def is_union(self):
		origin = self.get_outer().annotation
		return (
			origin is t.Union or
			(hasattr(t, 'UnionType') and origin is t.UnionType)
		)

	# Is origin a list
	# ----------------------------------------------------------------------
	def is_list(self):
		return self.get_outer().annotation in (list, t.List)

	# Is origin a dict
	# ----------------------------------------------------------------------
	def is_dict(self):
		return self.get_outer().annotation in (dict, t.Dict)

	# Is type a dict with args
	# ----------------------------------------------------------------------
	def is_nested_dict(self):
		args = self.get_args()
		return self.is_dict() and len(args) == 2

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
		return tp.get_outer().annotation is t.Annotated

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
	def is_inner_subclass(self, cls):
		return self.get_inner().is_subclass(cls)

	# Validates runtime value against this type
	# ----------------------------------------------------------------------
	def validate_value(self, value, field_name='value'):
		tp = self.to_non_optional()

		if tp.get_nesting() > 1:
			raise TypeError(f'Field `{field_name}` does not support deep nesting.')

		expected = tp.annotation if tp.is_subclass(o.T) else tp.get_outer().annotation
		if not isinstance(value, expected):
			raise TypeError(
				f'Field `{field_name}`: expected `{expected.__name__}`, got `{value.__class__.__name__}`.'
			)

		if tp.is_nested_list():
			args = tp.get_args()
			inner = Type(args[0]).to_non_optional()
			inner_expected = inner.annotation if inner.is_subclass(o.T) else inner.get_outer().annotation
			if not all(isinstance(v, inner_expected) for v in value):
				raise TypeError(f'Field `{field_name}` invalid list value.')

		elif tp.is_nested_dict():
			args = tp.get_args()
			key_tp = Type(args[0]).to_non_optional()
			val_tp = Type(args[1]).to_non_optional()

			if not key_tp.is_atomic():
				raise TypeError(f'Field `{field_name}` dict keys must be atomic.')

			key_expected = key_tp.get_outer().annotation
			val_expected = val_tp.annotation if val_tp.is_subclass(o.T) else val_tp.get_outer().annotation

			if not all(isinstance(k, key_expected) for k in value):
				raise TypeError(f'Field `{field_name}` invalid dict key type.')
			if not all(isinstance(v, val_expected) for v in value.values()):
				raise TypeError(f'Field `{field_name}` invalid dict value type.')

		return value

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
		origin     = self.get_outer().annotation

		if self.is_union():
			args = [a for a in self.get_args() if a is not type(None)]
			if len(args) == 1:
				annotation = Type(args[0]).to_non_optional().annotation

		elif origin is list:
			args = self.get_args()
			if len(args) == 1:
				annotation = list[
					Type(args[0]).to_non_optional().annotation
				]
			else:
				annotation = list

		elif origin is dict:
			args = self.get_args()
			if len(args) == 2:
				annotation = dict[
					Type(args[0]).to_non_optional().annotation,
					Type(args[1]).to_non_optional().annotation
				]
			else:
				annotation = dict

		return Type(annotation)

	# Wraps type into optional 
	# ----------------------------------------------------------------------
	def to_string(self):
		return self.annotation.__name__
