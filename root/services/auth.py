# ==============================================================================
# AUTH SERVICE
# ==============================================================================
# Assign and check inherited access rights in persistent tree ontologies.
# ==============================================================================

import o


class Auth(o.Service):

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Assign or remove a client's explicit rights on a tree node.
	# Only trusted server code may call this method.
	# ----------------------------------------------------------------------
	def set(self, node, client, permissions):
		if not o.TREE_MODE:
			raise RuntimeError('Auth requires tree mode')

		if not isinstance(node, o.T):
			raise TypeError('node must be an O instance')

		if not isinstance(client, (o.T, str)) or isinstance(client, str) and not client:
			raise TypeError('client must be an O instance or a nonempty string')

		if permissions is not None and (not isinstance(permissions, str) or any(char not in 'rw' for char in permissions) or len(set(permissions)) != len(permissions)):
			raise ValueError('permissions must be r, w, rw, an empty denial, or None to remove')

		client_id = f'entity:{client.id}' if isinstance(client, o.T) else f'name:{client}'
		key       = f'{o.V.__proto__}.__auth__/{node.id}'

		with o.services.Memory.write() as memory:
			rules = memory.get(key, {})

			if permissions is None:
				rules.pop(client_id, None)
			else:
				rules[client_id] = permissions

			if rules:
				memory.set(key, rules)
			else:
				memory.unset(key)

	# Resolve the nearest explicit rule, denying access if none exists.
	# ----------------------------------------------------------------------
	def can(self, client, node, permission):
		if not o.TREE_MODE:
			raise RuntimeError('Auth requires tree mode')

		if not isinstance(node, o.T):
			raise TypeError('node must be an O instance')

		if not isinstance(client, (o.T, str)) or isinstance(client, str) and not client:
			raise TypeError('client must be an O instance or a nonempty string')

		if permission not in ('r', 'w'):
			raise ValueError('permission must be r or w')

		client_id = f'entity:{client.id}' if isinstance(client, o.T) else f'name:{client}'
		node_id   = node.id
		allowed   = False

		with o.services.Memory.read() as memory:
			while node_id is not None:
				rules = memory.get(f'{o.V.__proto__}.__auth__/{node_id}', {})

				if client_id in rules:
					allowed = permission in rules[client_id]
					break

				node_id = memory.get(f'tree/parents/{node_id}', None)

		return allowed
