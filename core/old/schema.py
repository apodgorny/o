import json
from typing import Any

import o


# ======================================================================
# CLASS Schema
# ======================================================================

class SchemaMeta(type(o.Module)):

	# When types are defined with class extending o.Schema,
	# override instantiation to produce correct class to enable
	# my_class_instance is o.types.MyClass
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

class Schema(o.BaseSchema, metaclass=SchemaMeta):

	# Initialize schema
	# ----------------------------------------------------------------------
	def __init__(self, **data):
		self._id         = data.pop('id',  None)
		self._key        = data.pop('key', None)
		self._is_unsaved = self._id is None

		# Normalize input – reference all o.Schema
		# - - - - - - - - - - - - - - - - - - - -
		for k, v in list(data.items()):
			if isinstance(v, o.Schema):
				data[k] = o.Ref.reference(v, persistent=False)

		super().__init__(**data)

		# Add self to caches
		# - - - - - - - - - - - - - - - - - - - -
		if self._id is not None:
			o.__cache_by_id__[self.__class__.__name__][self._id] = self

		if self._key is not None:
			o.__cache_by_key__[self.__class__.__name__][self._key] = self

		o.__cache_by_instance_id__ [self.__class__.__name__][self.__instance_id__] = self

	# Accessor overrides to allow lazy loading of nested models
	# ----------------------------------------------------------------------
	def __set_model_attr__(self, key, value):
		if isinstance(value, o.Schema):
			value = o.Ref.reference(value, persistent=False)
		# self._is_unsaved = True
		object.__setattr__(self, '_is_unsaved', True)
		return super().__set_model_attr__(key, value)

	def __get_model_attr__(self, key):
		value = super().__get_model_attr__(key)
		if o.Ref.is_reference(value):
			return o.Ref.dereference(value)
		return value

	# Instance loading short-hand (class-level [])
	# ----------------------------------------------------------------------
	@classmethod
	def __class_getitem__(cls, id_or_key):
		return cls.load(id_or_key)
		
	# String representation
	# ----------------------------------------------------------------------
	def __repr__(self):
		return f'<{self.__o_module__} id={self._id}>'

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Getters
	# ----------------------------------------------------------------------
	@property
	def id(self) : return self._id

	@property
	def key(self) : return self._key

	@property
	def is_saved(self) : return not self._is_unsaved

	@o.dual_property
	def table_name(cls, self):
		return o.String.to_snake_case(cls.__name__)

	# Define – overriding base method to cache returned class
	# ----------------------------------------------------------------------
	@classmethod
	def define(cls, schema_name, **fields):
		new_class = super(o.Schema, cls).define(schema_name, **fields)
		o.types[schema_name] = new_class
		return new_class

	# Has record with key or id?
	# ----------------------------------------------------------------------
	@classmethod
	def has(cls, id_or_key):
		return o.Db.has(cls.table_name, id_or_key)

	# Load
	# ----------------------------------------------------------------------
	@classmethod
	def load(cls, id_or_key):
		obj        = None
		from_cache = True

		# Load from cache
		# - - - - - - - - - - - - - - - - - - - -
		cache = o.__cache_by_key__ if isinstance(id_or_key, str) else o.__cache_by_id__
		obj   = cache[cls.__name__].get(id_or_key, None)

		# Load from db once per object's lifetime
		# - - - - - - - - - - - - - - - - - - - -
		if obj is None:
			from_cache = False
			row        = o.Db.get(cls.table_name, id_or_key)

			if row is not None:
				data = {}

				# Deserialize custom types
				# - - - - - - - - - - - - - - - - - - - -
				for k, v in  dict(row).items():
					t = self.get_type(k)
					if t.is_subclass(o.CustomType):
						v = t.unravel_subclass(o.CustomType).deserialize(v)
					data[k] = v

				obj = cls(** data)
			
		# If both, cache and db, failed
		# - - - - - - - - - - - - - - - - - - - -
		if obj is None:
			raise RuntimeError(f'Failed loading `{cls.__name__}`({id_or_key})')

		obj.on_load(from_cache)
		return obj

	# Save
	# ----------------------------------------------------------------------
	def save(self):
		data = {}

		o.Db.create_table(self.table_name, self.get_definition())

		# Save leafs first
		# - - - - - - - - - - - - - - - - - - - -
		for k, v in self:
			if isinstance(v, o.Schema):
				v.save()

		if self._is_unsaved:

			# Compile data to save
			# - - - - - - - - - - - - - - - - - - - -
			for k, v in self:
				t = self.get_type(k)
				if t.is_subclass(o.Schema):
					data[k] = o.Ref.reference(v, persistent=True)
				if t.is_subclass(o.CustomType):
					data[k] = t.unravel_subclass(o.CustomType).deserialize(v)
				else:
					data[k] = v

			# Save to db
			# - - - - - - - - - - - - - - - - - - - -
			self._id = o.Db.set(
				self.table_name,
				id  = self._id,
				key = self._key,
				** data
			)

			o.__cache_by_id__[self.__class__.__name__][self._id] = self

		self.on_save()
		return self

	# Delete
	# ----------------------------------------------------------------------
	def delete(self):
		if self._id is not None:
			rowcount = o.Db.delete(self.table_name, self._id)

			# Remove self from caches
			# - - - - - - - - - - - - - - - - - - - -
			if self._id in o.__cache_by_id__[self.__class__.__name__]:
				del o.__cache_by_id__[self.__class__.__name__][self._id]

			if self.__instance_id__ in o.__cache_by_instance_id__[self.__class__.__name__]:
				del o.__cache_by_instance_id__ [self.__class__.__name__][self.__instance_id__]

			if self._key is not None and self._key in o.__cache_by_key__[self.__class__.__name__]:
				del o.__cache_by_key__[self.__class__.__name__][self._key]

			# Make unsaved
			# - - - - - - - - - - - - - - - - - - - -
			self._id         = None
			self._is_unsaved = True

			self.on_delete(rowcount)
			return rowcount > 0



	# Event hooks
	# ----------------------------------------------------------------------
	def on_load   (self, from_cache) : pass
	def on_save   (self)             : pass
	def on_delete (self, rowcount)   : pass
