# `o` invariants 1

## Scope

This file records the invariants established in the current design conversation around `o.T`, source-backed classes, shadow classes, and Python inheritance.
It is meant as a compact working law, not as a historical transcript.

---

## Root law

- `o.T` is the public root class of the ontology.
- `o.T` is not an ordinary source-backed class that should be shadowed like its descendants.
- The hidden-source / public-shadow split starts below the root.

---

## Source and shadow law

- A source-backed class loaded from a `.py` file may be hidden as a source authority.
- The public class returned by `o` is the shadow class.
- The source class must not appear in public `o` ontology surfaces such as `o.get(id)` or `o.T.Name`.
- The shadow class is the public identity carrier for `__proto__`, `id`, disk class, and public persistence.

---

## Python inheritance law

- `o` should piggy-back on Python inheritance as much as possible.
- The public shadow class is allowed to inherit ordinary namespace from the hidden source base.
- Ordinary Python attributes and methods do not need to be copied into the shadow class `__dict__` merely to make them visible.
- If an attribute is available through normal Python MRO, that is a valid and preferred implementation path.

Meaning:

- hidden source base may hold ordinary namespace
- public shadow may expose that namespace through inheritance
- no duplicate republishing is required just to satisfy local lookup

---

## Ordinary namespace law

- Field declarations are not part of ordinary class namespace.
- After class definition, field names such as `name` should not remain in the class `__dict__`.
- Ordinary underscored attributes and ordinary methods remain ordinary Python namespace and may be resolved through inheritance.

---

## Carrier law

- Any `.py` class carrier loaded through `py.py` is an own-module source file by law.
- That fact is supplied by the loader.
- `o` should not try to re-derive own-module status from class name or route suffix.

Operational consequence:

- plugin supplies `__has_own_module__ = True`
- module layer may default it to `False`
- no name-based deduction is needed

---

## Route law

- `__route__` is source authority metadata.
- A public class room may persist `__route__` if hidden source authority exists behind it.
- Runtime-defined public classes have no route.

---

## Reconciliation law

- Public field persistence belongs to the shadow class room.
- Source-defined fields are reconciled into that public field room.
- Runtime-defined fields live in the same public field room.
- Therefore source-defined and runtime-defined public fields are not separate public ontologies.

---

## Layer separation law

- Disk entities must not modify runtime wrappers, Python classes, or public objects.
- Disk entities may read disk state, write disk state, and return disk-layer objects or values.
- Wrapper mutation belongs to wrapper/materialization layer such as `TMeta`, `Fields`, or plugin code.
- This keeps disk representation and runtime object assembly as separate layers.

---

## Marker law

- Storage markers such as `__is_source__` are storage metadata.
- They are not ordinary field properties.
- They must not participate in normal field-prop decoding or publishing.

---

## Design direction

- Prefer clear laws over heuristic deduction.
- Prefer Python's own inheritance and lookup semantics over local reimplementation when the language already gives the desired behaviour.
- Avoid copying structure merely to simulate what normal MRO already provides.
