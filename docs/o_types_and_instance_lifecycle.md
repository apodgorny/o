# Types and instances in `o`

## Overview

In `o`, types and instances do not have the same ontological status.

They stand somewhere between Python classes and SQL tables:

- like Python classes, they define structure and behavior
- like SQL tables, they define persistent form and must be managed explicitly

This leads to an intentional asymmetry:

- types are deleted explicitly
- instances are deleted implicitly through GC via `__del__`

That asymmetry is correct.

---

## 1. Types are persistent schema-form objects

A type in `o` is not just a temporary Python class.

It is a global named form in the system, such as:

- `o.User`
- `o.List`
- `o.Dict`
- `o.Invoice`

A type defines:

- how values are interpreted
- how objects are stored on disk
- how bytes are read back into meaning
- how nested values are validated and cast
- how persistent entities are represented in the world of `o`

So a type is not merely something that can instantiate objects.

It is closer to:

- a schema
- a structural contract
- a persistent world-form

Because of that, a type should not disappear merely because no current instances exist.

So the existence of a type is not dependent on current instance count.

---

## 2. Types are global

In this architecture, types are accessed via `o`.

That means they remain strongly referenced by the registry / namespace and do not vanish automatically.

This is intentional.

If a type is globally named, it is part of the ontology of the system.

So redefining an existing global type is an error.

This is not ordinary Python rebinding.
It is attempted redefinition of an existing world-form.

Type identity is explicit, global, and stable.

---

## 3. Type deletion is explicit

Because types are global structural forms, deleting a type is a schema-level operation.

It must be explicit.

This is like dropping a table in SQL:

- a table does not disappear because no rows remain
- it is removed explicitly when the schema itself should no longer exist

So:

- type lifetime is not driven by Python reference counting
- type lifetime is not driven by instance count
- type lifetime is driven by explicit deletion

---

## 4. Instances are different

An instance in `o` is not the same kind of thing as a type.

The instance itself exists on disk.
The Python wrapper object is only a temporary in-memory manifestation of that disk object.

So when you write:

```python
x = o.User(...)
```

the Python object `x` is not the durable object in the deepest sense.

It is a live wrapper / handle / manifestation for a persistent disk-backed entity.

This means:

- the persistent record is the durable object
- the Python wrapper is temporary
- the wrapper may disappear while the disk object remains
- another wrapper may later be instantiated for the same disk object

So instance lifetime in memory is naturally ephemeral.

---

## 5. Instance deletion is implicit via GC and `__del__`

Because Python wrappers are ephemeral, implicit cleanup is appropriate for them.

In this system, instance cleanup is implemented through `__del__`.

When the wrapper becomes unreachable:

- Python GC / refcounting can destroy the wrapper
- `__del__` is triggered
- cleanup logic can run automatically

This is correct because the wrapper is a runtime manifestation, not the eternal schema-form.

So unlike types:

- instances may disappear automatically
- wrapper death is part of normal runtime behavior
- that cleanup is implicit

This gives the system a useful asymmetry:

- type deletion is explicit
- instance cleanup is implicit

---

## 6. Why this asymmetry is correct

The asymmetry matches the ontology.

### Types

Types are:

- global
- structural
- schema-like
- persistent in meaning
- part of the world-definition

So they should be explicitly removed.

### Instances

Instances are:

- disk-backed entities with temporary Python wrappers
- runtime manifestations
- ephemeral in memory
- naturally compatible with GC cleanup

So they may be implicitly cleaned up.

This is not inconsistency.
It is a correct reflection of the fact that these are two different layers of existence.

---

## 7. Relation to Python classes

Ordinary Python classes behave differently:

- they are ordinary runtime objects
- they live while references exist
- they can be rebound by name
- they are not normally treated as schema objects

`o` types are stricter than ordinary Python classes.

They are registered globally and treated as stable forms.

So while they use Python class machinery, their semantic role is larger than that of ordinary classes.

---

## 8. Relation to SQL tables

Ordinary SQL tables also differ:

- they are explicitly created
- explicitly dropped
- define persistent structure
- do not vanish when empty

`o` types share this aspect.

But unlike SQL tables, they also participate in Python runtime behavior:

- casting
- validation
- instance wrapping
- method dispatch
- container/object behavior

So they are not merely tables either.

They really do sit between:

- Python classes
- SQL tables

And their lifetime rules reflect exactly that.

---

## 9. Final principle

The guiding principle is:

- a type is a persistent named structural form of the world
- an instance wrapper is a temporary in-memory manifestation of a disk object

Therefore:

- removing a type changes the world-schema and must be explicit
- removing an instance wrapper is ordinary runtime cleanup and may be implicit

That is why in `o`:

- types are deleted explicitly
- instances are cleaned up implicitly via GC and `__del__`

This is not an implementation accident.
It is the correct ontological model for the system.
