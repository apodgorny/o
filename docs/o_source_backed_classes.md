# `o` source-backed classes and public shadow classes

This file records the current architectural direction for source-backed classes.
It describes the split between hidden source authority and the public writable class face.

It is meant to make class loading, field persistence, and runtime class growth cleaner than the current mixed model.

---

## 1. Core law

A source-backed class is **not** the public class in `o`.

The new split is:

- source class = hidden construction authority
- shadow class = public class entity

Meaning:

- the source file still defines lawful form and behavior
- the public class that `o` returns is a shadow class built from that source class
- runtime additions and public persistence live on the shadow class

So the user-facing class is always the shadow class, not the raw source class.

---

## 2. Visibility law

The raw source class must not be visible through public `o` surfaces.

That means:

- `o.T.Name` must return the shadow class
- `o.get(id)` must return the shadow class
- public `__proto__` chain belongs only to the shadow class
- the source class must not appear as a public entity in local `o` lookup

Accepted nuance:

- the source class may still appear in ordinary Python introspection such as `__bases__` and `mro()`
- this is acceptable because the shadow class really extends the source class in Python
- the invisibility rule is about public `o` ontology, not about hiding Python inheritance machinery

So:

- hidden in `o`
- visible in Python inheritance if needed

---

## 3. Disk room law

Source-backed and non-source-backed public classes occupy the same class room shape on disk.

The important distinction is not a different room kind, but whether source authority exists.

Current direction:

- a class room may persist `__route__`
- if `__route__` exists, the public shadow class has source authority behind it
- if `__route__` does not exist, the class is purely runtime-defined

Meaning:

- one public class room shape
- route presence indicates hidden source authority

The room remains the public room of the shadow class.
The source class is not itself the public disk entity.

---

## 4. Plugin-owned source loading

Source-backedness should no longer be a deep concern of `TMeta`.

The new direction is:

- the `o` plugin handles source-backed class loading
- the plugin talks to `o.disk.Class`
- the plugin reconciles source declarations with persisted public class state
- the plugin privately loads the source class
- the plugin then creates or reopens the shadow class and returns that public face

This means the source-backed / runtime-backed split moves out of `TMeta` and into the plugin layer.

Desired plugin flow:

1. detect source-backed class request
2. privately load the source class from `__route__`
3. open the public class room through `o.disk.Class`
4. reconcile source field declarations into the public field room
5. build the shadow class with the source class in `bases`
6. publish and return only the shadow class

So the public class is always the reconciled shadow class.

---

## 5. `TMeta` simplification direction

`TMeta` should become a pure class materializer.

It should ideally stop caring about:

- source-backedness
- route re-entry policy
- whether a class was loaded from source or born at runtime
- reopening through `eval(route)`

This suggests that machinery such as:

- `__has_own_module__`
- `__is_runtime_defined__`
- `is_loading`

may shrink drastically or disappear if the plugin fully owns the source-backed branch.

Desired `TMeta` role:

- receive `bases` and `namespace`
- normalize fields and annotation
- attach `__proto__`
- attach `id`
- attach `__disk_class__`
- bind public fields
- register the public class

Meaning:

- plugin decides source law
- `TMeta` just builds the public class

---

## 6. Route law

`__route__` remains source authority metadata, but it is no longer a public class-recovery mechanism.

So the desired direction is:

- `__route__` points to hidden source authority
- `__route__` is consulted by the plugin
- route loading privately enters the source class
- the plugin then returns the public shadow class

This means the ugly `eval(route)` line in `TMeta` should go away.

The class-reentry law becomes:

- route resolves hidden source authority
- public class identity resolves to the shadow class

So route is no longer:

- public class lookup

It becomes:

- hidden source authority lookup

Important refinement:

- `eval(route)` may still exist as a lookup re-entry mechanism if that is what triggers normal `o` resolution and plugin interception
- this is acceptable
- the important change is that `eval(route)` must no longer live in `TMeta.__new__`
- `TMeta.__new__` should not own source-backed policy
- if `eval(route)` remains, it should live at the lookup / plugin boundary, not inside class materialization

So the simplification target is:

- not necessarily "no eval anywhere"
- but definitely "no eval in `TMeta.__new__`"

---

## 7. Shadow class inheritance law

The shadow class should directly extend the source class in Python.

That means:

- source methods are inherited naturally
- source descriptors are inherited naturally
- source generated-property descriptors can live on the Python inheritance chain
- the shadow class does not have to manually republish every method body

Accepted consequence:

- the source class may appear in `__bases__`
- the source class may appear in `mro()`

This is acceptable because the source class is still hidden from public `o` ontology even if it participates in Python inheritance.

So the public law is:

- shadow class is the `o` class
- source class is a Python base, not a public `o` entity

---

## 8. Public identity law

Only the shadow class should be registered as the public class entity.

That means:

- only the shadow class should enter `o.__entities__`
- only the shadow class should be returned by `o.get(id)`
- only the shadow class should appear in public `__proto__` chain
- instance birth should happen from the shadow class

The source class should not be published into public `o` identity surfaces.

Meaning:

- one public class face
- one public `id`
- one public `__proto__`

The source class is hidden construction machinery.

---

## 9. Public field room law

The shadow class must own the full public field surface.

This means that when a source-backed class is loaded:

- all source-defined fields are copied into the public field room on disk
- those copied fields become part of the shadow class field set
- runtime-added fields live in the same public field room

So all public fields live together in one place:

- source-origin public fields
- runtime-origin public fields

This is necessary so that field props can be added uniformly to both.

For example, if a source file defines:

```python
class User(o.T):
	name: str
```

then after source loading the public shadow field room should contain `name` as an ordinary public field room entry.

That allows later runtime acts like:

```python
User._.name.description = 'Human readable full name'
```

without needing a separate field ontology for source-defined fields.

---

## 10. Source markers on fields

Source-origin should be stored at the field room itself.

Current preferred direction:

- each source-origin field room contains an empty marker file `__is_source__`
- runtime-origin fields do not have that marker

So a field room may look like:

```text
__fields__/
	name/
		type
		default
		__is_source__
	age/
		type
		description
		__is_source__
	nickname/
		type
```

Meaning:

- field exists = public field exists
- `__is_source__` exists = source-origin field
- `__is_source__` absent = runtime-origin field

This is preferred over a single central source-field list because:

- provenance stays attached to the field itself
- it is easier to inspect by eye
- there is no risk of central provenance state drifting away from actual field rooms
- existence of an empty marker file is a natural binary disk invariant

---

## 11. Reconciliation law

On source-backed class load, the plugin should reconcile source declarations into the public field room.

The law is:

- if source defines a field, that field must exist publicly
- if a public field has `__is_source__` and no longer exists in source, delete that field room
- if a public field has no `__is_source__`, it is runtime-origin and should remain

So reconciliation should do the following:

1. collect current source field declarations
2. for every current source field:
   - create or update the public field room
   - ensure `__is_source__` exists
3. for every existing public field room with `__is_source__`:
   - if the field no longer exists in source, delete it
4. leave runtime-origin fields untouched

Meaning:

- source still has deletion authority over source-origin fields
- source does not silently delete runtime-origin fields

---

## 11.1 `disk.Class.reconcile(source_cls)`

The preferred direction is to implement reconciliation on `disk.Class` itself.

Current intended API:

```python
o.disk.Class.reconcile(source_cls)
```

where `source_cls` is the privately loaded source class.

This is preferred because:

- disk entities are now cached, so opening the class room in the plugin and later in class materialization is not a conceptual problem
- reconciliation belongs to the class room more naturally than to ad hoc plugin code
- the plugin can stay focused on interception and public-shadow assembly

Important layer boundary:

- disk entities must not modify runtime wrappers, source classes, shadow classes, or public objects
- `disk.Class.reconcile(...)` may reconcile disk rooms and return the reconciled `disk.Class`
- it must not attach attributes such as `__disk_class__`, `__proto__`, `id`, `_`, or `__annotation__` to Python classes
- wrapper/class mutation belongs above the disk layer, for example in `TMeta`, `Fields`, or plugin code

Meaning:

- disk layer owns representation
- materialization layer owns wrappers
- reconciliation crosses data from source into disk, not behavior from disk into Python objects

The reconciliation method should do the following:

1. inspect `source_cls.__mro__`
2. find the first class in MRO that has `__proto__`
3. treat that class as the public parent anchor
4. derive the target public proto from that parent anchor and `source_cls.__name__`
5. derive the public class room path from that proto
6. instantiate or reopen the corresponding `disk.Class`
7. reconcile source fields into that room

Meaning:

- source classes themselves do not carry public `__proto__`
- public `o` classes do
- therefore the first `__proto__` in MRO is the nearest public base under which the shadow class should be created

This is a useful side effect of ordinary Python inheritance:

- base classes are already loaded in MRO
- no separate source-to-shadow parent mapping is needed

So the base-resolution law becomes:

- walk MRO
- first class with `__proto__` wins

---

## 11.2 Proto and path derivation

The public class room should be placed by public proto lineage, not by the hidden source class object directly.

Current intended derivation:

- public base proto comes from the first MRO class with `__proto__`
- public child proto becomes:

```python
f'{base_cls.__proto__}.{source_cls.__name__}'
```

Then path can be derived from proto using existing `o` geometry.

This is already supported by current code:

- `o.proto_to_path(proto)` can derive the class room path from proto
- `o.disk.Entity.__init__` already accepts proto-like input and resolves path from it
- `o.disk.Class.get(proto)` already uses this geometry

So reconciliation does not need a new path language.

The intended practical flow is:

1. derive public proto
2. derive room path from that proto
3. append the class room name through normal proto geometry
4. instantiate or reopen the corresponding `disk.Class`
5. reconcile fields there

Meaning:

- ontology placement is still proto-based
- storage placement remains existing folder geometry
- hidden source authority does not get to decide public room placement directly

---

## 12. Source-field props law

A field that originated in source may still receive runtime-added props on the public shadow class.

Example:

- source declares `name: str`
- runtime adds `description`

Then the public field should still be one field:

- origin = source
- extra props = persisted in the public field room

If the source field later disappears from source:

- because the field is marked `__is_source__`
- the whole field room is removed
- runtime-added props on that field disappear together with it

This is the chosen deletion law.

Meaning:

- field origin belongs to source
- public props may grow at runtime
- source removal kills the whole source-origin field

---

## 13. No split public field ontology

The public shadow class must not treat source-defined fields and runtime-defined fields as different kinds of public fields.

They should all behave uniformly at the public layer.

So:

- both live in `__fields__`
- both can expose field props through `o.F`
- both can participate in class-side field access

The only difference is provenance:

- source-origin fields have `__is_source__`
- runtime-origin fields do not

That keeps the public field world uniform while preserving reconciliation law.

---

## 14. Runtime field addition law

When a runtime field is added to a public shadow class:

- it is added into the same public field room
- it is not marked `__is_source__`
- it survives future source reload unless explicitly deleted

So source-backed and non-source-backed public field additions share one disk surface.

This means the public shadow class is the writable class face regardless of whether hidden source authority exists.

---

## 15. Source class never in proto chain

Although the source class may appear in Python `__bases__` or `mro()`, it must not appear in public `o` proto chain.

That means:

- no public proto segment for the source class
- no public `o.get(id)` result returning the source class
- no public `o.T.Name` result returning the source class

The public proto chain belongs to the shadow class only.

So the ontological chain and the Python inheritance chain are allowed to differ.

---

## 16. Instance birth law

Instances should be born from the shadow class.

Meaning:

- constructor calls happen on the public shadow class
- public field set comes from the shadow class
- source methods still participate through inheritance
- persisted instance identity belongs to the public shadow lineage

So the user never works with instances of the raw source class as public beings.

---

## 17. Summary formulas

- source class = hidden authority
- shadow class = public class entity
- route = hidden source re-entry, not public identity
- public field room stores full visible field surface
- source-origin field = field room contains `__is_source__`
- runtime-origin field = field room does not contain `__is_source__`
- source disappearance deletes only source-origin fields
- runtime fields survive source reload
- `TMeta` should become unaware of source-backedness
- plugin owns source loading and reconciliation

---

## 18. Current implementation direction

The intended implementation direction is:

1. add an `o` plugin that intercepts source-backed class loading before A publishes a raw Python class as the public face
2. privately load the source class from route
3. reconcile source field declarations into the public `disk.Class` field room
4. mark copied source fields with `__is_source__`
5. create or reopen the shadow class with the source class in `bases`
6. publish only the shadow class into public `o` identity surfaces
7. simplify `TMeta` so it only materializes the public class and does not carry source-backed policy

This is the current target architecture.
