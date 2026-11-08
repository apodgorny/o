# ==============================================================================
# MIGRATION SERVICE
# ==============================================================================
# Validate and apply stored-instance schema changes.
# ==============================================================================

import sys

import o


UNDEFINED = o.Undefined
ATOMIC    = (int, float, str, bool, type(None))


class Migration(o.Service):

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Check whether a descendant overrides an inherited field
	# ----------------------------------------------------------------------
	def _is_overridden(self, memory, existing, class_proto, name):
		ancestor   = existing.__proto__
		relative   = class_proto[len(ancestor):].strip('.')
		overridden = False

		if relative:
			for part in relative.split('.'):
				ancestor += '.' + part

				if memory.has(f'{ancestor}._.{name}.type'):
					overridden = True
					break

		return overridden

	# Validate atomic conversion without creating persistent entities
	# ----------------------------------------------------------------------
	def _convert(self, memory, key, old_id, change):
		old_type       = o.services.Entity.get(change['old']['type'])
		old_annotation = o.Annotation(getattr(old_type, '__annotation__', old_type))
		new_type       = change['new'].type
		new_annotation = o.Annotation(getattr(new_type, '__annotation__', new_type))

		atomic = (
			old_annotation.origin in ATOMIC and
			new_annotation.origin in ATOMIC
		)

		if atomic:
			proto = memory.get(f'ids/{old_id}', UNDEFINED)

			if proto is not UNDEFINED and proto.startswith(old_type.__proto__ + '._'):
				value = memory.get(f'{proto}.__value__', UNDEFINED)

				if value is not UNDEFINED:
					try:
						converted = new_annotation.cast(value)
					except (TypeError, ValueError) as error:
						raise ValueError(
							f'Cannot convert `{key}` '
							f'(id={old_id}, value={value!r}): {error}'
						) from error
				else:
					raise ValueError(f'Missing atomic value for `{key}` (id={old_id})')
			else:
				raise ValueError(f'Invalid stored type for `{key}` (id={old_id})')
		else:
			raise TypeError(f'Only atomic type conversions are supported for `{key}`')

		return converted

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Prepare migration without modifying stored instance data
	# ----------------------------------------------------------------------
	def prepare(self, existing, fields, annotation):
		ready = not type.__subclasses__(existing)

		if ready:
			ready = not any(
				isinstance(entity, existing)
				for entity in o.services.Cache.entities.values()
			)

		if ready:
			changes = self.analyze(existing, fields, annotation)
			self.inspect(existing, changes)
			self.ask_questions(existing, changes)
		else:
			raise RuntimeError(
				f'Migration requires unloaded instances and subclasses: '
				f'`{existing.__proto__}`'
			)

		return changes

	# Identify fields requiring stored-data migration or validation
	# ----------------------------------------------------------------------
	def analyze(self, existing, fields, annotation):
		annotation_unchanged = (
			annotation is None or
			getattr(existing, '__annotation__', UNDEFINED) == o.Annotation(annotation)
		)

		if annotation_unchanged:
			old_fields = existing.__class__.__read__(existing)
			new_fields = {
				name: field if isinstance(field, o.F) else o.F(field)
				for name, field in fields.items()
			}
			changes = {}

			for name in sorted(old_fields.keys() | new_fields.keys()):
				old          = old_fields.get(name)
				new          = new_fields.get(name)
				type_changed = False

				if old is not None and new is not None:
					if isinstance(new.type, type) and issubclass(new.type, o.T):
						type_changed = old['type'] != new.type.id
					else:
						old_type       = o.services.Entity.get(old['type'])
						old_annotation = getattr(old_type, '__annotation__', old_type)
						type_changed   = (
							o.Annotation(old_annotation) != o.Annotation(new.type)
						)

				required = (
					new is not None and new.default is UNDEFINED and
					(old is None or old.get('default', UNDEFINED) is not UNDEFINED)
				)

				if required or (old is not None and (new is None or type_changed)):
					changes[name] = {
						'old'          : old,
						'new'          : new,
						'required'     : required,
						'type_changed' : type_changed,
						'updates'      : [],
					}
		else:
			raise TypeError('Changing class annotation is not supported')

		return changes

	# Inspect persisted instances and validate proposed conversions
	# ----------------------------------------------------------------------
	def inspect(self, existing, changes):
		if changes:
			prefix = existing.__proto__ + '.'

			with o.services.Memory.read() as memory:
				for key, old_id in memory.items(prefix):
					parts = key[len(prefix):].split('.')

					if o.TMeta.is_instance_version(parts[-1]):
						class_proto = key.rsplit('._', 1)[0]

						for name, change in changes.items():
							if change['required']:
								if not self._is_overridden(memory, existing, class_proto, name):
									if memory.has(f'{key}.{name}'):
										pass
									else:
										raise TypeError(
											f'Required field `{name}` is missing on `{key}`'
										)

					elif len(parts) >= 2 and o.TMeta.is_instance_version(parts[-2]):
						name   = parts[-1]
						change = changes.get(name)

						if change is not None and change['old'] is not None:
							class_proto = key.rsplit('._', 1)[0]

							if not self._is_overridden(memory, existing, class_proto, name):
								value = None

								if change['type_changed']:
									value = self._convert(memory, key, old_id, change)

								change['updates'].append((key, old_id, value))

	# Collect all approvals before changing stored data
	# ----------------------------------------------------------------------
	def ask_questions(self, existing, changes):
		for name, change in changes.items():
			needs_approval = (
				change['type_changed'] or
				(change['new'] is None and bool(change['updates']))
			)

			if needs_approval:
				if sys.stdin.isatty() and sys.stdout.isatty():
					action = 'Delete' if change['new'] is None else 'Change type of'
					count  = len(change['updates'])

					answer = input(
						f'{action} `{existing.__proto__}.{name}` '
						f'({count} stored values)? [y/N] '
					).strip().lower()

					if answer in ('y', 'yes'):
						pass
					else:
						raise RuntimeError('Migration canceled; no data changed')
				else:
					raise RuntimeError(
						'Migration required. Run the program in an interactive '
						'terminal; migration questions will be asked.'
					)

	# Apply approved changes within the caller's write transaction
	# ----------------------------------------------------------------------
	def apply(self, changes):
		with o.services.Memory.write() as memory:
			for change in changes.values():
				target = None

				if change['type_changed'] and change['updates']:
					target = o.TMeta.__embody__(change['new'].type)

				for key, old_id, value in change['updates']:
					if memory.get(key, UNDEFINED) == old_id:
						parent = o.services.Entity.get(key.rsplit('.', 1)[0])

						if change['new'] is None:
							parent.__unlink__(o.services.Entity.get(old_id))
							memory.unset(key)
						else:
							child = o.services.Entity.cast(target, value)
							parent.__link__(child)
							parent.__unlink__(o.services.Entity.get(old_id))
							memory.set(key, child.id)
					else:
						raise RuntimeError(
							f'Stored value changed after migration approval: `{key}`'
						)
