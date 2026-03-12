import types
import typing as t

import o


class Annotation(o.Module):

	def __init__(self, annotation):
		super().__init__()

		if isinstance(annotation, Annotation):
			annotation = annotation.annotation

		self.annotation      = annotation
		self.origin          = t.get_origin(annotation) or annotation
		self.is_none         = annotation in (None, type(None))
		self.options         = self._get_options()
		self.is_union        = bool(self.options)
		self.is_optional     = any(option.is_none for option in self.options)
		self.is_list         = self.origin is list
		self.is_dict         = self.origin is dict
		self.is_set          = self.origin is set
		self.is_tuple        = self.origin is tuple
		self.is_atomic       = self.origin not in (list, dict, set, tuple)
		self.key, self.value = self._get_key_value()
		self.is_homogenous   = self._get_is_homogenous()
		self.id              = self._get_id()

		self._validate()

	# ----------------------------------------------------------------------

	def __repr__ (self): return self.id
	def __str__  (self): return self.id
	def __hash__ (self): return hash(self.id)
	def __eq__   (self, other):
		return self.id == other.id if isinstance(other, Annotation) else False

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Get union options
	# ----------------------------------------------------------------------
	def _get_options(self):
		options    = set()
		origin     = t.get_origin(self.annotation)
		union_type = getattr(types, 'UnionType', None)

		if origin in (t.Union, union_type):
			for arg in t.get_args(self.annotation):
				option = Annotation(arg)

				if option.is_union:
					for nested in option.options:
						options.add(nested)
				else:
					options.add(option)

		return options

	# Get key, value annotations
	# ----------------------------------------------------------------------
	def _get_key_value(self):
		key   = None
		value = None
		args  = t.get_args(self.annotation)

		if self.is_list:
			if len(args) not in (0, 1):
				raise TypeError(f'Invalid list annotation: `{self.annotation}`')

			key = Annotation(int)
			if len(args) == 1:
				value = Annotation(args[0])

		elif self.is_dict:
			if len(args) not in (0, 2):
				raise TypeError(f'Invalid dict annotation: `{self.annotation}`')

			if len(args) == 2:
				key   = Annotation(args[0])
				value = Annotation(args[1])

		return key, value

	# Get homogenous flag
	# ----------------------------------------------------------------------
	def _get_is_homogenous(self):
		h = True

		if   self.is_union                                           : h = False
		elif self.key   is not None and not self.key.is_homogenous   : h = False
		elif self.value is not None and not self.value.is_homogenous : h = False

		return h

	# Get canonical annotation id
	# ----------------------------------------------------------------------
	def _get_id(self):
		id = None

		if self.is_none:
			id = 'None'
		elif self.is_union:
			id = ' | '.join(sorted([option.id for option in self.options]))
		elif self.is_list:
			id = 'list' if self.value is None else f'list[{self.value.id}]'
		elif self.is_dict:
			id = 'dict' if self.key is None else f'dict[{self.key.id}, {self.value.id}]'
		else:
			id = self._get_origin_name()

		return id
	# Get readable origin name
	# ----------------------------------------------------------------------
	def _get_origin_name(self):
		name = None

		if self.origin is None                : name = 'None'
		elif hasattr(self.origin, '__name__') : name = self.origin.__name__
		else                                  : name = str(self.origin)

		return name

	# Validate tree invariants
	# ----------------------------------------------------------------------
	def _validate(self):
		for option in self.options:
			if not isinstance(option, Annotation):
				raise TypeError(f'Option must be `Annotation`, got `{type(option)}`')

		if self.key is not None and not isinstance(self.key, Annotation):
			raise TypeError(f'Key must be `Annotation`, got `{type(self.key)}`')

		if self.value is not None and not isinstance(self.value, Annotation):
			raise TypeError(f'Value must be `Annotation`, got `{type(self.value)}`')

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Derive value annotation
	# ----------------------------------------------------------------------
	@classmethod
	def annotate(cls, value):

		def join(items):
			joined      = None
			annotations = sorted({cls.annotate(item).annotation for item in items}, key=repr)
			for annotation in annotations:
				joined = annotation if joined is None else joined | annotation
			return joined

		annotation = None

		if isinstance(value, cls):
			annotation = value.annotation
		elif value is None:
			annotation = None
		elif isinstance(value, list):
			annotation = list if len(value) == 0 else list[join(value)]
		elif isinstance(value, dict):
			annotation = dict if len(value) == 0 else dict[
				join(value.keys()),
				join(value.values()),
			]
		else:
			annotation = type(value)

		return cls(annotation)
