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
	def __init__(self, target, route=None, zone=None):
		self.target = target
		self.route  = route or []
		self.zone   = zone or o.services.Memory.zone(f'{target.__proto__}.')

	# Move accessor
	# ----------------------------------------------------------------------
	def __getattr__(self, name):
		key    = self._key()
		route  = self.route
		target = self.target
		zone   = self.zone
		value  = UNDEFINED

		if self._is_field():
			if name == 'annotation':
				annotation = getattr(self.type, '__annotation__', UNDEFINED)
				value      = annotation
			elif name == 'is_optional':
				annotation     = getattr(self.type, '__annotation__', UNDEFINED)
				default        = zone.get(f'{key}.default', UNDEFINED)
				field_nullable = False

				if annotation is not UNDEFINED:
					field_nullable = o.Annotation(annotation).is_optional

				value = field_nullable or (default is not UNDEFINED)
			else:
				value = zone.get(f'{key}.{name}', UNDEFINED)

				if value is UNDEFINED:
					raise AttributeError(name)

				if name == 'type':
					value = o.get(value)

		else:
			value = o.Accessor(
				target,
				route + [name],
				zone,
			)

		return value

	# Set accessor prop
	# ----------------------------------------------------------------------
	def __setattr__(self, name, value):
		has_route    = 'route' in self.__dict__
		is_dunder    = name.startswith('__') and name.endswith('__')
		is_internal  = name in ('target', 'route', 'zone', 'READ_ONLY', 'ATOMIC')
		is_internal  = is_internal or is_dunder

		if is_internal:
			object.__setattr__(self, name, value)
		elif has_route and self._is_field():
			if name in self.READ_ONLY:
				raise AttributeError(f'Field prop `{name}` is read-only')

			if not isinstance(value, self.ATOMIC):
				raise ValueError('Value must be atomic')

			self.zone.set(f'{self._key()}.{name}', value)
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
		return '.'.join(self.route)

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Store value
	# ----------------------------------------------------------------------
	def set(self, value):
		self.zone.set(self._key(), value)
		result = self
		return result

	# Resolve stored value
	# ----------------------------------------------------------------------
	def get(self, default=UNDEFINED):
		value = self.zone.get(self._key(), default)
		return value

	# Remove value
	# ----------------------------------------------------------------------
	def unset(self):
		self.zone.unset(self._key())
		result = self
		return result

	# Check whether value exists
	# ----------------------------------------------------------------------
	def has(self):
		result = self.zone.has(self._key())
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

			for key in self.zone.keys(prefix):
				name = key[len(prefix):].split('.')[0]

				if name not in items:
					items[name] = o.Accessor(target, route + [name], self.zone)

			result = items.items()
		else:
			result = self.zone.items(self._key())

		return result
