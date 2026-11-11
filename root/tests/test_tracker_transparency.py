# ==============================================================================
# TRACKER BEHAVIOR TRANSPARENCY TEST
# ==============================================================================
# Compare the same ontology operations with no tracker and with r, w and rw.
# Observation may change the trace, but not object behavior or persistence.
# ==============================================================================

import time

from contextlib import nullcontext

import o


class TestTrackerTransparency(o.Tester):
	RUNTIME_PREFIX = 'o_tracker_transparency_'

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Select an optional tracking scope without changing the tested operation.
	# ----------------------------------------------------------------------
	@classmethod
	def _scope(cls, mode, reads, writes):
		scope = nullcontext()

		if mode == 'r':
			scope = o.services.Tracker.track('r', reads)
		elif mode == 'w':
			scope = o.services.Tracker.track('w', writes)
		elif mode == 'rw':
			scope = o.services.Tracker.track('rw', reads, writes)

		return scope

	# Return the exact error signature produced by a failing operation.
	# ----------------------------------------------------------------------
	@classmethod
	def _error(cls, operation):
		signature = None

		try:
			operation()
		except Exception as error:
			signature = (type(error).__name__, str(error))

		return signature

	# Exercise fields, collections and built-in methods against real storage.
	# ----------------------------------------------------------------------
	@classmethod
	def _run_operations(cls, mode, Model, Holder):
		person = Model(value=5, label='initial')
		holder = Holder(member=person)
		items  = o.List([3, 1, 2])
		notes  = o.Dict({'a': 1, 'b': 2})
		atom   = o.Str('alex')
		reads  = []
		writes = []

		# The next read must use O's persisted cache-miss path.
		# ----------------------------------------------------------------------
		person.__dict__.pop('value', None)

		with cls._scope(mode, reads, writes):
			before = (
				Model.label,
				person.value,
				person.value,
				person.label,
				person.description,
				holder.member is person,
				items[0],
				len(items),
				tuple(items),
				notes['a'],
				'a' in notes,
				'missing' in notes,
				len(notes),
				tuple(notes.keys()),
				tuple(notes.items()),
				atom.upper(),
			)

			person.value = 7
			person.label = 'assigned'
			del person.label
			default_after_delete = person.label

			items.sort()
			popped_list = items.pop()
			items.append(4)
			items[0] = 9
			del items[1]
			items.reverse()

			notes.update({'c': 3})
			notes['a'] = 9
			popped_dict = notes.pop('b')
			del notes['c']
			notes.setdefault('d', 4)

			during = (
				person.value,
				default_after_delete,
				tuple(items),
				tuple(notes.items()),
				popped_list,
				popped_dict,
				holder.member is person,
			)

		# Compare actual persisted state as well as the visible Python values.
		# ----------------------------------------------------------------------
		stored_value = o.services.Entity.value(person.__zone__.get('value'))
		list_bytes   = items.__zone__.get('__items__')
		dict_bytes   = notes.__zone__.get('__items__')
		result       = (
			before,
			during,
			person.value,
			person.label,
			stored_value,
			person.__zone__.has('value'),
			person.__zone__.has('label'),
			tuple(sorted(
				key for key in person.__dict__
				if key != 'id' and not key.startswith('_')
			)),
			tuple(items),
			tuple(notes.items()),
			len(list_bytes),
			len(dict_bytes),
			atom.__value__,
		)

		return result

	# Compare errors, unchanged state and failed deletion side effects.
	# ----------------------------------------------------------------------
	@classmethod
	def _run_failures(cls, mode, Model):
		person = Model(value=5)
		items  = o.List([1, 2])
		notes  = o.Dict({'a': 1})
		reads  = []
		writes = []
		errors = []

		with cls._scope(mode, reads, writes):
			errors.append(cls._error(lambda: items[100]))
			errors.append(cls._error(lambda: notes['absent']))
			errors.append(cls._error(lambda: delattr(notes, 'absent')))
			errors.append(cls._error(lambda: getattr(person, 'absent')))
			errors.append(cls._error(lambda: setattr(person, 'absent', 8)))
			errors.append(cls._error(lambda: setattr(person, '_private', 8)))
			errors.append(cls._error(lambda: delattr(person, 'absent')))
			errors.append(cls._error(lambda: notes.__delitem__('absent')))

			del person.value
			errors.append(cls._error(lambda: person.value))
			errors.append(cls._error(lambda: delattr(person, 'value')))

		result = (
			tuple(errors),
			person.__zone__.has('value'),
			'value' in person.__dict__,
			tuple(items),
			tuple(notes.items()),
			len(items.__zone__.get('__items__')),
			len(notes.__zone__.get('__items__')),
		)

		return result

	# Check class defaults, inherited fields and new runtime field publication.
	# ----------------------------------------------------------------------
	@classmethod
	def _run_schema_changes(cls, mode):
		name   = f'TrackerTransparencySchema{time.time_ns()}'
		Base   = o.T.extend(name, count=o.F(int, default=3))
		reads  = []
		writes = []

		with cls._scope(mode, reads, writes):
			Child    = Base.extend('Child', title=o.F(str, default='initial'))
			instance = Child()
			before   = (Base.count, Child.count, instance.count, instance.title)

			Child.extra = o.F(int, default=7)
			added       = (Child.extra, instance.extra)

			Child.extra = 13
			changed     = (Child.extra, instance.extra)

			instance.title = 'updated'
			del instance.title
			restored = instance.title

			del Child.extra
			missing = cls._error(lambda: getattr(instance, 'extra'))

		result = (
			before,
			added,
			changed,
			restored,
			missing,
			Child.__has_field__('extra'),
			Child.__has_field__('title'),
			'title' in instance.__dict__,
			'extra' in instance.__dict__,
		)

		return result

	# Verify fresh reconstruction observes the same entity shape and values.
	# ----------------------------------------------------------------------
	@classmethod
	def _run_reconstruction(cls, mode, Model):
		person = Model(value=4, label='saved')
		items  = o.List([1, 2, 3])
		notes  = o.Dict({'a': 1, 'b': 2})
		reads  = []
		writes = []

		with cls._scope(mode, reads, writes):
			person.value = 5
			items[0] = 7
			notes['a'] = 9

			person.__invalidate__()
			items.__invalidate__()
			notes.__invalidate__()

			during = (
				person.value,
				person.label,
				tuple(items),
				tuple(notes.items()),
			)

		result = (
			during,
			person.value,
			person.label,
			tuple(items),
			tuple(notes.items()),
			o.services.Entity.value(person.__zone__.get('value')),
		)

		return result

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Compare complete return values, object caches and persisted mutations.
	# ----------------------------------------------------------------------
	@classmethod
	def test_normal_operations_match_without_tracking(cls):
		state = cls._patch_runtime()

		try:
			name     = f'TrackerTransparencyModel{time.time_ns()}'
			Model    = o.T.extend(name, value=int, label=o.F(str, default='default'))
			Holder   = o.T.extend(f'{name}Holder', member=Model)
			baseline = cls._run_operations(None, Model, Holder)

			for mode in ('r', 'w', 'rw'):
				assert cls._run_operations(mode, Model, Holder) == baseline, mode
		finally:
			cls._restore_runtime(state)

	# Preserve raised exception classes/messages and resulting persisted state.
	# ----------------------------------------------------------------------
	@classmethod
	def test_failures_match_without_tracking(cls):
		state = cls._patch_runtime()

		try:
			Model    = o.T.extend(f'TrackerTransparencyErrors{time.time_ns()}', value=int)
			baseline = cls._run_failures(None, Model)

			assert all(error is not None for error in baseline[0])

			for mode in ('r', 'w', 'rw'):
				assert cls._run_failures(mode, Model) == baseline, mode
		finally:
			cls._restore_runtime(state)

	# Preserve runtime class schema and inherited default semantics.
	# ----------------------------------------------------------------------
	@classmethod
	def test_schema_changes_match_without_tracking(cls):
		state = cls._patch_runtime()

		try:
			baseline = cls._run_schema_changes(None)

			for mode in ('r', 'w', 'rw'):
				assert cls._run_schema_changes(mode) == baseline, mode
		finally:
			cls._restore_runtime(state)

	# Preserve cache invalidation and reconstruction under every mode.
	# ----------------------------------------------------------------------
	@classmethod
	def test_reconstruction_matches_without_tracking(cls):
		state = cls._patch_runtime()

		try:
			Model    = o.T.extend(
				f'TrackerTransparencyReload{time.time_ns()}',
				value = int,
				label = str,
			)
			baseline = cls._run_reconstruction(None, Model)

			for mode in ('r', 'w', 'rw'):
				assert cls._run_reconstruction(mode, Model) == baseline, mode
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestTrackerTransparency.run()
