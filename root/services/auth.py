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

	# Assign explicit rights for an integer client ID, or remove the rule.
	# Only trusted server code may change authorization policies.
	# ----------------------------------------------------------------------
	def set(self, node: o.T, client_id: int, permissions: str | None) -> None:
		if o.TREE_MODE:
			if isinstance(node, o.T):
				if type(client_id) is int:
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
					raise TypeError('client_id must be int')
			else:
				raise TypeError('node must be an O instance')
		else:
			raise RuntimeError('Auth requires tree mode')

	# Resolve the nearest explicit rule; missing rules deny access.
	# ----------------------------------------------------------------------
	def can(self, client_id: int, node: o.T, permission: str) -> bool:
		if o.TREE_MODE:
			if isinstance(node, o.T):
				if type(client_id) is int:
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
					raise TypeError('client_id must be int')
			else:
				raise TypeError('node must be an O instance')
		else:
			raise RuntimeError('Auth requires tree mode')

		return allowed
