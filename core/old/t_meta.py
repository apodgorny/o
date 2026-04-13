import o


class TMeta(o.ModuleMeta):

	# Get attribute of class
	# ----------------------------------------------------------------------
	def __getattr__(cls, name):
		result = None

		if name[:1].isupper():
			result = cls.__load_subclass__(name)

		if result is None:
			raise AttributeError(f'Class `{cls.__name__}` has no attribute `{name}`')

		return result

	# Set attribute on class
	# ----------------------------------------------------------------------
	def __setattr__(cls, name, value):
		super().__setattr__(name, value)

		if not name.startswith('_'):
			cls.__write__()

	# Delete attribute on class
	# ----------------------------------------------------------------------
	def __delattr__(cls, name):
		super().__delattr__(name)

		if not name.startswith('_'):
			cls.__write__()

	# Load subclass
	# ----------------------------------------------------------------------
	def __load_subclass__(cls, name):
		proto = f'{cls.__proto__}.{name}'
		id_   = o.hash(proto)

		(
			o_module,
			attributes,
			_,
			_,
			proto_parent,
			proto_children,
			_,
		) = o.services.Store.read(id_)

		namespace = dict(attributes)
		namespace['__id__']             = id_
		namespace['__proto__']          = proto
		namespace['__o_module__']       = o_module
		namespace['__proto_parent__']   = proto_parent
		namespace['__proto_children__'] = proto_children

		return TMeta(name, (cls,), namespace)

	# Read store and restore internal state
	# ----------------------------------------------------------------------
	def __read__(cls):

		# Read internal state from disk
		# - - - - - - - - - - - - - - - - - -
		(
			cls.__o_module__,
			attributes,
			_,
			_,
			cls.__proto_parent__,
			cls.__proto_children__,
			_,
		) = o.services.Store.read(cls.__id__)

		# Set attributes to object from dict
		# - - - - - - - - - - - - - - - - - -
		for name, value in attributes.items():
			super().__setattr__(name, value)

	# Write internal state to store
	# ----------------------------------------------------------------------
	def __write__(cls):

		# Collect attributes into dict
		# - - - - - - - - - - - - - - - - - -
		attributes = {
			key:ref
			for key, ref in vars(cls).items()
			if not key.startswith('_')
		}

		# Write internal state to disk
		# - - - - - - - - - - - - - - - - - -
		o.services.Store.write(
			cls.__id__,
			o_module       = cls.__o_module__,
			attributes     = attributes,
			list_items     = [],
			dict_items     = {},
			proto_parent   = getattr(cls, '__proto_parent__', None),
			proto_children = getattr(cls, '__proto_children__', []),
			value          = None,
		)

	# Validate field value
	# --------------------------------------------------------------
	def __validate__(cls, value):
		tp = cls.type
		
		# Undefined
		# - - - - - - - - - - - - - - - - - - - -
		if value is o.undefined:
			if cls.default is not o.undefined:
				value = cls.default
			elif cls.is_optional:
				value = None
			else:
				raise TypeError(f'Field `{cls.name}` is not optional and must not be undefined.')

		# None
		# - - - - - - - - - - - - - - - - - - - -
		elif value is None:
			if not cls.is_optional:
				raise TypeError(f'Field `{cls.name}` is not optional and must not be None.')

		# Value
		# - - - - - - - - - - - - - - - - - - - -
		else:

			# Any o.T
			# - - - - - - - - - - - - - - - - - - - -
			if isinstance(value, o.T):
				if not (isinstance(tp.annotation, type) and issubclass(tp.annotation, o.T)):
					raise TypeError(f'Field `{cls.name}`: expected `{tp.annotation}`, got `{type(value)}`.')
				elif not isinstance(value, tp.annotation):
					raise TypeError(f'Field `{cls.name}`: expected `{tp.annotation}`, got `{type(value)}`.')

			# Not o.T
			# - - - - - - - - - - - - - - - - - - - -
			else:
				actual = o.Type.annotate(value)
				if actual not in tp:
					raise TypeError(
						f'Field `{cls.name}`: expected `{tp.annotation}`, got `{actual.annotation}`.'
					)

		return value
