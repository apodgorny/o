# Types and instances in `o`

## Overview

In `o`, types and instances do not live by the same law.

- types are world forms
- instances are persistent value entities

But the important split is no longer:

- explicit type deletion
- implicit instance deletion through `__del__`

The current split is:

- type lifetime is explicit and schema-like
- instance lifetime is determined by disk ownership

---

## 1. Types are persistent forms

A type in `o` is not just a temporary Python class.

It is a named form such as:

- `o.T.User`
- `o.T.Invoice`
- `o.T.V`

A type defines:

- structure
- validation
- embodiment law
- reconstruction law

So a type is not governed by current instance count.
It remains a stable form of the world until explicitly removed.

---

## 2. Types are global

Types live in the ontology namespace.

That means:

- they are globally addressable
- they are not meant to vanish just because no current instance happens to be loaded
- redefining an existing named type is not ordinary rebinding

This is the schema side of the system.

---

## 3. Instances are persistent entities, not temporary wrappers

An instance in `o` exists on disk.

The Python object is only the current manifestation of that disk entity.

So:

- the room on disk is the durable thing
- the wrapper in RAM is only the current manifestation
- the wrapper may disappear and later be reconstructed

This means RAM lifetime must not decide truth about persistence.

---

## 4. Instance lifetime is owned by disk edges

Current instance deletion law:

- object attrs hold child refs
- list state holds ordered child refs
- dict state holds key/value refs
- `o.V` holds root-level persistent refs

These edges are counted by persistent refcount.

So an instance stays alive while it is owned on disk.
When its last owning edge disappears, refcount reaches zero and GC releases it.

---

## 5. `o.V` is the persistence root

Top-level persistence is no longer implicit.

It is rooted through `o.V`.

`o.V` is:

- a regular source-backed `o.T` subclass
- a singleton value instance
- the root owner of persistent top-level state

Meaning:

- attached to `o.V` -> survives reload
- detached from `o.V` and from all other owners -> may be released

This makes persistence legible:

- persistence is reachability from `o.V`

---

## 6. Wrapper lifetime is not lifecycle truth

Python wrapper death is not the deletion trigger.

`__del__` is not the lifecycle oracle.

Why:

- disk may contain meaningful ownership unknown to current RAM
- strong refs in `o.__entities__` are runtime cache mechanics, not ontology
- process end is not a reliable semantic event

So the current model is intentionally stricter:

- memory is manifestation
- disk is truth

---

## 7. Startup sweep completes the model

Because persistence truth lives on disk, startup performs orphan cleanup.

On initialization:

- `o.ensure_value()` brings up the singleton root `o.V`
- `o.services.GC.sweep()` releases zero-ref non-root instance rooms

So objects that were never rooted, or were left behind after previous process life, do not silently survive reload.

---

## 8. Asymmetry that remains correct

The asymmetry is still real, but it is now cleaner:

### Types

Types are:

- named
- structural
- schema-like
- explicit

So type lifetime is explicit.

### Instances

Instances are:

- disk-backed values
- owned through direct edges
- released by refcount and cascade

So instance lifetime is structural, not manual in everyday use.

---

## 9. Final principle

The guiding law now is:

- types define world form
- instances live while the world still owns them

Therefore:

- removing a type is explicit schema work
- removing an instance is an ownership event on disk

This is the current ontological model of `o`.
