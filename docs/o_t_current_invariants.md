# `o.T` current invariants and decisions

This file captures only the invariants, contracts, and chosen directions established in the current conversation.
It intentionally excludes older conflicting lines unless they were explicitly reaffirmed here.

---

## 1. Canonical identity

- `__proto__` is the canonical string identity of an entity.
- Example: `o.T.MyClass.MySubclass._12`.
- `__route__` is the location of source on disk / code location.
- `__route__` is **not** canonical identity.

---

## 2. Disk substrate

- The active substrate is folder-based disk geometry.
- `Class` and `Instance` are distinct disk entities.
- Instance rooms live under class folders.
- Instance rooms use underscored names like `_<digits>`.
- Folder structure is source of truth for class / instance placement.

---

## 3. Universal object semantics

- All `o.T` entities have object attributes.
- This includes atomics, lists, dicts, and field-bearing classes.
- Object attributes exist to support ordinary entity fields and generated properties.
- Object attributes are persisted through `__attributes__`.
- Object attributes are independent from list / dict / atomic special semantics.

---

## 4. Two input modes

### 4.1 Root `o.T`

`o.T` itself is the universal embodiment entrypoint.

Rules:
- accepts one positional arg, or kwargs, or both
- one positional arg chooses the embodied runtime type from Python root type
- kwargs are always object attributes on the born entity
- existing `o.T` instances pass through unchanged
- root embodiment is recursive

### 4.2 Subclasses of `o.T`

Subclasses follow a different constructor law.

Rules:
- one positional arg is allowed if the class has `__annotation__`
- kwargs become object attributes
- declared fields are validated as required if they have no default
- undeclared attrs are still allowed ad hoc
- annotation-bearing classes may also have object attrs
- annotation semantics and object-attribute semantics are independent axes and may coexist

Chosen allowance:
- a subclass may accept both:
  - one annotated value
  - kwargs as object attrs

Example shape:
- `o.List([1, 2, 3], title='numbers')`

---

## 5. Constructor split

The current split is:

- `TMeta.__call__` decides whether `__init__` should run
- `T.__new__` chooses embodiment path and creates the live instance
- `T.__write__` performs common born-instance setup
- subclass `__init__` handles class-specific contained value semantics

Meaning:
- `__new__` chooses construction logic
- `__write__` creates the new instance facts and assigns common runtime slots
- `__init__` handles only class-specific contained value semantics

---

## 6. `__write__` responsibilities

`__write__` handles common born-instance setup for all subclasses.

It:
- creates the new instance facts
- assigns `id`
- assigns `__version__`
- assigns `__proto__`
- validates missing required declared fields
- assigns kwargs through `setattr`

---

## 7. Field rules

- kwargs may correspond to declared fields or ad hoc attrs
- missing required fields must raise error
- field names cannot start with `_`
- lowercase names are field / attribute names
- capitalized names are class / subclass names

Field requiredness follows the default law:

- `default is o.Undefined` → required / not optional / not nullable
- `default is None` → optional / nullable
- `default is other value` → optional / not nullable

Defaults live on the assembled class, not in the instance.
Therefore:
- defaults are class-side
- defaults are inherited naturally
- instance construction should not redundantly materialize defaults into the live object just to make them exist

---

## 8. Live slot law

For object attrs, the current live instance slot law is:

- the instance slot holds a lazy copy / Python-visible value
- the disk side stores the embodied child id in `__attributes__`
- this follows simultaneity: memory and disk are updated together as one act

Meaning:
- the slot does not have to mirror the persisted id form directly
- it holds Python leaves for atomics and wrappers for non-atomics while disk stores the child reference

---

## 9. Embodiment

- Embodiment means creating the appropriate typed entity from object shape / data shape.
- Root embodiment starts from `o.T(data)`.
- Embodiment is recursive from `o.T(data)`.
- Root embodiment dispatches by the Python root type.

---

## 10. Atomic direction

Chosen architectural direction:
- `Atomic` should be atomic in the strong sense: it should not refer to anything else.
- Therefore `Atomic` should store the raw value bytes in its own `__value__` file.
- It should not store another entity id.

This implies:
- object attributes store child ids
- an atomic entity stores its own substance directly

Rejected direction:
- object → atom id → value id

Chosen direction:
- object → atom id
- atom → raw value bytes

---

## 11. `o.Atom`

Current chosen direction for `o.Atom`:

- `o.Atom` is the common atomic base
- `o.Atom` itself should not declare `__annotation__`
- concrete atomic subtypes such as `o.Str` and `o.Int` must declare `__annotation__`
- concrete atomic init requires one value
- atomic init validates against the subtype annotation
- atomic init writes the raw bytes to disk

Current simplification:
- no `undefined` handling inside concrete atomic value materialization
- concrete atomic instances are expected to be born with a real value

`__cast_out__` is sufficient as a memory-side read because of simultaneity.
The point is not laziness; the point is that memory and disk already agree.

---

## 12. Atomic codec law

Chosen design:
- general atomic flow lives in `o.Atom`
- concrete subtypes implement their own conversion to bytes

Example:
- `o.Str.__cast_in__(value)` encodes `str` to bytes
- `o.Int.__cast_in__(value)` encodes `int` to bytes

Meaning:
- common flow, concrete codec
- no giant universal serializer in `o.Atom`

---

## 13. Current atomic set

The currently added atomics are:
- `o.Str`
- `o.Int`
- other basic atomics were planned next

Concrete atomics register their origin types through `__cast_map__`.

---

## 14. List direction

The current intended `o.List` design is:

- list-specific contained value is provided as one positional annotated value
- kwargs remain object attrs
- list items are embodied recursively through `o.T(item)`
- disk list storage stores child ids in order
- runtime surface should expose Python-facing list access

List invariants discussed:
- list semantics and object attributes are independent
- `x[0]` is list semantics
- `x.title` is object-field semantics

Live access shape chosen:
- Python value for atomics
- wrapper for non-atomics

This applies to container access too.

---

## 15. `__getattr__` law

A future / required `__getattr__` was identified with two meanings:

### instance lowercase name
- resolve persisted object attr by child id from `__attributes__`
- cache the visible value into the live instance slot

### class capitalized name
- resolve nested subclass from disk-backed proto chain

### class underscored version
- resolve instance materialization by version like `._0`

---

## 16. Reconstruction promise

The reconstruction contract was reaffirmed.

Desired law:
- `o.get(id)` returns class or instance
- reconstructed entities must preserve the same visible interface shape
- class reconstruction yields an assembled class
- instance reconstruction yields a ready instance

---

## 17. Annotation law

- In runtime, `__annotation__` should be an `o.Annotation` object.
- `TMeta` is responsible for normalizing class-declared annotations into `o.Annotation`.
- Therefore code in `T` may assume `cls.__annotation__` is already normalized.

---

## 18. Current naming split

- lowercase names → fields / attributes
- capitalized names → classes / subclasses
- names starting with `_` are internal / service names and are not valid ordinary field names

---

## 19. Class birth law

Named class birth now has two lawful paths only:

- source-backed class
  - declared in a file-backed `o.Module`
  - persists `__route__` on class room
  - re-enters through source resolution

- runtime-defined class
  - declared through `extend()`
  - does not persist `__route__`
  - re-enters structurally from disk lineage

Direct runtime class declaration without lawful module origin is not the current line.

---

## 20. Current public conveniences

The current public surface directly exposes:
- `x.id`
- `x.__proto__`
- `x.__version__`

---

## 21. Summary formula

The current picture is:

- `o.T` is the root embodiment entrypoint
- all `o.T` entities have object attributes
- subclasses may simultaneously have:
  - one annotated contained value
  - kwargs as object attrs
- `__new__` chooses the construction law
- `__write__` performs common born-instance setup
- subclass `__init__` materializes its own contained value
- object attributes persist child ids
- atomic entities persist their own raw value bytes
- root embodiment is recursive
- reconstruction must preserve the same interface shape

---

## 22. Persistence and liveness

Current persistence law:

- `o.T.V` is the root value class
- `o.V` is the singleton root value instance
- top-level persistence is reachability from `o.V`

Current lifecycle law:

- direct ownership edges live in `__attributes__`, `__list__`, and `__dict__`
- GC persists refcount in one binary table
- `GC.dec(id)` may release an instance room and cascade through direct children
- startup sweep removes zero-ref non-root instance rooms

Rejected law:

- wrapper dies -> entity dies

Current law:

- disk ownership changes -> refcount changes -> release may happen
