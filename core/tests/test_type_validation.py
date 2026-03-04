import o


class a(): pass
class b(): pass
class c(): pass
class d(): pass
class e(): pass


class TestTypeValidation(o.Test):

	# ============================================================
	# STRUCTURAL SIGNATURE DIFFERENCES
	# ============================================================

	@classmethod
	def test_dict_key_value_swap(cls):
		t1 = o.Type(dict[a,b]).signature
		t2 = o.Type(dict[b,a]).signature
		assert t1 != t2


	@classmethod
	def test_list_inner_variation(cls):
		t1 = o.Type(list[a]).signature
		t2 = o.Type(list[b]).signature
		assert t1 != t2


	@classmethod
	def test_nested_list_vs_flat(cls):
		t1 = o.Type(list[list[a]]).signature
		t2 = o.Type(list[a]).signature
		assert t1 != t2


	@classmethod
	def test_dict_value_depth_difference(cls):
		t1 = o.Type(dict[a,list[b]]).signature
		t2 = o.Type(dict[a,b]).signature
		assert t1 != t2


	@classmethod
	def test_double_container_variation(cls):
		t1 = o.Type(list[dict[a,b]]).signature
		t2 = o.Type(dict[list[a],b]).signature
		assert t1 != t2


	@classmethod
	def test_deep_branch_difference(cls):
		t1 = o.Type(list[dict[a,list[b]]]).signature
		t2 = o.Type(list[dict[a,list[c]]]).signature
		assert t1 != t2


	@classmethod
	def test_same_depth_different_shape(cls):
		t1 = o.Type(list[dict[a,b]]).signature
		t2 = o.Type(list[list[dict[a,b]]]).signature
		assert t1 != t2


	@classmethod
	def test_empty_container_vs_typed(cls):
		t1 = o.Type(list).signature
		t2 = o.Type(list[a]).signature
		assert t1 != t2


	@classmethod
	def test_dict_vs_list_root(cls):
		t1 = o.Type(list[a]).signature
		t2 = o.Type(dict[a,b]).signature
		assert t1 != t2


	# ============================================================
	# PREFIX SEMANTICS ( actual in expected )
	# ============================================================

	@classmethod
	def test_prefix_simple(cls):
		expected = o.Type(list)
		actual   = o.Type(list[a])
		assert actual in expected


	@classmethod
	def test_prefix_deep(cls):
		expected = o.Type(list)
		actual   = o.Type(list[dict[a,b]])
		assert actual in expected


	@classmethod
	def test_prefix_chain(cls):
		expected = o.Type(list[list])
		actual   = o.Type(list[list[a]])
		assert actual in expected


	@classmethod
	def test_prefix_reverse(cls):
		expected = o.Type(list[a])
		actual   = o.Type(list)
		assert not (actual in expected)


	@classmethod
	def test_exact_match(cls):
		expected = o.Type(list[dict[a,b]])
		actual   = o.Type(list[dict[a,b]])
		assert actual in expected
		assert expected in actual


	@classmethod
	def test_different_root(cls):
		expected = o.Type(list[a])
		actual   = o.Type(dict[a,b])
		assert not (actual in expected)
		assert not (expected in actual)


	@classmethod
	def test_sibling_branches(cls):
		parent = o.Type(list)
		a1     = o.Type(list[a])
		b1     = o.Type(list[b])

		assert a1 in parent
		assert b1 in parent
		assert not (a1 in b1)
		assert not (b1 in a1)


	@classmethod
	def test_deep_incompatible(cls):
		expected = o.Type(list[dict[a,list[b]]])
		actual   = o.Type(list[dict[a,list[c]]])

		assert not (actual in expected)
		assert not (expected in actual)


	# ============================================================
	# STABILITY & DETERMINISM
	# ============================================================

	@classmethod
	def test_signature_determinism(cls):
		t1 = o.Type(list[dict[a,b]]).signature
		t2 = o.Type(list[dict[a,b]]).signature
		assert t1 == t2


	@classmethod
	def test_signature_independent_instances(cls):
		t1 = o.Type(list[dict[a,b]])
		t2 = o.Type(list[dict[a,b]])
		assert t1.signature == t2.signature


if __name__ == '__main__':
	TestTypeValidation.run()
	print('\nAll tests passed')