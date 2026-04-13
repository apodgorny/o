# O Implementation Updates 1

## New concepts and invariants

- `Class` and `Instance` are distinct disk entities.
- `Class` and `Instance` both receive full `path` on init.
- `Class` creates its own directory on init.
- `Instance` creates its own directory on init.
- All disk managers now materialize their own storage on init.
- `Instances` creates `__instances__/` on init.
- `Instances` also guarantees `__instances__/__index__` exists on init.
- Empty `__instances__/__index__` is materialized immediately as `count = 0`, `order = []`.
- `Subclasses` creates `__subclasses__/` on init.
- `List` is a file manager for `__list__` inside an instance.
- `Dict` is a file manager for `__dict__` inside an instance.
- `Atomic` is a file manager for `__value__` inside an instance.
- `List`, `Dict`, and `Atomic` live only inside instance directories.
- An instance may have `__list__`, or `__dict__`, or `__value__`, or only `__attributes__/`.
- Instance structural files are determined by ontology, not by a universal fixed shape.
- On creation, `Instance` receives `annotation`.
- `annotation.is_list` causes materialization of `__list__`.
- `annotation.is_dict` causes materialization of `__dict__`.
- `annotation.is_atomic` causes materialization of `__value__`.
- Reload does not require passing `annotation`.
- On reload, `Instance` reconstructs itself from disk state.
- Annotation for runtime casting comes from the `o.T` subclass via `self.__annotation__`, not from the disk layer.
- `__proto__` is runtime metadata, not a persisted file.
- `__proto__` is reconstructed from folder position and order.
- Folder geometry is the source of truth for `__proto__`.
- `__o_module__` is the code location if applicable, not canonical identity.
- Source-backed class rooms may persist `__o_module__` in `__o_module__`.
- Runtime-defined classes do not persist `__o_module__`.
- Canonical identity is based on `__proto__`.
- Canonical id is `hash(__proto__)`.
- `o.services.Registry` stores softlinks by canonical id.
- Disk class vs instance distinction is determined by path shape.
- If the last path segment matches `_<digits>`, the entity is an instance.
- Otherwise, the entity is a class.
- This distinction is for disk path segments, not dotted proto text.
- Current approved `__fields__` layout is slot-first, then metadata.
- Canonical form is `__fields__/<slot_name>/<metadata_name>`.
- Example: `__fields__/age/description`.
- Previous metadata-first `__fields__` layout is no longer normative.
- Subclasses are materialized as real child class folders.
- `__subclasses__/` exists as the subclass catalog manager folder.
- Subclass classes are materialized inside `__subclasses__/`.
- Object instance values will live under `__attributes__/`.
- `__attributes__` is an instance-side directory.
- Each file inside `__attributes__` is named by attribute/slot name.
- File content in `__attributes__/<name>` is the referenced value id as binary `Q`.
- `o.disk.Attributes` is the manager for `__attributes__`.
- `Attributes` keeps an internal `dict` of `name -> id or None`.
- This `__attributes__` geometry is accepted for now as the lazy varsized object form.
- Atomic instances still use an instance directory.
- This is accepted for now as the uniform geometry, with possible optimization later.

## Implementation stage

Current approved implementation line:

- `o.disk.Entity`
  - stores `id` and `path`
  - registers `id -> path` in `o.services.Registry`
  - `load(id)` resolves path from registry
  - `load(id)` distinguishes class vs instance by last path segment `_<digits>`
  - `load(id)` reloads `o.disk.Class(path)` or `o.disk.Instance(path)` accordingly

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
  - on creation may receive `annotation`
  - always materializes:
    - `attributes = o.disk.Attributes(path)`
  - materializes instance-side managers according to ontology
  - may materialize:
    - `list = o.disk.List(path)`
    - `dict = o.disk.Dict(path)`
    - `atomic = o.disk.Atomic(path)`

- `o.disk.Fields`
  - manages `__fields__/`
  - canonical layout is slot-first then metadata

- `o.disk.Subclasses`
  - manages `__subclasses__/`
  - `set(name)` materializes subclass class folder
  - `get(name)` returns cached item from `items`

- `o.disk.Instances`
  - manages `__instances__/`
  - persists `count` and `order` in `__instances__/__index__`
  - creates new instance rooms by version/order id

- `o.disk.List`
  - manages file `__list__` inside an instance
  - public state: `items`
  - persists ordered refs as binary data
  - whole-state interface:
    - `items`
  - point interface:
    - `get(index)`
    - `set(index, id)`

- `o.disk.Dict`
  - manages file `__dict__` inside an instance
  - public state: `items`
  - persists key/value refs as binary `QQ` pairs
  - whole-state interface:
    - `items`
  - point interface:
    - `get(key)`
    - `set(key, id)`

- `o.disk.Atomic`
  - manages file `__value__` inside an instance
  - public state: raw bytes
  - persists atomic substance directly in `__value__`
  - public methods:
    - `set(bytes)`
    - `get()`

- `o.disk.Attributes`
  - manages `__attributes__/` inside an instance
  - file form: `__attributes__/<name>` -> `id` binary `Q`
  - public state: `items`
  - public methods:
    - `set(name, id)`
    - `get(name)`
    - `has(name)`

Current folder geometry:

```text
<Class>/
	__fields__/
		<slot_name>/
			<metadata_name>

	__subclasses__/
		<SubclassName>/
		<SubclassName>/

	__instances__/
		__index__
		_0/
		_1/
		_2/
```

```text
<Instance>/
	__list__          # only for list-like ontology
	__dict__          # only for dict-like ontology
	__value__         # only for atomic ontology
	__attributes__/   # for object slot values
		<name>          # file with referenced value id as binary Q
```

```text
Disk class / instance distinction:

.../<ClassName>     -> class
.../_12             -> instance
```
