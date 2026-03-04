import o


class TestT(o.Test):

	# ============================================================
	# BASIC FIELD INITIALIZATION
	# ============================================================

	@classmethod
	def test_simple_field(cls):
		class T_Simple(o.T):
			x: int

		a = T_Simple(x=10)

		assert isinstance(a, T_Simple)
		assert a.x == 10


	@classmethod
	def test_required_field_missing(cls):
		class T_Required(o.T):
			x: int

		try:
			T_Required()
			assert False
		except TypeError:
			pass


	@classmethod
	def test_optional_with_default(cls):
		class T_Default(o.T):
			x: int = 5

		a = T_Default()

		assert isinstance(a, T_Default)
		assert a.x == 5


	@classmethod
	def test_optional_none(cls):
		class T_None(o.T):
			x: int = None

		a = T_None(x=None)

		assert isinstance(a, T_None)
		assert a.x is None


	# ============================================================
	# TYPE VALIDATION
	# ============================================================

	@classmethod
	def test_type_mismatch(cls):
		class T_TypeMismatch(o.T):
			x: int

		try:
			T_TypeMismatch(x='hello')
			assert False
		except TypeError:
			pass


	@classmethod
	def test_nested_list(cls):
		class T_List(o.T):
			x: list[int]

		a = T_List(x=[1, 2, 3])

		assert isinstance(a, T_List)
		assert a.x == [1, 2, 3]


	@classmethod
	def test_nested_list_type_error(cls):
		class T_ListError(o.T):
			x: list[int]

		try:
			T_ListError(x=[1, 'a'])
			assert False
		except TypeError:
			pass


	@classmethod
	def test_dict_validation(cls):
		class T_Dict(o.T):
			x: dict[int, str]

		a = T_Dict(x={1: 'a'})

		assert isinstance(a, T_Dict)
		assert a.x == {1: 'a'}


	@classmethod
	def test_dict_type_error(cls):
		class T_DictError(o.T):
			x: dict[int, str]

		try:
			T_DictError(x={'a': 1})
			assert False
		except TypeError:
			pass


	# ============================================================
	# INHERITANCE
	# ============================================================

	@classmethod
	def test_inheritance_fields(cls):
		class T_Base(o.T):
			x: int

		class T_Child(T_Base):
			y: str

		b = T_Child(x=1, y='a')

		assert isinstance(b, T_Child)
		assert b.x == 1
		assert b.y == 'a'


	@classmethod
	def test_inheritance_missing_parent_field(cls):
		class T_Base2(o.T):
			x: int

		class T_Child2(T_Base2):
			y: str

		try:
			T_Child2(y='a')
			assert False
		except TypeError:
			pass


	# ============================================================
	# DEFINE WITH o.F
	# ============================================================

	@classmethod
	def test_define_with_oF(cls):

		T_Def1 = o.T.define(
			'T_Def1',
			x=o.F(int),
			y=o.F(str, default='ok')
		)

		a = T_Def1(x=10)

		assert a.x == 10
		assert a.y == 'ok'


	@classmethod
	def test_define_with_annotations(cls):

		T_Def2 = o.T.define(
			'T_Def2',
			x=o.F(int),
			y=o.F(list[int])
		)

		a = T_Def2(x=5, y=[1, 2])

		assert a.x == 5
		assert a.y == [1, 2]


	@classmethod
	def test_define_mixed(cls):

		T_Def3 = o.T.define(
			'T_Def3',
			x=o.F(int),
			y=o.F(list[int], default=[1])
		)

		a = T_Def3(x=7)

		assert a.x == 7
		assert a.y == [1]


	# ============================================================
	# CLASS DEFINITIONS
	# ============================================================

	@classmethod
	def test_class_with_oF(cls):

		class T_ClassF(o.T):
			x = o.F(int)
			y = o.F(str, default='z')

		a = T_ClassF(x=3)

		assert a.x == 3
		assert a.y == 'z'


	@classmethod
	def test_class_with_annotations(cls):

		class T_ClassAnn(o.T):
			x: int
			y: list[int]

		a = T_ClassAnn(x=1, y=[2, 3])

		assert a.x == 1
		assert a.y == [2, 3]


	@classmethod
	def test_class_mixed(cls):

		class T_ClassMixed(o.T):
			x: int
			y = o.F(list[int], default=[9])

		a = T_ClassMixed(x=4)

		assert a.x == 4
		assert a.y == [9]


	# ============================================================
	# SHAPE EQUALITY
	# ============================================================

	@classmethod
	def test_define_vs_class_field_shape(cls):

		T_Shape1 = o.T.define(
			'T_Shape1',
			x=o.F(int),
			y=o.F(list[int], default=[1])
		)

		class T_Shape2(o.T):
			x = o.F(int)
			y = o.F(list[int], default=[1])

		assert set(T_Shape1.__fields__.keys()) == set(T_Shape2.__fields__.keys())

		for k in T_Shape1.__fields__:
			f1 = T_Shape1.__fields__[k]
			f2 = T_Shape2.__fields__[k]

			assert f1.type.signature == f2.type.signature
			assert f1.is_optional == f2.is_optional


	# ============================================================
	# DEFAULT ISOLATION
	# ============================================================

	@classmethod
	def test_default_composite_not_shared(cls):

		class T_DefaultList(o.T):
			x = o.F(list[int], default=[1])

		a = T_DefaultList()
		b = T_DefaultList()

		a.x.append(2)

		assert a.x == [1, 2]
		assert b.x == [1]


	# ============================================================
	# UNKNOWN FIELD
	# ============================================================

	@classmethod
	def test_unknown_field_raises(cls):

		class T_Unknown(o.T):
			x: int

		try:
			T_Unknown(x=1, y=2)
			assert False
		except TypeError:
			pass


	# ============================================================
	# FIELD OVERRIDE
	# ============================================================

	@classmethod
	def test_field_override(cls):

		class T_BaseOverride(o.T):
			x: int

		class T_ChildOverride(T_BaseOverride):
			x: str

		c = T_ChildOverride(x='a')

		assert c.x == 'a'


	# ============================================================
	# OPTIONAL ABSENT VS NONE
	# ============================================================

	@classmethod
	def test_optional_absent_vs_none(cls):

		class T_Optional(o.T):
			x = o.F(int, default=None)

		a1 = T_Optional()
		a2 = T_Optional(x=None)

		assert a1.x is None
		assert a2.x is None


	# ============================================================
	# DICT KEY & VALUE VALIDATION
	# ============================================================

	@classmethod
	def test_dict_key_and_value_validation(cls):

		class T_DictKV(o.T):
			x: dict[int, str]

		try:
			T_DictKV(x={'a': 'ok'})
			assert False
		except TypeError:
			pass

		try:
			T_DictKV(x={1: 2})
			assert False
		except TypeError:
			pass


	# ============================================================
	# WRAPPED OBJECT INPUT
	# ============================================================

	@classmethod
	def test_wrapped_object_input(cls):

		class T_Wrapped(o.T):
			x: o.List

		a = T_Wrapped(x=o.List([1, 2]))

		assert a.x == [1, 2]


	# ============================================================
	# PERSISTENCE ROUNDTRIP
	# ============================================================

	@classmethod
	def test_persistence_roundtrip(cls):

		class T_Persist(o.T):
			x: int

		a = T_Persist(x=42)

		id_ = a.__id__

		a2 = T_Persist.bind(id_)

		assert a2.x == 42


if __name__ == '__main__':
	TestT.run()
	print('\nAll tests passed')