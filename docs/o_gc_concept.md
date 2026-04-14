# GC concept in `o`

## Core principle

GC in `o` is disk-driven, not Python-driven.

The source of truth is:

- persistent ownership edges on disk
- persistent refcount in the GC table
- reachability from the root value `o.V`

Python wrapper lifetime is not the source of truth.

---

## Current law

1. GC counts only direct owning edges.

Those edges are created and removed only at disk mutation boundaries:

- `Attributes.set()` / `delete()`
- `List.items`, `set()`, `delete()`
- `Dict.items`, `set()`, `delete()`

2. Refcount is persisted in one binary table.

- file: `__refcounts__`
- owner: `o.services.GC`
- shape: fixed-size hash table by entity `id`

3. `GC.update(old_id, new_id)` is the canonical edge-replacement act.

Meaning:

- removed edge -> `dec(old_id)`
- added edge -> `inc(new_id)`
- unchanged edge -> no-op

4. `GC.dec(id)` may release an entity.

When count drops to `0`:

- the instance room is released
- registry entry is removed
- loaded wrapper is evicted from `o.__entities__`
- direct children are decremented

5. Release is cascading, but only through direct children.

There is no mark-sweep scan.
There is no subtree recount on ordinary writes.

The law is:

- ordinary mutation updates only changed direct edges
- release cascades only through direct children

6. Cycles are outside the current GC contract.

Pure refcount does not collect cycles.
That is an accepted boundary of the current system.

---

## Root law

Persistence across reload is defined by `o.V`.

- `o.V` is the singleton root value
- attaching something to `o.V` gives it persistent ownership
- detaching the last owning path lets refcount GC release it

So the clean reading is:

- reachable from `o.V` -> survives reload
- not reachable from `o.V` -> may be swept as orphan

---

## Startup sweep

Python process shutdown is not relied on for truth.

Therefore startup performs orphan cleanup:

- every non-root instance with `refcount == 0` is released

This makes the system robust against:

- ordinary process end
- wrapper lifetime accidents
- previous crashes

---

## What `__del__` is not

`__del__` is not the deletion mechanism.

It is not used as the liveness oracle, because:

- RAM may not know all meaningful disk edges
- wrapper lifetime is not persistent truth
- process end is not a trustworthy commit point

So the current model is not:

- wrapper dies -> entity dies

It is:

- disk edge disappears -> refcount changes
- refcount reaches zero -> entity is released

---

## Summary

GC in `o` is:

- direct-edge refcount
- persisted on disk
- rooted by `o.V`
- cascaded through direct children
- repaired by startup orphan sweep

This preserves simultaneity and keeps disk as the single source of lifecycle truth.
