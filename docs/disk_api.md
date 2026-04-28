# `core/disk` and storage services

## Folder structure

```text
<data_root>/
	__registry__
	__refcounts__
	T/
		__fields__/
			<field_name>/
				<property_name>

		__subclasses__/
			<ClassName>/

		__instances__/
			_<n>/
				__attributes__
				__list__      # list instance only
				__dict__      # dict instance only
				__value__     # atomic instance only
```

`__registry__` and `__refcounts__` are binary service tables.
Entity rooms remain folder-based.

## `entity.py`

| Signature | Returns / does |
| --- | --- |
| `class Entity(o.Module)` | Base disk entity with stable `id` from `path` and registry binding. |
| `Entity.__init__(self, path_or_proto=None)` | Sets `path`, computes `id`, and registers `id -> path`. |
| `Entity.load(cls, id)` | `o.disk.Instance | o.disk.Class | o.Undefined` ; resolves disk entity by registry id. |

## `class.py`

| Signature | Returns / does |
| --- | --- |
| `class Class(o.disk.Entity)` | Disk class room with field, subclass, and instance managers. |
| `Class.__init__(self, path)` | Creates class folder, attaches managers, and exposes `annotation` / `route`. |
| `Class.annotation` | `annotation | o.Undefined` ; class annotation persisted as text and read back through `o.Annotation`. |
| `Class.route` | `str | o.Undefined` ; lawful source-backed world address persisted in `__route__`. |

## `instance.py`

| Signature | Returns / does |
| --- | --- |
| `class Instance(o.disk.Entity)` | Disk instance room with object attrs and optional list, dict, or atomic manager. |
| `Instance.__init__(self, path, annotation=o.Undefined)` | Creates room, materializes `attributes`, and reopens shape from annotation or existing files. |
| `Instance.delete(self)` | Removes the instance room from disk. Higher-level release work belongs to `o.services.GC`. |

## `fields.py`

| Signature | Returns / does |
| --- | --- |
| `class Fields(o.Module)` | Manager for `__fields__` under a class room. |
| `Fields.set(self, field_name)` | Creates or returns field manager by name. |
| `Fields.get(self, field_name)` | Returns cached field manager if present. |
| `Fields.has(self, field_name)` | Checks whether field manager exists. |

## `field.py`

| Signature | Returns / does |
| --- | --- |
| `class Field(o.Module)` | Manager for one field folder and its string properties. |
| `Field.set(self, prop_name, value=None)` | Writes one field property. |
| `Field.get(self, prop_name)` | Reads one field property if present. |
| `Field.remove(self, prop_name)` | Deletes one field property if present. |
| `Field.has(self, prop_name)` | Checks property presence. |

## `subclasses.py`

| Signature | Returns / does |
| --- | --- |
| `class Subclasses(o.Module)` | Manager for `__subclasses__` under a class room. |
| `Subclasses.set(self, name)` | Creates or returns subclass disk room. |
| `Subclasses.get(self, name)` | Returns cached subclass room if loaded. |
| `Subclasses.has(self, name)` | Checks whether subclass name is present. |

## `instances.py`

| Signature | Returns / does |
| --- | --- |
| `class Instances(o.Module)` | Manager for class instance rooms and live order. |
| `Instances.set(self, count, order)` | Rewrites class-side sequence state with next birth number and live order. |
| `Instances.create(self, annotation)` | Creates next instance room by append-only birth path. |
| `Instances.remove(self, version)` | Removes one version from live order without deleting the room itself. |
| `Instances.get(self, version)` | Reopens room by underscored version token if it exists. |

## `attributes.py`

| Signature | Returns / does |
| --- | --- |
| `class Attributes(o.Module)` | Manager for packed `__attributes__` name -> child id state. |
| `Attributes.set(self, name, id)` | Persists one attr edge, updates GC, returns old id or `o.Undefined`. |
| `Attributes.get(self, name)` | Returns child id by name. |
| `Attributes.delete(self, name)` | Removes one attr edge, updates GC, returns removed id. |
| `Attributes.has(self, name)` | Checks whether attr entry exists. |

## `list.py`

| Signature | Returns / does |
| --- | --- |
| `class List(o.Module)` | Manager for `__list__` ordered child ids. |
| `List.items` | `list[int]` ; whole ordered id state. Setter rewrites full file and updates GC by delta. |
| `List.get(self, index)` | Returns child id at index if in range. |
| `List.set(self, index, id)` | Replaces one child id, updates GC, returns old id. |
| `List.delete(self, index)` | Removes one child id, updates GC, returns removed id. |

## `dict.py`

| Signature | Returns / does |
| --- | --- |
| `class Dict(o.Module)` | Manager for `__dict__` key-id -> value-id mapping. |
| `Dict.items` | `dict[int, int]` ; whole mapping state. Setter rewrites full file and updates key/value GC by delta. |
| `Dict.get(self, key)` | Returns value id by resolved key token. |
| `Dict.get_key_id(self, key)` | Resolves persisted key id from incoming key token. |
| `Dict.set(self, key, value_id)` | Upserts one pair, updates key/value GC, returns old value id or `o.Undefined`. |
| `Dict.delete(self, key)` | Removes one pair, updates key/value GC, returns removed value id. |

## `atomic.py`

| Signature | Returns / does |
| --- | --- |
| `class Atomic(o.Module)` | Manager for atomic `__value__` raw bytes. |
| `Atomic.set(self, value)` | Writes raw bytes and refreshes cache. |
| `Atomic.get(self)` | Returns cached or on-disk raw bytes. |

## `services/registry.py`

| Signature | Returns / does |
| --- | --- |
| `class Registry(o.Service)` | Binary `id -> path` index for entity lookup. |
| `Registry.initialize(self)` | Creates or opens fixed-size `__registry__` table. |
| `Registry.add(self, id, dir_path)` | Persists one `id -> path` binding. |
| `Registry.remove(self, id)` | Clears one binding. |
| `Registry.get(self, id)` | Resolves directory path by `id` without allocating on read miss. |

## `services/g_c.py`

| Signature | Returns / does |
| --- | --- |
| `class GC(o.Service)` | Binary persistent refcount table and release service. |
| `GC.initialize(self)` | Creates or opens fixed-size `__refcounts__` table. |
| `GC.get(self, id)` | Returns persistent refcount. |
| `GC.set(self, id, count)` | Writes persistent refcount. |
| `GC.update(self, old_id, new_id)` | Replaces one ownership edge. |
| `GC.inc(self, id)` | Increments persistent refcount. |
| `GC.dec(self, id)` | Decrements persistent refcount and may trigger release. |
| `GC.get_children(self, id)` | Reads direct child ids from one entity room. |
| `GC.release(self, id)` | Releases one zero-ref non-root instance and cascades to direct children. |
| `GC.sweep(self)` | Releases zero-ref non-root instance rooms on startup. |
