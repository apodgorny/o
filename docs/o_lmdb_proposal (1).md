# o + LMDB Proposal

## Purpose

Use LMDB as the persistence engine for `o`, while keeping `o` as the semantic and object model.

```text
o      = identity + laws + schema + behavior model
LMDB   = fast persistent key/value substrate
Python = authoring language
```

LMDB must not define the ontology.
`o` defines what exists.
LMDB remembers it quickly.

---

## Core Separation

```text
Source Layer      : Python classes under o.root
Model Layer       : o classes / instances / fields / refs
Storage Layer     : LMDB
Projection Layer  : Python runtime / UI / JSON / GML / other outputs
```

LMDB is infrastructure only.
`o` remains canonical semantics.

---

## Canonical Identity

Use existing `o` identity law.

```text
__proto__ = canonical path string
```

Examples:

```text
o.T.User
o.T.User._0
o.T.User._0.__attributes__.name
o.T.User.__fields__.age
```

LMDB keys are derived from `__proto__` or exact structural path.

---

## Primary Storage Shape

```text
key   = path / __proto__ / expath
value = serialized node bytes
```

Recommended serialization:

```text
MessagePack  : normal compact mode
JSON         : debug / readable mode
custom bytes : later hot path if needed
```

The main point: do not store the whole class or whole universe as one blob.
Use one addressable node per record.

---

## Node Uniformity Law

Classes and instances use the same storage mechanism.

```text
put(key, node)
get(key)
delete(key)
scan(prefix)
```

Only semantics differ.

Example class node:

```python
{
	'kind': 'class',
	'proto': 'o.T.User',
	'bases': ['o.T'],
	'fields': ['name', 'age'],
}
```

Example instance node:

```python
{
	'kind': 'instance',
	'proto': 'o.T.User._0',
	'class': 'o.T.User',
	'attributes': {
		'name': 'Alexander',
		'age': 42,
	},
}
```

Core symmetry:

```text
class node    = entity node
instance node = entity node
```

Storage does not need separate worlds for class and instance.

---

## Suggested Key Layout

```text
o.T.User
o.T.User.__fields__.name
o.T.User.__fields__.age
o.T.User.__instances__._0
o.T.User.__instances__._0.__attributes__.name
o.T.User.__instances__._0.__attributes__.age
```

This keeps subtree reads simple with prefix scans.

---

## Read Patterns

Read one node:

```text
get('o.T.User')
```

Read subtree:

```text
scan(prefix='o.T.User')
```

Read instance only:

```text
get('o.T.User.__instances__._0')
```

Read one attribute:

```text
get('o.T.User.__instances__._0.__attributes__.age')
```

---

## Fluent Cursor Interface

Keep the beautiful old `_` accessor idea, but implement it over LMDB records instead of CST/source files.

Core expectation:

```text
dot access moves cursor
set replaces current value
missing target raises
```

Examples:

```python
o.T.User._.fields.first_name.props.default.set('bar')
obj._.attributes.first_name.set('Alexander')
```

The cursor keeps:

```text
env / db handle
current key
current node
route / breadcrumbs to root
```

Each `.` step extends the LMDB key path and loads the addressed node lazily.

```text
cursor.fields.first_name
→ key = o.T.User.__fields__.first_name
```

Each `set()` serializes and writes the current node or property back to LMDB.

```text
cursor.set(value)
→ txn.put(current_key, serialize(value))
```

No CST tree is involved.
No source rewrite is involved.
The accessor language remains, but the embodiment is LMDB.

---

## Unified Cursor Law

One structural accessor model should cover classes, instances, fields, attributes, refs, and projections.

```text
Class._    -> cursor rooted at class proto
Instance._ -> cursor rooted at instance proto
```

Same semantics, same storage backend.

Examples:

```python
o.T.User._.fields.age.get()
o.T.User._.fields.age.annotation.set('int')
user._.attributes.name.set('Alexander')
```

The cursor is not a manager family.
It is one generic route object over the node store.

---

## Cursor Reference Hops

References are natural traversal doors.

If a node value contains a reference:

```text
ref = o.T.Address.__instances__._12
```

then traversal may continue through the referenced target:

```text
see ref value
resolve target key
swap cursor root/current key
continue remaining route
```

This preserves the old parser proposal's ref-hop idea, but implemented as LMDB key resolution.

---

## Why This Shrinks Code

The old proposal expected the parser model to replace many specialized pieces:

```text
field managers
attribute managers
list managers
dict managers
wrapper classes
sync glue
```

The LMDB version keeps that simplification:

```text
one cursor
one traversal law
one set law
one ref-hop law
one serializer
one LMDB backend
```

Specialized behavior belongs to node semantics, not to separate storage managers.

---

## Memory Model

Old idea:

```text
disk holds full body
memory holds current cursor + tiny slice + offsets
```

LMDB version:

```text
LMDB holds full node tree
memory holds current cursor + decoded current node
```

No duplicated in-memory truth is required.
Only the active node or subtree is decoded.

---

## JSON / Schema Projections

The fluent cursor can expose projections without changing storage.

```text
json       = value projection
jsonschema = type/law projection
GML        = representation projection
```

Class field properties can project into JSON Schema.
Instances can project into JSON.
Screen nodes can project into GML or partial patches.

---

## Write Patterns

Update class metadata:

```text
put('o.T.User', serialized_node)
```

Update one field metadata:

```text
put('o.T.User.__fields__.age', serialized_node)
```

Update one instance attribute:

```text
put('o.T.User.__instances__._0.__attributes__.age', serialized_node)
```

This avoids rewriting the whole class or whole file.

---

## Source Cache Model

Python source remains the authoring layer.
LMDB stores the compiled semantic form.

```text
Python source -> o model -> serialized nodes -> LMDB
```

On load:

```text
if source_version unchanged:
	load from LMDB
else:
	rebuild affected nodes from source
	refresh LMDB
	load from LMDB
```

Version signals:

```text
content hash  : preferred
mtime + size  : fallback
```

Suggested version key:

```text
o.T.User.__version__
```

Suggested value:

```text
hash(source_file + relevant class block)
```

---

## Why LMDB Fits o

LMDB gives the storage properties that match `o`:

```text
memory mapped reads
ordered keys
prefix-friendly traversal
ACID transactions
many readers
embedded library, no server
simple deployment
fast local persistence
```

The single-writer property is acceptable for the current `o` shape because `o` is not primarily a high-concurrency multi-writer firehose.

---

## Multi-DB Layout

Use named databases if useful:

```text
nodes
meta
refs
vectors
cache
```

Possible meanings:

```text
nodes   : canonical serialized o nodes
meta    : versions, schema hashes, source hashes
refs    : forward / reverse references
vectors : embeddings by node path
cache   : derived projections
```

Keep the first version minimal. `nodes` and `meta` may be enough.

---

## References / Identity Law

References should be stored by canonical proto or stable ids.

```text
node -> referenced proto list
```

This enables:

```text
GC
dependency graph
reverse lookup
partial invalidation
projection refresh
```

Do not let LMDB keys replace `o` identity.
LMDB keys are storage addresses.
`__proto__` remains canonical identity.

---

## Future Vector Integration

Optional database:

```text
vectors
```

Example key:

```text
o.T.User.__fields__.bio
```

Example value:

```text
embedding bytes
```

This allows semantic lookup at node level without changing the core node store.

---

## UI / Tree Projection Synergy

The same stored tree can project to:

```text
Python runtime objects
JSON
GML
HTML
partial screen patches
agent prompts
```

Storage stays the same.
Projection changes.

---

## GML / Screen Model Connection

A tag can be an `o` class or instance expressed as markup.

```text
Tag = Container Instance
Tag = Type + Attributes + Container Zone
```

Screen generation flow:

```text
plan what to present
divide screen into zones
map zones onto screen
choose items for each zone
generate representation detail
stop when detailed enough
traverse tree
produce markup / patch / pixels
```

Events:

```text
user event bubbles upward
root receives semantic prompt
tree regenerates partly or fully
response patches screen by expath
```

Browser role:

```text
browser = graphics renderer + event source
server  = prompt -> response / tree patch
```

---

## Patch Model

Every node should have stable address notation.

```text
Patch = expath + representation + mode
```

Possible modes:

```text
replace
merge
remove
animate
raster_update
```

This allows responses at different granularities:

```text
whole screen
subtree
single node
attribute
layout region
pixels
```

---

## Minimal Python Sketch

```python
import lmdb
import msgpack


class Store:

	def __init__(self, path):
		self.env = lmdb.open(
			path,
			map_size=1024 * 1024 * 1024,
			max_dbs=8,
		)
		self.nodes = self.env.open_db(b'nodes')

	def put(self, key, node):
		key_bytes   = key.encode()
		value_bytes = msgpack.packb(node, use_bin_type=True)

		with self.env.begin(write=True, db=self.nodes) as txn:
			txn.put(key_bytes, value_bytes)

	def get(self, key):
		node      = None
		key_bytes = key.encode()

		with self.env.begin(db=self.nodes) as txn:
			value_bytes = txn.get(key_bytes)
			if value_bytes is not None:
				node = msgpack.unpackb(value_bytes, raw=False)

		return node

	def scan(self, prefix):
		nodes        = {}
		prefix_bytes = prefix.encode()

		with self.env.begin(db=self.nodes) as txn:
			cursor = txn.cursor()
			cursor.set_range(prefix_bytes)

			for key_bytes, value_bytes in cursor:
				if not key_bytes.startswith(prefix_bytes):
					break

				key = key_bytes.decode()
				nodes[key] = msgpack.unpackb(value_bytes, raw=False)

		return nodes
```

Example use:

```python
store = Store('./_o_lmdb')

store.put('o.T.User', {
	'kind': 'class',
	'proto': 'o.T.User',
	'bases': ['o.T'],
	'fields': ['name', 'age'],
})

store.put('o.T.User.__fields__.age', {
	'kind': 'field',
	'name': 'age',
	'annotation': 'int',
	'default': 0,
})

user_tree = store.scan('o.T.User')
```

---

## Important Non-Goals

Do not:

```text
imitate SQL tables
split truth across multiple systems
store whole universe in one blob
let storage names replace o names
turn LMDB into ontology
```

---

## Migration Path

Phase 1:

```text
LMDB as cache beside current store
```

Phase 2:

```text
class / instance primary nodes in LMDB
```

Phase 3:

```text
refs, vectors, indexes unified
```

Phase 4:

```text
optional old store retirement
```

---

## Final Principle

```text
o decides what exists.
LMDB remembers it quickly.
```

