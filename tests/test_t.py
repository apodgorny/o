# ======================================================================
# test_t.py
# ======================================================================

import o

o.Conf.DB_CONN = 'sqlite:///test.db'
o.Db.connect()
o.Db.drop_all_tables()


# ======================================================================
# TYPE CREATION (via o.T.define)
# ======================================================================

User = o.T.define(
	'User',
	name = str,
)

Post = o.T.define(
	'Post',
	title  = str,
	author = User,
)


# ======================================================================
# TESTS
# ======================================================================

def test_t_registry():
	assert 'User' in o.T
	assert 'Post' in o.T
	assert 'Foo' not in o.T


def test_t_type_identity():
	# o.T returns the actual schema class
	assert o.T.User is User
	assert isinstance(User, type)


def test_t_schema_is_class():
	# Schema types behave like classes, not proxies
	assert hasattr(User, '__getitem__')
	assert hasattr(User, '__contains__')
	assert callable(User)


def test_t_create_and_load_by_id():
	print('=' * 70)
	print('START test_t_create_and_load_by_id')

	u = User(name='Alice').save()
	assert u.id is not None

	u2 = o.T.User[u.id]
	assert isinstance(u2, User)
	assert u2.id == u.id
	assert u2.name == 'Alice'


def test_t_create_and_load_by_key_via_getitem():
	print('=' * 70)
	print('START test_t_create_and_load_by_key_via_getitem')

	u = User(key='alice', name='Alice').save()
	assert u.key == 'alice'

	assert 'alice' in o.T.User

	u2 = o.T.User['alice']
	assert isinstance(u2, User)
	assert u2.name == 'Alice'


def test_t_create_and_load_by_key_via_attribute():
	print('=' * 70)
	print('START test_t_create_and_load_by_key_via_attribute')

	u = User(key='bob', name='Bob').save()
	assert u.key == 'bob'

	u2 = o.T.User['bob']
	assert isinstance(u2, User)
	assert u2.name == 'Bob'


def test_t_missing_key():
	assert 'missing' not in o.T.User

	try:
		_ = o.T.User.missing
		assert False, 'Expected AttributeError'
	except AttributeError:
		pass


def test_t_post_with_recursive_load():
	u = User(name='Dave').save()
	p = Post(title='Hi', author=u).save()

	p2 = Post.load(p.id)
	assert isinstance(p2.author, User)
	assert p2.author.name == 'Dave'


def test_t_ref_storage_format():
	u = User(name='Eve').save()
	p = Post(title='X', author=u).save()

	row = o.Db.get('post', p.id)
	assert isinstance(row['author'], str)
	assert row['author'].startswith(o.Ref.prefix)


def test_t_recursive_cycle_safety():
	u = User(name='Eve').save()
	p1 = Post(title='A', author=u).save()
	p2 = Post(title='B', author=u).save()

	u2 = User.load(u.id)
	assert u2 is u              # главное
	assert u2.name == 'Eve'     # вторично


def test_t_delete():
	u = User(name='Temp').save()
	id_ = u.id

	ok = u.delete()
	assert ok is True
	assert o.Db.get('user', id_) is None


# ======================================================================
# NEW TESTS — ARCHITECTURE INVARIANTS
# ======================================================================

def test_t_class_singleton_identity():
	# Loading never produces a different class
	u = User(name='Zed').save()
	u2 = User.load(u.id)

	assert u.__class__ is User
	assert u2.__class__ is User


def test_t_call_instantiates():
	u = o.T.User(name='CallStyle').save()
	assert isinstance(u, User)
	assert u.name == 'CallStyle'


# ======================================================================
# CALLER
# ======================================================================

if __name__ == '__main__':
	print('--- test_t.py ---')

	test_t_registry()
	print('OK: registry')

	test_t_type_identity()
	print('OK: type identity')

	test_t_schema_is_class()
	print('OK: schema is class')

	test_t_create_and_load_by_id()
	print('OK: load by id')

	test_t_create_and_load_by_key_via_getitem()
	print('OK: load by key via []')

	test_t_create_and_load_by_key_via_attribute()
	print('OK: load by key via .attr')

	test_t_missing_key()
	print('OK: missing key')

	test_t_post_with_recursive_load()
	print('OK: recursive load')

	test_t_ref_storage_format()
	print('OK: ref storage')

	test_t_recursive_cycle_safety()
	print('OK: recursive safety')

	test_t_delete()
	print('OK: delete')

	test_t_class_singleton_identity()
	print('OK: class identity')

	test_t_call_instantiates()
	print('OK: call instantiates')

	print('ALL TESTS PASSED')
