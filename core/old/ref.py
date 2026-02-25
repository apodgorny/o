# ======================================================================
# o.Ref
#
#  Why isn't (class, id) keys in o.__schema_instances__ sufficient?
#  The key (User, id) doesn't exist while id is None.
#  And this scenario is legal and fundamental:
#
#     u = User(name='Alice') # <--- id = None
#     p = Post(title='Hello', author=u)
#
#  We DON'T want to:
#  – force u.save()
#  - pollute the database for the sake of composition
#  - change the semantics of construction
# 
#   REFERENCING:
#   ---------------------------------------------------------------------------------------
#   #  Time     | Where                 | Action
#   ---------------------------------------------------------------------------------------
#   1. Creation | o.Schema.__init__     | turn attached models to mem refs      +
#   2. Setter   | o.Schema.__setattr__  | turn model being set into mem ref     +
#   3. Saving   | o.Schema.save         | turn all mem refs to db refs and save +
#   ---------------------------------------------------------------------------------------
# 
#   DE-REFERENCING:
#   ---------------------------------------------------------------------------------------
#   #  Time     | Where                 | Action
#   ---------------------------------------------------------------------------------------
#   1. Getter   | o.Schema.__getattr__  | if db ref in leaf, resolve to object, replace ref to mem +
#   2. Load     | o.Schema._load        | load with refs from db, leave db refs until accessed +
#   ---------------------------------------------------------------------------------------
# ======================================================================

import json

import o


class Ref(o.Module):
	prefix = '__o.Ref__'

	# Serialize to json
	# ----------------------------------------------------------------------
	@classmethod
	def reference(cls, schema, persistent):
		if not isinstance(schema, o.Schema):
			raise ValueError('Only o.Schema instances support referencing')

		schema_id = schema.id if persistent else schema.__instance_id__

		ref = dict(
			id   = schema_id,
			cls  = schema.__class__.__name__,
			p    = persistent
		)

		return cls.prefix + json.dumps(ref)

	# Unserialize from json
	# ----------------------------------------------------------------------
	@classmethod
	def dereference(cls, val):
		if not cls.is_reference(val):
			raise ValueError(f'Invalid reference `{val}`')

		val        = val[len(cls.prefix):]
		ref        = json.loads(val)
		persistent = ref['p']
		schema_cls = o.types[ref['cls']]

		if persistent:
			instance = schema_cls.load(ref['id'])
		else:
			instance = o.__cache_by_instance_id__[ref['cls']][ref['id']]

		return instance

	# Is string a valid reference?
	# ----------------------------------------------------------------------
	@classmethod
	def is_reference(cls, val):
		return isinstance(val, str) and val.startswith(cls.prefix)