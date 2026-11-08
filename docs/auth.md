# Authorization service

`o.services.Auth` is available only after `o.start(tree_mode=True)`.
Both public methods raise `RuntimeError` when tree mode is disabled.

```python
import o

o.start(tree_mode=True)

auth   = o.services.Auth
parent = o.T()

auth.set(parent, 7, 'rw')
auth.can(7, parent, 'r')  # True
auth.can(8, parent, 'r')  # False
```

## Public API

- `Auth.set(node: o.T, client_id: int, permissions: str | None) -> None`:
  privileged server-side assignment. `client_id` is a stable integer
  identity assigned by the application. `permissions` is `'r'`, `'w'`,
  `'rw'`, `'wr'`, `''` (explicit denial), or `None` (remove a rule).
- `Auth.can(client_id: int, node: o.T, permission: str) -> bool`:
  check one right (`'r'` or `'w'`). An absent rule defaults to `False`.

Client identities are stored and compared as integers, with no conversion
or prefix. String IDs, O objects, floats, and booleans are rejected.

The nearest explicit rule for a client is authoritative for **both** rights,
including rights it omits. A rule `'w'` therefore denies read even when a
parent grants `'rw'`. An empty rule explicitly denies both. Deleting an
override restores inheritance.

Each rule is persisted in LMDB under the root-owned internal namespace
`o.V.__auth__`, keyed by node ID and then integer client ID. The Python
`o.V.__auth__` attribute returns a **detached snapshot** of that mapping,
not a live mutable policy collection. Policy metadata is not an O holding
edge, so it does not affect tree ownership. Tree ancestry is read from the
existing `tree/parents` index; Auth never reimplements cycle detection.

`set` is a **trusted administrative API**, not a self-authorizing operation:
the server must authenticate the caller and separately restrict who can
change rules. Never expose arbitrary calls to `Auth.set` or `o.V.__auth__`
through a client-facing endpoint. `can` must be enforced server-side on
actual reads and writes; a filtered JSON projection is not authorization.
