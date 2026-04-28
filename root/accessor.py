import o

UNDEFINED = o.Undefined


class Accessor(o.Module):

	READ_ONLY = ('type', 'annotation', 'is_optional')
	ATOMIC    = (int, bool, float, str, type(None))

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Create accessor
	# ----------------------------------------------------------------------
	def __init__(self, target, route=None):
		self.target = target
		self.route  = route or []

	# Move accessor
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		key    = f'{self._key()}.{name}'
		route  = self.route
		target = self.target
		value  = UNDEFINED

		if self._is_field():
			if name == 'annotation':
				annotation = getattr(self.type, '__annotation__', UNDEFINED)
				value      = annotation
			elif name == 'is_optional':
				annotation     = getattr(self.type, '__annotation__', UNDEFINED)
				default        = o.services.Memory.get(f'{self._key()}.default', UNDEFINED)
				field_nullable = False

				if annotation is not UNDEFINED:
					field_nullable = o.Annotation(annotation).is_optional

				value = field_nullable or (default is not UNDEFINED)
			elif o.services.Memory.has(key):
				value = o.services.Memory.get(key)

				if name == 'type':
					value = o.get(value)
			else:
				raise AttributeError(name)
		else:
			value = o.Accessor(
				target,
				route + [name],
			)

		return value

	# Set accessor prop
	# ----------------------------------------------------------------------
	def __setattr__(self, name, value):
		has_route    = 'route' in self.__dict__
		is_dunder    = name.startswith('__') and name.endswith('__')
		is_internal  = name in ('target', 'route', 'READ_ONLY', 'ATOMIC')
		is_internal  = is_internal or is_dunder

		if is_internal:
			object.__setattr__(self, name, value)
		elif has_route and self._is_field():
			if name in self.READ_ONLY:
				raise AttributeError(f'Field prop `{name}` is read-only')

			if not isinstance(value, self.ATOMIC):
				raise ValueError('Value must be atomic')

			o.services.Memory.set(f'{self._key()}.{name}', value)
		else:
			raise AttributeError(name)

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Is accessor on field surface
	# ----------------------------------------------------------------------
	def _is_field(self):
		route = self.route
		return len(route) == 2 and route[0] == '_'

	# Resolve key
	# ----------------------------------------------------------------------
	def _key(self):
		return f'{self.target.__proto__}.{".".join(self.route)}'

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Store value
	# ----------------------------------------------------------------------
	def set(self, value):
		o.services.Memory.set(self._key(), value)
		result = self
		return result

	# Resolve stored value
	# ----------------------------------------------------------------------
	def get(self, default=UNDEFINED):
		value = o.services.Memory.get(self._key(), default)
		return value

	# Remove value
	# ----------------------------------------------------------------------
	def unset(self):
		o.services.Memory.unset(self._key())
		result = self
		return result

	# Check whether value exists
	# ----------------------------------------------------------------------
	def has(self):
		result = o.services.Memory.has(self._key())
		return result

	# Iterate stored items
	# ----------------------------------------------------------------------
	def items(self):
		result = None
		route  = self.route
		target = self.target

		if route == ['_']:
			prefix = f'{self._key()}.'
			items  = {}

			for key, value in o.services.Memory.items(prefix):
				name = key[len(prefix):].split('.')[0]

				if name not in items:
					items[name] = o.Accessor(target, route + [name])

			result = items.items()
		else:
			result = o.services.Memory.items(self._key())

		return result
