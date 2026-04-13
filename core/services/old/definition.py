import os, json, struct

import o



class Definition(o.Service):

	def initialize(self):
		self.dir        = o.db.definitions
		self.count_word = struct.Struct('<I')

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Return path for type definition file
	# ----------------------------------------------------------------------
	def _get_path(self, type_id):
		return os.path.join(self.dir.path, str(type_id))

	# Read raw json spec from definition file
	# ----------------------------------------------------------------------
	def _read_definition(self, type_id):
		path = self._get_path(type_id)

		with open(path, 'rb') as f:
			f.seek(self.count_word.size)
			raw_json = f.read()

		return json.loads(raw_json.decode('utf-8'))

	# Write json spec preserving current instance count
	# ----------------------------------------------------------------------
	def _write_definition(self, type_id, spec):
		path = self._get_path(type_id)
		data = json.dumps(spec, ensure_ascii=False).encode('utf-8')

		if os.path.exists(path):
			with open(path, 'r+b') as f:
				f.seek(self.count_word.size)
				f.truncate()
				f.write(data)
		else:
			with open(path, 'wb') as f:
				f.write(self.count_word.pack(0))
				f.write(data)

	# Deserialize field spec into `o.F`
	# ----------------------------------------------------------------------
	def _deserialize_field(self, spec):
		default = spec['default']
		if default == '__undefined__':
			default = o.undefined

		return o.F(
			name        = spec['name'],
			type        = eval(spec['type']),
			description = spec['description'],
			default     = default,
			is_optional = spec['is_optional'],
		)

	# Recreate type from persisted spec
	# ----------------------------------------------------------------------
	def _define_from_spec(self, spec):
		type_name   = spec['type_name']
		o_module    = spec['o_module']
		field_specs = spec['fields']
		annotation  = spec['annotation']
		type_cls    = None

		if field_specs:
			fields = {}

			for field_spec in field_specs:
				field = self._deserialize_field(field_spec)
				fields[field.name] = field

			type_cls = o.T.define(type_name, **fields)
		elif annotation:
			type_cls = o.T.define(
				type_name,
				eval(annotation)
			)
		else:
			type_cls = o[o_module]

		return type_cls

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Persist type definition, creating or updating definition file
	# ----------------------------------------------------------------------
	def define(self, cls):
		self._write_definition(cls.__type_id__, cls.serialize())
		return cls

	# Remove type definition from memory and disk
	# ----------------------------------------------------------------------
	def undefine(self, type_id):
		path = self._get_path(type_id)

		if os.path.exists(path):
			os.remove(path)

	# Get type by id, loading it from definition file if needed
	# ----------------------------------------------------------------------
	def get(self, type_id):
		type_cls = o.__types_by_id__.get(type_id, None)

		if type_cls is None:
			spec     = self._read_definition(type_id)
			type_cls = self._define_from_spec(spec)

			if type_cls.__type_id__ != type_id:
				raise ValueError(
					f'Type id mismatch for `{type_cls.__o_module__}`: '
					f'expected `{type_id}`, got `{type_cls.__type_id__}`'
				)

		return type_cls

	# Read fast instance count from file header
	# ----------------------------------------------------------------------
	def get_count(self, type_id):
		path = self._get_path(type_id)

		with open(path, 'rb') as f:
			raw = f.read(self.count_word.size)

		if len(raw) != self.count_word.size:
			raise IOError(f'Corrupted definition file for type `{type_id}`')

		return self.count_word.unpack(raw)[0]

	# Increment fast instance count in file header
	# ----------------------------------------------------------------------
	def inc_count(self, type_id):
		path  = self._get_path(type_id)
		count = 0

		with open(path, 'r+b') as f:
			raw = f.read(self.count_word.size)

			if len(raw) != self.count_word.size:
				raise IOError(f'Corrupted definition file for type `{type_id}`')

			count = self.count_word.unpack(raw)[0] + 1

			f.seek(0)
			f.write(self.count_word.pack(count))

		return count

	# Decrement fast instance count in file header
	# ----------------------------------------------------------------------
	def dec_count(self, type_id):
		path  = self._get_path(type_id)
		count = 0

		with open(path, 'r+b') as f:
			raw = f.read(self.count_word.size)

			if len(raw) != self.count_word.size:
				raise IOError(f'Corrupted definition file for type `{type_id}`')

			count = self.count_word.unpack(raw)[0]

			if count == 0:
				raise ValueError(f'Cannot decrement zero count for type `{type_id}`')

			count -= 1

			f.seek(0)
			f.write(self.count_word.pack(count))

		return count
