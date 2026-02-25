import o


class T(o.Service):

	def initialize(self):
		pass

	def __call__(self, *args, **kwargs):
		return o.Type(*args, **kwargs)

	def __getattr__(self, type_name):
		return self[type_name]

	def __getitem__(self, type_name):
		if type_name in o.types:
			return o.types[type_name]
		raise KeyError(f'Unknown type `{type_name}`')

	def __contains__(self, type_name):
		return type_name in o.types

	def define(self, schema_name, **fields):
		normalized = {}

		for name, value in fields.items():
			if isinstance(value, o.F):
				normalized[name] = value
			else:
				t = o.Type(value)
				default = None if t.is_optional() else o.undefined
				normalized[name] = o.F(t.to_non_optional().annotation, default=default)

		return o.Schema.define(schema_name, **normalized)