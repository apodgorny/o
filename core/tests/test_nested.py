import o


class TestNested(o.Test):

	# --------------------------------------------------------------
	@classmethod
	def test_T_inside_T_unique(cls):

		class B1(o.T):
			x: int

		class A1(o.T):
			b: B1

		b = B1(x=10)
		a = A1(b=b)

		assert isinstance(a.b, B1)
		assert a.b.__class__ is B1
		assert a.b.x == 10


	# --------------------------------------------------------------
	@classmethod
	def test_list_of_T_unique(cls):

		class B2(o.T):
			x: int

		class A2(o.T):
			items: list[B2]

		b1 = B2(x=1)
		b2 = B2(x=2)

		a = A2(items=[b1, b2])

		assert len(a.items) == 2
		assert isinstance(a.items[0], B2)
		assert isinstance(a.items[1], B2)
		assert a.items[0].x == 1
		assert a.items[1].x == 2


	# --------------------------------------------------------------
	@classmethod
	def test_dict_of_T_unique(cls):

		class B3(o.T):
			x: int

		class A3(o.T):
			items: dict[str, B3]

		b1 = B3(x=5)
		b2 = B3(x=6)

		a = A3(items={"a": b1, "b": b2})

		assert isinstance(a.items["a"], B3)
		assert isinstance(a.items["b"], B3)
		assert a.items["a"].x == 5
		assert a.items["b"].x == 6


	# --------------------------------------------------------------
	@classmethod
	def test_deep_nesting_roundtrip_unique(cls):

		class B4(o.T):
			x: int

		class A4(o.T):
			items: dict[str, list[B4]]

		b1 = B4(x=7)
		b2 = B4(x=8)

		a = A4(items={"k": [b1, b2]})

		id_ = a.__id__
		a2  = A4.bind(id_)

		assert isinstance(a2.items["k"][0], B4)
		assert isinstance(a2.items["k"][1], B4)
		assert a2.items["k"][0].x == 7
		assert a2.items["k"][1].x == 8


	# --------------------------------------------------------------
	@classmethod
	def test_multiple_bind_consistency(cls):

		class B5(o.T):
			x: int

		class A5(o.T):
			b: B5

		b = B5(x=42)
		a = A5(b=b)

		id_ = a.__id__

		a2 = A5.bind(id_)
		a3 = A5.bind(id_)

		assert isinstance(a2.b, B5)
		assert isinstance(a3.b, B5)
		assert a2.b.x == 42
		assert a3.b.x == 42


	# --------------------------------------------------------------
	@classmethod
	def test_type_identity_stable(cls):

		class B6(o.T):
			x: int

		class A6(o.T):
			b: B6

		b = B6(x=99)
		a = A6(b=b)

		assert B6.__type_id__ == b.__class__.__type_id__
		assert a.b.__class__.__type_id__ == B6.__type_id__