# test_schema.py

import o

# ----------------------------------------------------------------------
# DB setup
# ----------------------------------------------------------------------

o.Conf.DB_CONN = 'sqlite:///test.db'
o.Db.connect()
o.Db.drop_all_tables()


# ======================================================================
# Test schemas
# ======================================================================

class User(o.Schema):
	name = o.F(str)


class Post(o.Schema):
	title  = o.F(str)
	author = o.F(User, default=None)


# ======================================================================
# Tests
# ======================================================================

def test_schema_save_and_lazy_load():

	u = User(name='Alice')
	p = Post(title='Hello', author=u)

	p.save()

	assert u.id is not None
	assert p.id is not None

	# --------------------------------------
	# Load post (author is lazy ref)
	# --------------------------------------
	p2 = Post.load(p.id)

	# author is resolved on access
	assert isinstance(p2.author, User)
	assert u.__class__ is o.types.User
	assert p2.author.name == 'Alice'

	print('PASSED')


def test_ref_storage_format():

	u = User(name='Bob')
	p = Post(title='Hi', author=u)
	p.save()

	row = o.Db.get(Post.table_name, p.id)

	assert isinstance(row['author'], str)
	assert row['author'].startswith(o.Ref.prefix)


def test_partial_update():

	u = User(name='Alice')
	u.save()

	u.name = 'Alice Cooper'
	u.save()

	u2 = User.load(u.id)
	assert u2.name == 'Alice Cooper'


def test_nullable_reference():

	p = Post(title='Lonely', author=None)
	p.save()

	p2 = Post.load(p.id)
	assert p2.author is None


def test_shared_reference_identity():

	u = User(name='Eve')
	p1 = Post(title='A', author=u)
	p2 = Post(title='B', author=u)

	p1.save()
	p2.save()

	u2 = User.load(u.id)

	assert u2.name == 'Eve'

	# both posts point to same in-memory instance
	p1_loaded = Post.load(p1.id)
	p2_loaded = Post.load(p2.id)

	assert p1_loaded.author is p2_loaded.author
	assert p1_loaded.author is u2


def test_delete():

	u = User(name='Temp')
	u.save()

	uid = u.id
	u.delete()

	assert o.Db.get(User.table_name, uid) is None


# ======================================================================
# Runner
# ======================================================================

if __name__ == '__main__':

	test_schema_save_and_lazy_load()
	print('OK: save + lazy load')

	test_ref_storage_format()
	print('OK: ref storage format')

	test_partial_update()
	print('OK: partial update')

	test_nullable_reference()
	print('OK: nullable reference')

	test_shared_reference_identity()
	print('OK: shared reference identity')

	test_delete()
	print('OK: delete')

	print('\nALL SCHEMA TESTS PASSED')
