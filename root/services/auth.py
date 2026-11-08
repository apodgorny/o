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
	def _get_client_key(self, client):
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
		if o.TREE_MODE:
			if isinstance(node, o.T):
				client_id = self._get_client_key(client)

				if permissions in (None, '', 'r', 'w', 'rw', 'wr'):
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
				else:
					raise ValueError('permissions must be r, w, rw, or empty')
			else:
				raise TypeError('node must be an O instance')
		else:
			raise RuntimeError('Auth requires tree mode')

	# Resolve the nearest explicit rule; missing rules deny access.
	# ----------------------------------------------------------------------
	def can(self, client, node, permission):
		if o.TREE_MODE:
			if isinstance(node, o.T):
				client_id = self._get_client_key(client)

				if permission in ('r', 'w'):
					node_id = node.id
					allowed = False

					with o.services.Memory.read() as memory:
						while node_id is not None:
							rules = memory.get(f'{o.V.__proto__}.__auth__/{node_id}', {})

							if client_id in rules:
								allowed = permission in rules[client_id]
								break

							node_id = memory.get(f'tree/parents/{node_id}', None)
				else:
					raise ValueError('permission must be r or w')
			else:
				raise TypeError('node must be an O instance')
		else:
			raise RuntimeError('Auth requires tree mode')

		return allowed
