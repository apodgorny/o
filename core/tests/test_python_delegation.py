import o


class TestPythonDelegation(o.Test):

	# ======================================================================
	# LIST
	# ======================================================================

	# In-place python list mutations must persist
	# ----------------------------------------------------------------------
	@classmethod
	def test_list_inplace_methods(cls):
		l = o.List()

		l.append(3)
		l.append(1)
		l.append(2)

		l.sort()

		print(l)

		assert l[0] == 1
		assert l[1] == 2
		assert l[2] == 3

		l.reverse()

		assert l[0] == 3
		assert l[2] == 1


	# Methods returning values must work without altering storage
	# ----------------------------------------------------------------------
	@classmethod
	def test_list_non_inplace_methods(cls):
		l = o.List()

		l.append(1)
		l.append(2)
		l.append(2)

		assert l.count(2) == 2
		assert l.index(1) == 0
		assert len(l) == 3


	# Python slicing should return python object and not corrupt storage
	# ----------------------------------------------------------------------
	@classmethod
	def test_list_slice(cls):
		l = o.List()

		l.append(1)
		l.append(2)
		l.append(3)

		s = l[:2]

		assert s == [1, 2]
		assert len(l) == 3


	# ======================================================================
	# DICT
	# ======================================================================

	# In-place python dict mutations must persist
	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_inplace_methods(cls):
		d = o.Dict()

		d['a'] = 1
		d['b'] = 2

		d.update({'c': 3})

		assert d['c'] == 3

		d.pop('b')

		assert 'b' not in d


	# Non-mutating dict methods
	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_non_inplace_methods(cls):
		d = o.Dict()

		d['a'] = 1
		d['b'] = 2

		keys = d.keys()
		values = d.values()

		assert 'a' in keys
		assert 2 in values


	# Ensure python dict get works
	# ----------------------------------------------------------------------
	@classmethod
	def test_dict_get(cls):
		d = o.Dict()

		d['x'] = 10

		assert d.get('x') == 10
		assert d.get('y', 5) == 5


	# ======================================================================
	# OBJECT (node-like API)
	# ======================================================================

	# Object should allow attribute-style updates
	# ----------------------------------------------------------------------
	@classmethod
	def test_object_attribute_mutation(cls):
		n = o.Object()

		n.a = 1
		n.b = 2

		assert n.a == 1
		assert n.b == 2


	# Object dictionary-like update via python methods
	# ----------------------------------------------------------------------
	@classmethod
	def test_object_update(cls):
		n = o.Object()

		n.update({'a': 1, 'b': 2})

		assert n.a == 1
		assert n.b == 2


	# Ensure object non-mutating access works
	# ----------------------------------------------------------------------
	@classmethod
	def test_object_keys_values(cls):
		n = o.Object()

		n.a = 1
		n.b = 2

		keys = n.keys()
		values = n.values()

		assert 'a' in keys
		assert 2 in values

	@classmethod
	def test_object_key_length_limit_32(cls):
		n = o.Object()

		try:
			setattr(n, 'x' * 33, 1)
			assert False
		except ValueError:
			pass

	@classmethod
	def test_object_key_must_be_property_compatible(cls):
		n = o.Object()

		for bad in ('a b', 'a-b', '1abc'):
			try:
				setattr(n, bad, 1)
				assert False
			except ValueError:
				pass


	# ======================================================================
	# MIXED EDGE CASES
	# ======================================================================

	# Ensure mutation through delegated python call persists
	# ----------------------------------------------------------------------
	@classmethod
	def test_nested_list_mutation(cls):
		l = o.List()

		l.append([3,1,2])

		l[0].sort()

		assert l[0] == [1,2,3]


	# Ensure chained python operations behave correctly
	# ----------------------------------------------------------------------
	@classmethod
	def test_list_chained_calls(cls):
		l = o.List()

		l.append(5)
		l.append(3)
		l.append(4)

		l.sort()
		l.reverse()

		assert list(l) == [5,4,3]
