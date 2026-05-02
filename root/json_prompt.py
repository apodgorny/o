import o

UNDEFINED = o.Undefined


class JsonPrompt(o.Module):

	ATOMIC_TYPES = {
		str        : 'str',
		int        : 'int',
		float      : 'float',
		bool       : 'bool',
		type(None) : 'null',
	}

	# Build prompt on call
	# ----------------------------------------------------------------------
	def __new__(cls, t_cls):
		result = cls.build(t_cls)
		return result

	# Build class prompt
	# ----------------------------------------------------------------------
	@classmethod
	def build(cls, t_cls):
		lines  = ()
		prompt = None

		if t_cls is o.T:
			raise TypeError('`o.T` has no single JSON prompt')

		lines  = cls._get_root_prompt_lines(t_cls, ())
		lines  = cls._align_comments(lines)
		prompt = '\n'.join(lines)

		return prompt

	# Build root prompt lines
	# ----------------------------------------------------------------------
	@classmethod
	def _get_root_prompt_lines(cls, t_cls, stack):
		annotation = getattr(t_cls, '__annotation__', UNDEFINED)
		lines      = ()

		if annotation is UNDEFINED:
			lines = cls._get_object_prompt_lines(t_cls, stack)
		else:
			lines = cls._get_annotation_prompt_lines(annotation, stack)

		return lines

	# Build nested class prompt lines
	# ----------------------------------------------------------------------
	@classmethod
	def _get_class_prompt_lines(cls, t_cls, stack):
		annotation = getattr(t_cls, '__annotation__', UNDEFINED)
		lines      = ()
		name       = cls._get_class_name(t_cls)

		if annotation is UNDEFINED:
			if name in stack:
				lines = (name,)
			else:
				lines = cls._get_object_prompt_lines(t_cls, stack + (name,))
		else:
			lines = cls._get_annotation_prompt_lines(annotation, stack)

		return lines

	# Build annotation prompt lines
	# ----------------------------------------------------------------------
	@classmethod
	def _get_annotation_prompt_lines(cls, annotation, stack):
		annotation = o.Annotation(annotation)
		lines      = ()

		if annotation.is_union:
			text  = str(annotation).replace('None', 'null')
			lines = (text,)
		elif annotation.is_none:
			lines = ('null',)
		elif isinstance(annotation.annotation, type) and issubclass(annotation.annotation, o.T):
			lines = cls._get_class_prompt_lines(annotation.annotation, stack)
		elif annotation.is_list:
			lines = cls._get_list_prompt_lines(annotation.value, stack)
		elif annotation.is_dict:
			lines = cls._get_dict_prompt_lines(annotation.key, annotation.value, stack)
		else:
			text = cls.ATOMIC_TYPES.get(annotation.origin, UNDEFINED)

			if text is UNDEFINED:
				raise TypeError(f'Unsupported JSON prompt annotation: `{annotation}`')

			lines = (text,)

		return lines

	# Build list prompt lines
	# ----------------------------------------------------------------------
	@classmethod
	def _get_list_prompt_lines(cls, value, stack):
		lines      = ()
		value_lines = ('value',)

		if value is not None:
			value_lines = cls._get_annotation_prompt_lines(value, stack)

		if len(value_lines) == 1:
			lines = (f'[{value_lines[0]}]',)
		else:
			lines = ['[']

			for line in value_lines:
				lines.append(f'    {line}')

			lines.append(']')
			lines = tuple(lines)

		return lines

	# Build dict prompt lines
	# ----------------------------------------------------------------------
	@classmethod
	def _get_dict_prompt_lines(cls, key, value, stack):
		lines       = ()
		key_text    = 'key'
		key_comment = ''
		value_lines = ('value',)

		if key is not None:
			key_text    = cls._get_key_text(key)
			key_comment = cls._get_key_comment(key)

		if value is not None:
			value_lines = cls._get_annotation_prompt_lines(value, stack)

		lines = [ '{' ]
		line  = f'    {key_text} : {value_lines[0]}'

		if key_comment:
			line += f'  {key_comment}'

		lines.append(line)

		for line in value_lines[1:]:
			lines.append(f'    {line}')

		lines.append('}')
		lines = tuple(lines)

		return lines

	# Build object prompt lines
	# ----------------------------------------------------------------------
	@classmethod
	def _get_object_prompt_lines(cls, t_cls, stack):
		lines         = ['{']
		items         = list(cls._get_fields(t_cls).items())
		entries       = []
		max_key_width = 0
		max_line_len  = 0

		with o.services.Memory.read():
			for index, item in enumerate(items):
				name, field   = item
				key_text      = f'\'{name}\''
				field_lines   = list(cls._get_field_prompt_lines(field, stack))
				description   = cls._get_field_description(field)
				comment       = ''
				has_comment   = description is not UNDEFINED and description is not None
				is_last       = index == len(items) - 1

				if has_comment:
					comment = f'# {description}'

				if len(key_text) > max_key_width:
					max_key_width = len(key_text)

				entries.append({
					'key_text'    : key_text,
					'field_lines' : field_lines,
					'comment'     : comment,
					'is_last'     : is_last,
				})

		for entry in entries:
			key_text    = entry['key_text']
			field_lines = entry['field_lines']
			line        = f'    {key_text.ljust(max_key_width)} : {field_lines[0]}'

			if len(field_lines) == 1 and not entry['is_last']:
				line += ','

			if len(line) > max_line_len:
				max_line_len = len(line)

		for entry in entries:
			key_text    = entry['key_text']
			field_lines = entry['field_lines']
			comment     = entry['comment']
			line        = f'    {key_text.ljust(max_key_width)} : {field_lines[0]}'

			if len(field_lines) == 1 and not entry['is_last']:
				line += ','

			if comment:
				padding = ' ' * (max_line_len - len(line) + 1)
				line += f'{padding}{comment}'

			lines.append(line)

			for field_line in field_lines[1:]:
				lines.append(f'    {field_line}')

			if len(field_lines) > 1 and not entry['is_last']:
				lines[-1] += ','

		lines.append('}')
		return tuple(lines)

	# Build field prompt lines
	# ----------------------------------------------------------------------
	@classmethod
	def _get_field_prompt_lines(cls, field, stack):
		field_cls  = field.type
		annotation = getattr(field_cls, '__annotation__', UNDEFINED)
		lines      = ()

		if annotation is UNDEFINED:
			lines = cls._get_class_prompt_lines(field_cls, stack)
		else:
			lines = cls._get_annotation_prompt_lines(annotation, stack)

		if cls._is_field_nullable(field):
			lines = cls._make_nullable(lines)

		return lines

	# Merge inherited field view
	# ----------------------------------------------------------------------
	@classmethod
	def _get_fields(cls, t_cls):
		fields = {}

		for base in reversed(t_cls.__mro__):
			namespace = base.__dict__.get('_')

			if namespace is not None:
				for name, field in namespace.items():
					fields[name] = field

		return fields

	# Check field nullability
	# ----------------------------------------------------------------------
	@classmethod
	def _is_field_nullable(cls, field):
		field_cls      = field.type
		field_type     = getattr(field_cls, '__annotation__', UNDEFINED)
		default        = getattr(field, 'default', UNDEFINED)
		field_nullable = False

		if field_type is not UNDEFINED:
			field_nullable = o.Annotation(field_type).is_optional

		return field_nullable or (default is None)

	# Get field description
	# ----------------------------------------------------------------------
	@classmethod
	def _get_field_description(cls, field):
		description = UNDEFINED

		try:
			description = field.description
		except AttributeError:
			description = UNDEFINED

		return description

	# Get display name for recursive class
	# ----------------------------------------------------------------------
	@classmethod
	def _get_class_name(cls, t_cls):
		return t_cls.__proto__

	# Get prompt text for dict key
	# ----------------------------------------------------------------------
	@classmethod
	def _get_key_text(cls, key):
		key_text    = 'key'
		key_lines   = cls._get_annotation_prompt_lines(key, ())

		if len(key_lines) == 1:
			key_text = key_lines[0]

		if key_text == 'str':
			key_text = '\'key\''

		return key_text

	# Get prompt comment for dict key
	# ----------------------------------------------------------------------
	@classmethod
	def _get_key_comment(cls, key):
		comment   = ''
		key_lines = cls._get_annotation_prompt_lines(key, ())

		if len(key_lines) == 1:
			comment = f' # {key_lines[0]} key'

		return comment

	# Add null branch
	# ----------------------------------------------------------------------
	@classmethod
	def _make_nullable(cls, lines):
		items = list(lines)

		items[-1] += ' | null'

		return tuple(items)

	# Align prompt comments into one column
	# ----------------------------------------------------------------------
	@classmethod
	def _align_comments(cls, lines):
		aligned        = []
		comment_column = 0
		prefixes       = []
		has_key_line   = False
		has_plain_tree = False

		for line in lines:
			if '#' in line:
				prefix = line.split('#', 1)[0].rstrip()
				prefixes.append(prefix)

				if '\'key\'' in prefix:
					has_key_line = True

				if prefix.endswith('{'):
					has_plain_tree = True

				if len(prefixes) > 1 and line.index('#') > comment_column:
					comment_column = line.index('#')

		if prefixes:
			prefix_column = max(len(prefix) for prefix in prefixes)

			if has_plain_tree and not has_key_line:
				comment_column = prefix_column + 1
			elif prefix_column + 2 > comment_column:
				comment_column = prefix_column + 2

		for line in lines:
			aligned_line = line

			if '#' in line:
				prefix, comment = line.split('#', 1)
				prefix          = prefix.rstrip()
				padding         = ' ' * (comment_column - len(prefix))
				aligned_line    = f'{prefix}{padding}#{comment}'

			aligned.append(aligned_line)

		return tuple(aligned)
