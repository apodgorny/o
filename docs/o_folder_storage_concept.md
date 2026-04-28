# `o` as Folder-Based Storage Concept

## Core ontology

There are still two structures:

- `IS-A` — ontology / form / inheritance
- `HAS-A` — retention / ownership / liveness

But the current liveness law is stricter now:

- `IS-A` lives in folder geometry
- `HAS-A` lives in persisted refs and refcount
- top-level persistence is rooted through `o.V`

So:

- form is a tree
- ownership is a graph
- lifecycle is decided by disk edges, not wrapper lifetime

## Entity and file distinction

An entity is still a folder-backed thing.
Files are storage for its local state.

So:

- entity = room
- file = local state or service table

A child entity is not a file.
A file is not an `o` entity.

## Storage shape

Current instance-side state is:

- `__value__` for atomic raw bytes
- `__list__` for ordered child refs
- `__dict__` for keyed key/value refs
- `__attributes__` for packed named child refs

Current service-side state is:

- `__registry__` for binary `id -> path`
- `__refcounts__` for binary persistent refcount

## Instance files and sequence state

A workable current shape is:

- `__list__` — stores ordered child ids
- `__dict__` — stores keyed key/value ids
- `__value__` — stores atomic raw bytes
- `__attributes__` — stores named child ids
- `__version__` plus `__items__` — store next birth number and current live order

Meaning:

- instance-side files store per-instance shape and ownership edges
- class-side sequence state lives in `__version__` and `__items__`

## List behavior

List order is explicit.
It must not depend on folder order.

So list behavior comes from `__list__`, not from how the filesystem happens to return names.

## Class vs instance distinction

Subclass and instance are both entities, but they are distinguished spatially.

The class room owns:

- `__fields__/`
- `__subclasses__/`
- `__instances__/`

Instances live only under `__instances__/` as underscored versions:

- `_0`
- `_1`
- `_2`

So:

- subclass classes live under `__subclasses__/`
- instance rooms live under `__instances__/`
- instance birth id is stable
- live order is held separately in `__items__`

## Read / write model

The current desired law remains:

- read should stay read
- write should stay one explicit act

That is why:

- registry read miss does not allocate
- GC read miss does not allocate
- mutation boundaries are explicit in disk managers

This keeps simultaneity legible.

## Liveness model

The current liveness formula is:

- direct edge created -> refcount increments
- direct edge removed -> refcount decrements
- refcount reaches zero -> release may cascade through direct children
- `o.V` is the root owner of top-level persistent state
- startup sweep removes zero-ref non-root instance rooms

So the beautiful hard-link intuition is still right, but now it is implemented explicitly through:

- direct refs on disk
- one binary refcount table
- one root value

## Performance direction

Recent performance wins confirmed the architectural direction:

- packed `__attributes__`
- binary `__refcounts__`
- binary `__registry__`

The important point is not only speed.
It is that the faster path also matches the invariant better:

- fewer little files
- fewer hidden writes
- clearer ownership boundaries
