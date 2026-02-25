# ======================================================================
# Schema + Field smoke tests (new model)
# ======================================================================

import o


# ----------------------------------------------------------------------
# Schema with explicit o.F / o.T usage (NO annotations)
# ----------------------------------------------------------------------

class User(o.BaseSchema):
	name = o.F(str, description='User name')
	age  = o.F(int, default=0)
	note = o.F(str)

# ----------------------------------------------------------------------
# Test: field defaults & requiredness
# ----------------------------------------------------------------------

print(
	User.fields['note'].default,
	User.fields['note'].is_required()
)

assert User.fields['note'].default is None
assert User.fields['note'].is_required() is False


# ----------------------------------------------------------------------
# Test: construction and defaults
# ----------------------------------------------------------------------

u = User(name='Alice')

print('u.note =', u.note, type(u.note))

assert u.name == 'Alice'
assert u.age  == 0
assert u.note is None


# ----------------------------------------------------------------------
# Test: Field metadata preserved
# ----------------------------------------------------------------------

f_name = User.fields['name']
assert f_name.description == 'User name'


# ----------------------------------------------------------------------
# Test: dict-style access
# ----------------------------------------------------------------------

assert u['name'] == 'Alice'
u['age'] = 42
assert u.age == 42


# ----------------------------------------------------------------------
# Test: attribute access symmetry
# ----------------------------------------------------------------------

u.note = 'hello'
assert u['note'] == 'hello'


# ----------------------------------------------------------------------
# Test: to_dict / to_json
# ----------------------------------------------------------------------

d = u.to_dict()
assert d == {
	'name' : 'Alice',
	'age'  : 42,
	'note' : 'hello',
}

j = u.to_json()
assert '"name"' in j and '"Alice"' in j


# ----------------------------------------------------------------------
# Test: clone (no id, no persistence)
# ----------------------------------------------------------------------

u2 = u.clone()
assert u2 is not u
assert u2.to_dict() == u.to_dict()


# ----------------------------------------------------------------------
# Test: dynamic schema + o.F
# ----------------------------------------------------------------------

Post = o.BaseSchema.define(
	'Post',
	title = o.F(str, description='Post title'),
	views = o.F(int, default=0),
)

p = Post(title='Hello')

assert p.title == 'Hello'
assert p.views == 0


# ----------------------------------------------------------------------
# Test: validation error path
# ----------------------------------------------------------------------

try:
	User(name='Bob', age='wrong')
	raise RuntimeError('ValidationError not raised')
except Exception as e:
	msg = str(e)
	assert 'age' in msg


print('Schema + Field smoke tests: OK')
