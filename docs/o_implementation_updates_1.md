# O Implementation Updates 1

## Current state

This document no longer describes an intermediate stage.
It captures the current implemented storage line.

## Current invariants

- `Class` and `Instance` are distinct disk entities.
- `__proto__` is canonical identity.
- `__o_module__` is lawful source origin if one exists.
- folder geometry remains the source of truth for class / instance placement.
- `Registry` is a binary `id -> path` table, not a symlink forest.
- `GC` is a binary refcount table, not per-entity text files.
- object attrs, list items, and dict entries are direct ownership edges.
- persistence across reload is rooted through `o.V`.
- startup performs orphan sweep for zero-ref non-root instances.

## Disk entity line

- `o.disk.Entity`
  - stores `id` and `path`
  - registers `id -> path` in `o.services.Registry`
  - `load(id)` resolves path from registry
  - `load(id)` distinguishes class vs instance by last path segment `_<digits>`
  - `load(id)` reopens `o.disk.Class(path)` or `o.disk.Instance(path)`

- `o.disk.Class`
  - receives full `path`
  - creates its directory on init
  - materializes:
    - `fields = o.disk.Fields(path)`
    - `subclasses = o.disk.Subclasses(path)`
    - `instances = o.disk.Instances(path)`

- `o.disk.Instance`
  - receives full `path`
  - creates its directory on init
  - always materializes:
    - `attributes = o.disk.Attributes(path)`
  - materializes shape-specific managers according to ontology
  - may also materialize:
    - `list = o.disk.List(path)`
    - `dict = o.disk.Dict(path)`
    - `atomic = o.disk.Atomic(path)`

## Storage managers

- `o.disk.Attributes`
  - manages one packed file `__attributes__`
  - public state: `items`
  - methods:
    - `set(name, id)`
    - `get(name)`
    - `delete(name)`
    - `has(name)`
  - updates GC on mutation

- `o.disk.List`
  - manages file `__list__`
  - public state: `items`
  - methods:
    - `get(index)`
    - `set(index, id)`
    - `delete(index)`
  - whole-state setter updates GC by delta

- `o.disk.Dict`
  - manages file `__dict__`
  - public state: `items`
  - methods:
    - `get(key)`
    - `get_key_id(key)`
    - `set(key, value_id)`
    - `delete(key)`
  - whole-state setter updates key and value GC by delta

- `o.disk.Atomic`
  - manages file `__value__`
  - stores raw atomic bytes directly

## Services

- `o.services.Registry`
  - stores `id -> path` in one binary table `__registry__`
  - read miss does not allocate

- `o.services.GC`
  - stores persistent refcount in one binary table `__refcounts__`
  - `update(old_id, new_id)` is the canonical edge replacement act
  - `dec(id)` may release an entity
  - release cascades through direct children only
  - `sweep()` removes zero-ref non-root instance rooms on startup

## Root value

- `o.T.V` is the source-backed class
- `o.V` is the singleton root value instance

Meaning:

- attach under `o.V` -> survives reload
- leave unowned on disk -> orphan sweep may remove it on next startup

## Folder geometry

```text
<data_root>/
	__registry__
	__refcounts__
	T/
		__fields__/
			<slot_name>/
				<metadata_name>

		__subclasses__/
			<SubclassName>/

		__instances__/
			__index__
			_0/
			_1/
			_2/
```

```text
<Instance>/
	__attributes__   # packed name -> child id refs
	__list__         # only for list ontology
	__dict__         # only for dict ontology
	__value__        # only for atomic ontology
```

## Read / write law

- read should stay read
- mutation should stay one explicit act
- disk and RAM must move together under simultaneity
- GC hooks belong at disk mutation boundaries, not in wrappers
