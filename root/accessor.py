import o

UNDEFINED       = o.Undefined
READ_ONLY_PROPS = ('type', 'annotation', 'is_optional')
ATOMIC          = (int, bool, float, str, type(None))


class Accessor(o.Module):

	# ======================================================================
	# FRAMEWORK METHODS
	# ======================================================================

	# Create accessor
	# ----------------------------------------------------------------------
	def __init__(self, target, route=None, zone=None):
		self.target = target
		self.route  = route or []
		self.zone   = zone or target.__zone__

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
				value = getattr(self.type, '__annotation__', UNDEFINED)
			elif name == 'is_optional':
				value = self._is_optional(key)
			else:
				value = self._field_zone(name).get(f'{key}.{name}', UNDEFINED)
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
		is_internal  = name in ('target', 'route', 'zone') or is_dunder

		if is_internal:
			object.__setattr__(self, name, value)
		elif has_route and self._is_field():
			if self._can_set_prop(name, value):
				self.zone.set(f'{self._key()}.{name}', value)
		else:
			raise AttributeError(name)

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Get field default?
	# ----------------------------------------------------------------------
	def _get_default(self, key):
		return self._field_zone('default').get(f'{key}.default', UNDEFINED)

	# Resolve field owner
	# ----------------------------------------------------------------------
	def _field_owner(self):
		target_cls = self.target if isinstance(self.target, type) else self.target.__class__
		return target_cls.__class__.__field_owner__(target_cls, self.route[1])

	# Resolve field zone
	# ----------------------------------------------------------------------
	def _field_zone(self, prop='type'):
		owner = self._field_owner()
		zone  = self.zone

		if owner is not UNDEFINED and owner.__zone__.has(f'{self._key()}.{prop}'):
			zone = owner.__zone__

		return zone

	# Is field optional?
	# ----------------------------------------------------------------------
	def _is_optional(self, key):
		annotation     = getattr(self.type, '__annotation__', UNDEFINED)
		has_default    = self._get_default(key) is not UNDEFINED
		field_nullable = False

		if annotation is not UNDEFINED:
			field_nullable = o.Annotation(annotation).is_optional

		return field_nullable or has_default

	# Can set field property?
	# ----------------------------------------------------------------------
	def _can_set_prop(self, name, value):
		if name in READ_ONLY_PROPS:
			raise AttributeError(f'Field prop `{name}` is read-only')

		if not isinstance(value, ATOMIC):
			raise ValueError('Value must be atomic')
		
		return True

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
		return self

	# Resolve stored value
	# ----------------------------------------------------------------------
	def get(self, default=UNDEFINED):
		return self.zone.get(self._key(), default)

	# Remove value
	# ----------------------------------------------------------------------
	def unset(self):
		self.zone.unset(self._key())
		return self

	# Check whether value exists
	# ----------------------------------------------------------------------
	def has(self):
		return self.zone.has(self._key())

	# Iterate stored items
	# ----------------------------------------------------------------------
	def items(self):
		route  = self.route
		target = self.target

		if route == ['_']:
			prefix = f'{self._key()}.'
			items  = {}

			for key in self.zone.keys(prefix):
				name = key[len(prefix):].split('.')[0]
				if name not in items:
					items[name] = o.Accessor(target, route + [name], self.zone)

			return items.items()
		
		return self.zone.items(self._key())
