# Intent to upgrade `o`

## Core Direction

- Preserve the spirit of simultaneity: truth must be available at all times at the fingertips.
- Avoid delayed truth mechanisms such as broad GC sweeps.
- Lifecycle transitions should update the whole truth surface at once.
- `o` should remain primarily deterministic data / structure / persistence.
- Generative / nondeterministic behavior belongs outside `o` (e.g. in `a`).

## Garbage Collection Philosophy

- If a system needs sweeping, it indicates delayed truth.
- Prefer immediate consequence over later cleanup.
- Collectability should be derived from current disk truth, not stored as stale state.
- Better framing: `is_uncollectable` rather than `is_collectable`.
- Anything not held by valid relations becomes collectable and should be removed immediately.

## Holding Relations

An entity is uncollectable when held by one or more real relations such as:

- Root ownership
n- Construction ownership
- Parent ownership chain
- Existing instances (for classes)
- Other explicit semantic references

Death occurs when the last holding relation disappears.

## Construction Concept

- Replace temporary flags with real holding structure.
- Introduce Construction manager in disk entities.
- Construction acts as a root-like temporary holder during creation.
- Commit transfers holding relation to final owner.
- Abort releases holding relation.
- This prevents premature deletion between class creation and first instance creation.

## Registries Instead of Folders

Use registry mechanism (`id -> path`) on disk rather than ad-hoc folders of symlinks.

Two symmetric registries with different laws:

### Class Uncollectable Registry

- Holds temporary classes during becoming.
- Protects classes before first instance exists.
- Cleared on startup.
- Session / birth protection.

### Instance Uncollectable Registry

- Holds root-connected persistent instances.
- Represents connectedness to root.
- Persists across restart.
- Source of truth for instance reachability.

## Class Lifecycle Rules

- Temporary classes may receive generated internal unique names.
- Public name optional, internal unique name mandatory.
- Any class may be extended, not only `o.T`.
- Generated temporary child names are unique under parent namespace and prefixed.
- First instance removes temporary birth protection state.
- Last instance removal may trigger immediate class collection (for temporary classes).
- Explicit named classes are durable ontology and are not removed merely because they have zero instances.

## Instance Lifecycle Rules

- Instances inherit owner uncollectability on creation.
- Ownership link / unlink updates descendants recursively on selective basis.
- Disconnect from ownership chain triggers recalculation only where needed.

## Performance Direction

- Slow checks should happen only on rare boundary events:
  - first instance creation
  - last instance unlink
  - ownership link / unlink
  - startup rebuild / reset where applicable
- Prefer selective updates over global scans.

## Cache / Assemblage Point

- Introduce Cache manager.
- Cache budget `N` represents size of assemblage point of an agent.
- Global cache budget shared across caches.
- Rank entries by last accessed.
- Overflow evicts lowest-ranked entries simultaneously from caches.
- Cache is attention surface, not source of truth.
- Disk remains truth.

## Architectural Separation

Preferred separation:

- `a` = loading / birth substrate
- `o` = data / schema / persistence / deterministic structure
- `a` = agents + generation / nondeterministic action

## Key Principles

- System invariant must be obvious.
- No hidden truth.
- Structure defines life.
- Relations define persistence.
- Absence of holding relations defines deletion.
- Form one, laws clear.
