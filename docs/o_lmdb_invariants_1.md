# `o` LMDB invariants 1

## Scope

This file records the new accepted direction for `o` after the move away from folder storage.
It is meant as a law document, not as a proposal log.

---

## Root direction

- `o` keeps ontology, identity, schema, behavior, and deterministic persistence law.
- LMDB is storage substrate only.
- Python source remains authoring layer for source-backed classes.
- Public `o` surface should stay essentially the same even if storage changes underneath.

Meaning:

- keep `o.T`
- keep `o.get(...)`
- keep source-backed classes
- keep field / attribute reflection surface
- change storage and lifecycle embodiment, not ontology

---

## Public surface law

The public interface is preserved unless a new law is explicitly accepted.

This includes:

- `o.T`
- `o.get(id_or_proto)`
- source-backed class access
- runtime class extension
- field reflection through `._`
- instance attrs
- `to_json_schema()`
- `to_prompt()`

The storage move must not force a visible semantic rewrite of `o`.

---

## Canonical identity law

`__proto__` remains the canonical identity string of an entity.

`id` remains a first-class technical identifier derived from canonical proto.

```text
id = hash(proto)
```

Examples:

```text
o.T.User
o.T.User[0]
```

Accepted change:

- `._0` is removed completely
- `[0]` becomes canonical and evalable instance form

This means:

- class proto: `o.T.User`
- instance proto: `o.T.User[0]`

`__version__` remains an instance concern, but its exact runtime form is not fixed here.

---

## Reflection law

`__proto__` identifies the entity only.

Reflected structure after `._` is not part of proto identity.

Examples:

```text
o.T.User
o.T.User[0]
o.T.User._.fields.age
o.T.User[0]._.attributes.name
```

So the law is:

- `proto` = entity identity
- `reflection proto` = reflected address inside that entity

Important consequence:

- `__fields__`
- `__attributes__`
- list payload
- dict payload
- lifecycle state

are not part of entity proto.
They are addressed through reflection proto.

No separate `expath` term is needed.

---

## LMDB keyspace law

The first LMDB version uses one LMDB database with three logical keyspaces.

Those keyspaces are:

- main nodes
- `id` registry
- `route` registry

No extra artificial prefixes are required because the key forms already differ.

The accepted key forms are:

- main nodes start with `o.T`
- `id` registry key is just `id`
- `route` registry key is just `route`

Meaning:

- one physical LMDB database
- three logical spaces
- no decorative prefix scheme

---

## Main node law

Main nodes hold the actual semantic records of `o`.

Addressing law:

- entity root node is keyed by `proto`
- reflected node is keyed by `reflection proto`

Examples:

```text
o.T.User
o.T.User[0]
o.T.User._.fields.age
o.T.User[0]._.attributes.name
```

One addressable node corresponds to one addressable LMDB record.

This preserves:

- simultaneity
- fractional update
- one-to-one node storage

The root entity node stores only its own root payload.
Reflected children live as separate records.

---

## Value shape law

Stored values should be as direct as possible.

Accepted direction:

- direct value when possible
- wrapper structure only where required

So the first preference is not a universal fat node envelope.
The system should avoid unnecessary wrapper dicts when a direct value is sufficient.

---

## Serialization law

Serialization direction:

- production: `msgpack`
- debug: `json`

This is a storage mode choice, not an ontology choice.

---

## Registry law

### `id` registry

`id` registry stores:

```text
id -> proto
```

### `route` registry

`route` registry stores:

```text
route -> { id, proto, mtime }
```

`mtime` does not live on the class object itself.
It belongs to route synchronization metadata.

---

## Source synchronization law

Access through source-backed route or proto may trigger source synchronization.

The accepted law is:

- if source file is fresher than stored route `mtime`, synchronize source to class and then to LMDB
- otherwise load directly from LMDB

Source freshness is checked by `mtime` only.
No content hash is required in this law.

The source synchronization metadata lives in the `route` registry, not in class nodes.

Open implementation choice:

- freshness may be decided at plugin boundary
- freshness may be decided in `TMeta`

What is fixed already:

- freshness must be decided in one place before public class is returned

What is not fixed here:

- whether this is plugin-owned
- whether this is `TMeta`-owned
- whether separate `create()` exists or `__new__` handles the write path itself

---

## Source-backed class law

Source-backed authoring stays in Python files.

Synchronization law:

- source-backed access may rebuild semantic nodes from source
- rebuilt semantic nodes are written into LMDB
- later loads may reopen directly from LMDB when source is not fresher

Reconciliation law stays:

- source-defined public class structure remains authoritative where source defines it
- runtime public growth may still exist where it does not contradict source law

---

## Accessor law

Accessor syntax is no longer constrained by old folder grammar.

Accepted direction:

- canonical class access stays dotted
- canonical instance access becomes bracketed
- reflection stays under `._`

Examples:

```text
o.T.User
o.T.User[0]
o.T.User._.fields.age
o.T.User[0]._.attributes.name
```

This means accessor form, canonical proto, and storage law are now designed intentionally rather than inherited from folder shape.

---

## Collection law

`list` and `dict` keep their existing ownership semantics.

Accepted storage direction:

- container root stored as one node
- compact internal structure kept there
- references to children stored by `id`

So:

- no exploded per-item key law for first version
- ownership still flows through contained child refs

This preserves current semantic behavior while keeping storage smaller and clearer.

---

## Lifecycle law

The old persisted refcount line is removed.

The new line is:

- no broad sweep
- no delayed lifecycle truth
- collectability follows current holding relations
- linked / uncollectable truth is updated immediately at link / unlink time

This truth is cached on nodes.
It is not meant to be lazily rediscovered by later global cleanup.

Meaning:

- when a relation appears, truth is updated immediately
- when a relation disappears, truth is updated immediately
- updates propagate everywhere affected by that relation change

---

## Class lifecycle law

Temporary generated classes may be protected during becoming.

Accepted law:

- temporary class protection exists
- that protection is session-scoped
- temporary class uncollectable state is removed on next run

Durability split:

- source-backed / named public classes are durable ontology
- they are not removed merely because they currently have zero instances
- temporary generated classes may be removed when their last holding relation disappears

---

## Instance lifecycle law

Instance persistence is rooted through `o.V`.

Accepted law:

- instances live while linked to `o.V`
- instances are removed when unlinked from `o.V`
- child relations in attrs / list / dict are updated simultaneously with link / unlink
- linked fact is cached on nodes

There is no longer a general orphan sweep law here.

Startup cleanup is reduced to temporary class uncollectable cleanup only.

---

## Structural life law

Structure defines persistence.

That means:

- relations define life
- absence of holding relations defines deletion
- lifecycle truth should always be available from current stored state

This preserves the spirit of simultaneity:

- truth now
- no deferred repair
- no hidden cleanup stage

---

## Summary formula

The accepted direction now is:

```text
proto            = canonical identity of entity
reflection proto = reflected address inside entity
id               = hash(proto)
LMDB             = one database, three keyspaces
main nodes       = semantic truth
id registry      = id -> proto
route registry   = route -> { id, proto, mtime }
source sync      = by mtime
instance form    = [0], not ._0
lifecycle truth  = immediate, linked, cached, no sweep
```

