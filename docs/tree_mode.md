# Persistent tree mode

Choose the topology contract when creating an ontology database:

```python
import o

o.start(tree_mode=True)
```

The full startup signature is `o.start(path=None, sync=False, tree_mode=None)`.
`path` selects the LMDB ontology directory, and `sync` controls commit
durability. `tree_mode` accepts `True`, `False`, or `None`.

- On a new database, `None` or `False` creates **graph mode**.
  `True` creates **tree mode**.
- On an existing database, `None` loads the persisted mode.
- A conflicting explicit mode raises `ValueError` in `o.start()`
  before ontology classes or the root value are loaded.
- Legacy databases without a recorded mode are graph databases;
  opening one with `tree_mode=True` is rejected.
- The mode is recorded as `system/tree_mode` in LMDB and cached as
  `o.TREE_MODE`. Application code should treat it as read-only.
- `o.start()` returns `None`. As before, call it once during
  application startup, not repeatedly to change runtime mode.

In tree mode, every persistent holding edge has one parent. Edges
cannot create cycles, a child cannot occupy two slots (even in one
container), and `o.V` cannot be attached beneath another node.
The invariant also applies to disconnected subtrees. Dictionary keys
and dictionary values are both holding edges.

Move an object by unlinking it from its old parent before linking it
to a new parent. Reordering a list does not change ownership.
`drop()` of an attached instance is rejected until it is unlinked.
Direct writes to internal LMDB keys are outside the public object
mutation contract and must not be used to bypass these checks.

```python
o.start(tree_mode=True)

child = o.T()
parent = o.List([child])

del parent[0]
other = o.List([child])
```

Changing topology mode after database creation is unsupported in
either direction. To use another mode, create a separate database.
