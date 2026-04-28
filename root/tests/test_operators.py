import os
import shutil
import tempfile

import o

UNDEFINED = o.Undefined


class TestOperators(o.Tester):

	# ----------------------------------------------------------------------
	@classmethod
	def _patch_registry(cls):
		services = o.services
		registry = type('RegistryState', (), {})()
		state    = {
			'services'     : services,
			'had_registry' : 'Registry' in services.__dict__,
			'registry'     : services.__dict__.get('Registry'),
			'paths'        : {},
		}

		def add(id, path):
			state['paths'][id] = path

		def remove(id):
			if id in state['paths']:
				del state['paths'][id]

		def get(id):
			return state['paths'].get(id, UNDEFINED)

		registry.add    = add
		registry.remove = remove
		registry.get    = get

		services.Registry = registry

		return state

	# ----------------------------------------------------------------------
	@classmethod
	def _restore_registry(cls, state):
		services = state['services']

		if state['had_registry']:
			services.Registry = state['registry']
		else:
			del services.Registry

	# ----------------------------------------------------------------------
	@classmethod
	def _patch_runtime(cls):
		temp_root      = os.path.join(o.__path__, '__tmp__')
		registry_state = cls._patch_registry()

		os.makedirs(temp_root, exist_ok=True)

		root = tempfile.mkdtemp(prefix='o_operators_', dir=temp_root)

		state = {
			'root'      : root,
			'temp_root' : temp_root,
			'registry'  : registry_state,
			'data_dir'  : o.DATA_DIR,
			'entities'  : dict(o.__entities__),
			'cast_map'  : dict(o.__cast_map__),
			'value'     : o.__dict__.get('V', UNDEFINED),
		}

		o.DATA_DIR = os.path.join('__tmp__', os.path.basename(root))

		return state

	# ----------------------------------------------------------------------
	@classmethod
	def _restore_runtime(cls, state):
		o.DATA_DIR = state['data_dir']

		o.__entities__.clear()
		o.__entities__.update(state['entities'])

		o.__cast_map__.clear()
		o.__cast_map__.update(state['cast_map'])

		if state['value'] is UNDEFINED:
			if 'V' in o.__dict__:
				del o.__dict__['V']
		else:
			o.__dict__['V'] = state['value']

		cls._restore_registry(state['registry'])

		if os.path.isdir(state['temp_root']):
			shutil.rmtree(state['temp_root'])

	# ----------------------------------------------------------------------
	@classmethod
	def test_operator_surface_exists(cls):
		names = [
			'__pos__',
			'__neg__',
			'__abs__',
			'__invert__',
			'__add__',
			'__sub__',
			'__mul__',
			'__matmul__',
			'__truediv__',
			'__floordiv__',
			'__mod__',
			'__pow__',
			'__lshift__',
			'__rshift__',
			'__and__',
			'__xor__',
			'__or__',
			'__radd__',
			'__rsub__',
			'__rmul__',
			'__rmatmul__',
			'__rtruediv__',
			'__rfloordiv__',
			'__rmod__',
			'__rpow__',
			'__rlshift__',
			'__rrshift__',
			'__rand__',
			'__rxor__',
			'__ror__',
			'__lt__',
			'__le__',
			'__eq__',
			'__ne__',
			'__gt__',
			'__ge__',
		]

		for name in names:
			assert callable(getattr(o.T, name))

	# ----------------------------------------------------------------------
	@classmethod
	def test_unary_operators_delegate_to_visible_value(cls):
		state = cls._patch_runtime()

		try:
			assert +o.Int(7) == 7
			assert -o.Int(7) == -7
			assert abs(o.Int(-7)) == 7
			assert ~o.Int(1) == -2
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_binary_operators_delegate_to_visible_value(cls):
		state = cls._patch_runtime()

		try:
			assert o.Int(7) + o.Int(2) == 9
			assert o.Int(7) - 2 == 5
			assert o.Int(3) * 4 == 12
			assert o.Int(7) // 2 == 3
			assert o.Int(7) % 4 == 3
			assert o.Int(2) ** 3 == 8
			assert o.Int(6) & 3 == 2
			assert o.Int(6) ^ 3 == 5
			assert o.Int(6) | 3 == 7
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_reflected_operators_delegate_to_visible_value(cls):
		state = cls._patch_runtime()

		try:
			assert 2 + o.Int(3) == 5
			assert 10 - o.Int(3) == 7
			assert 4 * o.Int(3) == 12
			assert 8 // o.Int(2) == 4
			assert 8 % o.Int(3) == 2
			assert 2 ** o.Int(3) == 8
			assert 8 >> o.Int(1) == 4
			assert 1 | o.Int(2) == 3
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_comparison_operators_delegate_to_visible_value(cls):
		state = cls._patch_runtime()

		try:
			assert (o.Int(2) < o.Int(3)) == True
			assert (o.Int(2) <= 2) == True
			assert (o.Int(2) == o.Int(2)) == True
			assert (o.Int(2) != 3) == True
			assert (o.Int(4) > o.Int(3)) == True
			assert (o.Int(4) >= 4) == True
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_list_operator_surface_uses_visible_value(cls):
		state = cls._patch_runtime()

		try:
			assert o.List([1, 2]) + [3] == [1, 2, 3]
			assert o.List([1, 2]) == o.List([1, 2])
		finally:
			cls._restore_runtime(state)

	# ----------------------------------------------------------------------
	@classmethod
	def test_object_like_entity_rejects_operator_path(cls):
		state = cls._patch_runtime()

		try:
			root_name          = os.path.basename(state['root'])
			OperatorObjectLike = o.T.extend(f'OperatorObjectLike_{root_name}', name=str)
			x                  = OperatorObjectLike(name='alex')
			raised             = False

			try:
				-x
			except TypeError:
				raised = True

			assert raised == True
		finally:
			cls._restore_runtime(state)


if __name__ == '__main__':
	TestOperators.run()
