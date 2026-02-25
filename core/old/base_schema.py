# ======================================================================
# o.BaseSchema — minimal structural + validation schema
# ======================================================================

import json, yaml

from pydantic      import BaseModel, ValidationError, ConfigDict, Field, create_model
from pydantic_core import PydanticUndefined

import o


FIELD_INFO_KEYS = o.pydantic.FieldInfoKeys()


# ======================================================================
# CLASS BaseSchema
# ======================================================================

class BaseSchema(o.Module):
	model_class = None

	def __init__(self, **data):
		self.model = self.model_class(**data)

	# Allow class definitions of types in addition to cls.define()
	# ----------------------------------------------------------------------
	def __init_subclass__(cls, **kwargs):
		super().__init_subclass__(**kwargs)

		fields = {
			k: v for k, v in cls.__dict__.items()
			if isinstance(v, o.F)
		}

		if fields:
			defined          = cls.define(cls.__name__, **fields)
			cls.model_class  = defined.model_class
			cls.__o_module__ = defined.__o_module__

			for k in fields: delattr(cls, k)  # Cleanup

	# Field access
	# ----------------------------------------------------------------------

	def __get_model__(self):
		if 'model' in self.__dict__:
			return object.__getattribute__(self, 'model')
		return None

	def __set_model_attr__(self, key, value):
		model = self.__get_model__()
		if model is not None and key in model.model_fields:
			setattr(model, key, value)
			return True
		return False

	def __get_model_attr__(self, key):
		model = self.__get_model__()
		if model is not None and key in model.model_fields:
			return getattr(model, key)
		return o.undefined

	def __getitem__(self, key):
		result = self.__get_model_attr__(key)
		if result is o.undefined:
			raise KeyError(key)
		return result

	def __setitem__(self, key, value):
		if not self.__set_model_attr__(key, value):
			raise KeyError(key)

	def __getattr__(self, key):
		result = self.__get_model_attr__(key)
		if result is o.undefined:
			raise AttributeError(key)
		return result

	def __setattr__(self, key, value):
		if key in ['model', 'model_class'] or key in self.__dict__:
			object.__setattr__(self, key, value)
		else:
			if not self.__set_model_attr__(key, value):
				object.__setattr__(self, key, value)
		return None

	# Iteration over the model
	# ----------------------------------------------------------------------
	def __iter__(self):
		for field_name in self.fields.keys():
			yield field_name, getattr(self, field_name)

	# String
	# ----------------------------------------------------------------------
	def __str__(self):
		return o.pydantic.Transform.to_string(self.model)

	# ======================================================================
	# PUBLIC CLASS METHODS
	# ======================================================================

	# Define schema and create BaseModel
	# ------------------------------------------------------------------
	@classmethod
	def define(cls, schema_name, **fields):
		model_fields = {}

		# Process fields
		# - - - - - - - - - - - - - - - - - - - -
		for fname, f in fields.items():
			if not isinstance(f, o.F):
				raise TypeError(f'Field `{fname}` must be o.F()')

			t       = o.Type(str | None) if f.type.is_subclass(BaseSchema) else f.type
			default = None if f.default is o.undefined else f.default

			field = Field(
				default     = default,
				description = f.description
			)
			model_fields[fname] = (t.annotation, field)

		# Define pydantic configuration
		# - - - - - - - - - - - - - - - - - - - -
		config = ConfigDict(
			extra           = 'forbid',  # Raise if mistyped or unknown fields are present
			strict          = True,      # Automatically coerse values into defined types
			from_attributes = True       # Allow model creation from objects, not just dict
		)

		# Create pydantic model
		# - - - - - - - - - - - - - - - - - - - -
		model_class = create_model(
			schema_name,
			__base__   = BaseModel,
			__config__ = config,
			** model_fields,
		)

		# Return subclass
		# - - - - - - - - - - - - - - - - - - - -
		new_class = type(schema_name, (cls,), { 'model_class': model_class })
		new_class.__o_module__ = f'o.{schema_name}'

		return new_class

	# ======================================================================
	# PUBLIC PROPERTIES
	# ======================================================================

	# Get field list
	# ----------------------------------------------------------------------
	@o.dual_property
	def fields(cls, self) -> dict:
		return cls.model_class.model_fields

	# ======================================================================
	# PUBLIC INSTANCE METHODS
	# ======================================================================

	# Check if field exists
	# ----------------------------------------------------------------------
	def has_field(self, field_name) -> bool:
		return field_name in self.fields

	# Get field type
	# ----------------------------------------------------------------------
	@o.dual_method
	def get_type(self, field_name, remove_optional=True) -> bool:
		field = self.fields[field_name]  # Key error if not present
		t = o.Type(field.annotation)
		return t.to_non_optional() if remove_optional else t

	# Get field default
	# ----------------------------------------------------------------------
	def get_default(self, field_name) -> bool:
		field = self.fields[field_name]  # Key error if not present
		return field.default

	# Get field default
	# ----------------------------------------------------------------------
	def get_description(self, field_name: str) -> str:
		field = self.fields[field_name]
		return field.description or ''

	# Is field optional (has default of any kind)
	# ----------------------------------------------------------------------
	def is_optional(self, field_name):
		return self.get_default(field_name) is not PydanticUndefined

	# Is field nullable (NULL allowed)
	# ----------------------------------------------------------------------
	def is_nullable(self, field_name):
		return self.get_default(field_name) is None

	# Create jsonschema with references resolved
	# ----------------------------------------------------------------------
	def to_jsonschema(self) -> dict:
		return o.pydantic.Transform.to_dereferenced_jsonschema(self.model)

	# Create instance with default values
	# ----------------------------------------------------------------------
	def to_default(self):
		field_values = {}

		for k, f in self.fields.items():
			if f.default != PydanticUndefined:
				field_values[k] = f.default
			else:
				field_values[k] = ''

		return self.model(**field_values)

	# Produce a human-readable bullet list for fields (minus except_keys)
	# ----------------------------------------------------------------------
	def describe(self, except_keys=None):
		except_keys = set(except_keys or [])
		lines       = []
		fields      = [k for k in self.fields if k not in except_keys]

		for i, k in enumerate(fields):
			field  = self.fields[k]
			label  = k
			descr  = (field.description or '').rstrip('.')
			prefix = '-' if i == 0 else '\t-'

			lines.append(f'{prefix} {label}: {descr}')
		return '\n'.join(lines)

	# Definition info 
	# ----------------------------------------------------------------------
	def get_definition(self):
		definition = []
		for name in self.fields:
			if name not in ('id', 'key'):
				definition.append(dict(
					name     = name,
					type     = self.get_type(name),
					default  = self.get_default(name),
					nullable = self.is_nullable(name),
					optional = self.is_optional(name)
				))
		return definition

	# Transformations
	# ----------------------------------------------------------------------
	def to_pydantic(self) -> type:
		return self.__class__.model_class

	def to_dict(self, recursive=False, show_empty=False) -> dict:
		return o.pydantic.Transform.to_data(self.model, recursive, show_empty)

	def to_json(self, recursive=False) -> str:
		data = self.to_dict(recursive, True)
		return json.dumps(data, indent=4, ensure_ascii=False)

	def to_yaml(self, recursive=False, show_empty=False) -> str:
		data = self.to_dict(recursive, show_empty)
		return yaml.dump(data, allow_unicode=True, sort_keys=False)

	def clone(self):
		return self.__class__(** self.to_dict())

	# Utility method to hold function arguments
	# ----------------------------------------------------------------------
	def unpack(self):
		args = tuple(self[k] for k in self.fields.keys())
		return args[0] if len(args) == 1 else args

	# Walk
	# ----------------------------------------------------------------------
	def walk(self, fn, val=None):
		if val is None:
			out = {}
			for k, v in self:
				out[k] = self.walk(fn, v)
		else:
			if isinstance(val, BaseSchema):
				res = fn(val)
				out = val if res is None else res
			elif isinstance(val, list):
				out = []
				for v in val:
					out.append(self.walk(fn, v))
			elif isinstance(val, dict):
				out = {}
				for k, v in val.items():
					out[k] = self.walk(fn, v)
			else:
				out = val
		return out

