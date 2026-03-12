import typing as t

import o


class Type(o.Module):
	id_to_words = {}
	words_to_id = {}

	def __init__(self, annotation):

		# Another V object
		# - - - - - - - - - - - - - - - - - - - -
		if isinstance(annotation, Type):
			self.annotation = annotation.annotation
			self.signature  = annotation.signature

		# Type annotation
		# - - - - - - - - - - - - - - - - - - - -
		elif isinstance(annotation, type) or t.get_origin(annotation) is not None:
			self.annotation = annotation
			self.signature  = self._sign(annotation)

		# Python value
		# - - - - - - - - - - - - - - - - - - - -
		else:
			v = self.annotate(annotation)
			self.signature  = v.signature
			self.annotation = v.annotation

	# Validation: (A in B) ==> (A is a valid B)
	# ----------------------------------------------------------------------
	def __contains__(self, v):
		return v.signature.startswith(self.signature)

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Cache word to class indices under base64 id, return id
	# ----------------------------------------------------------------------
	def _encode(self, word):
		if word not in self.words_to_id:
			new_id = o.services.Base64.encode(len(self.words_to_id), digits=3)
			self.words_to_id[word] = new_id
			self.id_to_words[new_id] = word
		return self.words_to_id[word]

	# Annotation -> signature
	# ----------------------------------------------------------------------
	def _sign(self, annotation, level=0, levels=None):
		origin     = t.get_origin(annotation) or annotation
		name       = origin.__name__
		args       = t.get_args(annotation)
		len_args   = len(args)
		levels     = [[]] if levels is None else levels

		# Enforce homogenous annotation
		# - - - - - - - - - - - - - - - - - - - -
		if origin == dict and len_args not in (0, 2):
			raise TypeError(f'Wrong argument number in `{annotation}`, expected 0 or 2, got {len_args}')
		if origin in (list, tuple, set) and len_args > 1:
			raise TypeError(f'Wrong argument number in `{annotation}`, expeccted 0 or 1 got {len_args}')

		self._encode(name)
		levels[level].append(name)

		if len_args > 0:
			levels += [[]]
			for arg in args:
				self._sign(arg, level+1, levels)

		if level == 0:
			signature = ''
			for level in levels:
				if level:
					signature += self._encode(','.join(level))
			return signature
		return None

	# ======================================================================
	# PUBLIC CLASS METHODS
	# ======================================================================

	# Python object -> annotation
	# ----------------------------------------------------------------------
	@classmethod
	def annotate(cls, value):
		tp = None

		# Type annotation
		# - - - - - - - - - - - - - - - - - - - -
		if isinstance(value, Type):
			tp = value

		# Generic Alias
		# - - - - - - - - - - - - - - - - - - - -
		elif isinstance(value, (type, t.GenericAlias)) or t.get_origin(value) is not None:
			tp = Type(value)

		# Dict
		# - - - - - - - - - - - - - - - - - - - -
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
						if kt.signature != kt_best.signature:
							raise TypeError(f'Dict keys are not homogenous in `{value}`')
						if vt.signature != vt_best.signature:
							raise TypeError(f'Dict values are not homogenous in `{value}`')

				tp = Type(dict[kt_best.annotation, vt_best.annotation])

		# List
		# - - - - - - - - - - - - - - - - - - - -
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
						if vt.signature != vt_best.signature:
							raise TypeError(f'List is not homogenous in `{value}`')

				tp = Type(list[vt_best.annotation])

		# Atomic value
		# - - - - - - - - - - - - - - - - - - - -
		elif isinstance(value, (int, str, float, bool, complex)):
			tp = Type(type(value))

		# o.T
		# - - - - - - - - - - - - - - - - - - - -
		elif isinstance(value, o.T):
			tp = Type(type(value))

		# None
		# - - - - - - - - - - - - - - - - - - - -
		elif value is None:
			tp = Type(type(None))

		# All else – UNSUPPORTED
		# - - - - - - - - - - - - - - - - - - - -
		else:
			raise TypeError(f'Unsupported type: `{type(value)}`')

		return tp

	# ======================================================================
	# PUBLIC INSTANCE METHODS
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