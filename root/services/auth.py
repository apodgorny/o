# ==============================================================================
# AUTH SERVICE
# ==============================================================================
# Assign and check inherited access rights in persistent tree ontologies.
# ==============================================================================

import o


class Auth(o.Service):

	# ======================================================================
	# PRIVATE METHODS
	# ======================================================================

	# Identify clients without retaining O objects in authorization records.
	# ----------------------------------------------------------------------
	def _client_key(self, client):
		if isinstance(client, o.T):
			key = f'entity:{client.id}'
		elif isinstance(client, str) and client:
			key = f'name:{client}'
		else:
			raise TypeError('client must be an O instance or a nonempty string')

		return key

	# ======================================================================
	# PUBLIC METHODS
	# ======================================================================

	# Assign explicit rights for a client, or remove the rule with None.
	# Only trusted server code may change authorization policies.
	# ----------------------------------------------------------------------
	def set(self, node, client, permissions):
		if not o.TREE_MODE:
			raise RuntimeError('Auth requires tree mode')

		if not isinstance(node, o.T):
			raise TypeError('node must be an O instance')

		client_id = self._client_key(client)

		if permissions is not None:
			if not isinstance(permissions, str):
				raise ValueError('permissions must be r, w, rw, or empty')

			if len(set(permissions)) != len(permissions):
				raise ValueError('permissions cannot contain duplicates')

			if any(right not in 'rw' for right in permissions):
				raise ValueError('permissions must contain only r and w')

		key = f'{o.V.__proto__}.__auth__/{node.id}'

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

	# Resolve the nearest explicit rule; missing rules deny access.
	# ----------------------------------------------------------------------
	def can(self, client, node, permission):
		if not o.TREE_MODE:
			raise RuntimeError('Auth requires tree mode')

		if not isinstance(node, o.T):
			raise TypeError('node must be an O instance')

		client_id = self._client_key(client)

		if permission not in ('r', 'w'):
			raise ValueError('permission must be r or w')

		node_id = node.id
		allowed = False

		with o.services.Memory.read() as memory:
			while node_id is not None:
				rules = memory.get(f'{o.V.__proto__}.__auth__/{node_id}', {})

				if client_id in rules:
					allowed = permission in rules[client_id]
					break

				node_id = memory.get(f'tree/parents/{node_id}', None)

		return allowed
