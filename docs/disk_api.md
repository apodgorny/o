# `core/disk` lookup

## Folder structure

```text
<class_path>/
	__fields__/
		<field_name>/
			<property_name>

	__subclasses__/
		<ClassName>/

	__instances__/
		__index__
		_<n>/
			__attributes__/
				<field_name>
			__list__      # list instance only
			__dict__      # dict instance only
			__value__     # atomic instance only
```

## `entity.py`

| Signature | Returns / does |
| --- | --- |
| `class Entity(o.Module)` | Base disk entity with stable `id` from path and registry binding. |
| `Entity.__init__(self, path=None)` | `None` ; sets `id`, `path`, registers entity path. |
| `Entity.__del__(self)` | `None` ; removes entity id from registry if still present. |
| `Entity.load(cls, id)` | `o.disk.Instance | o.disk.Class | o.undefined` ; resolves disk entity by registry id. |

## `class.py`

| Signature | Returns / does |
| --- | --- |
| `class Class(o.disk.Entity)` | Disk class room with field, subclass, and instance managers. |
| `Class.__init__(self, path)` | `None` ; creates class folder, attaches managers, and exposes `annotation` / `o_module`. |
| `Class.annotation` | `annotation | o.undefined` ; class annotation persisted as string form and read back through `o.Annotation`. |
| `Class.o_module` | `str | o.undefined` ; lawful source-backed world address persisted in `__o_module__`. |

## `instance.py`

| Signature | Returns / does |
| --- | --- |
| `class Instance(o.disk.Entity)` | Disk instance room with optional list, dict, atomic, and attributes managers. |
| `Instance.__init__(self, path, annotation=o.undefined)` | `None` ; creates room and materializes managers from annotation or existing files. |

## `fields.py`

| Signature | Returns / does |
| --- | --- |
| `class Fields(o.Module)` | Manager for `__fields__` directory under a class room. |
| `Fields.__init__(self, class_path)` | `None` ; loads existing field managers from disk. |
| `Fields._get_field_path(self, field_name)` | `str` ; returns folder path for one field. |
| `Fields.set(self, field_name)` | `o.disk.Field` ; creates or returns field manager by name. |
| `Fields.get(self, field_name)` | `o.disk.Field | None` ; returns cached field manager if present. |
| `Fields.has(self, field_name)` | `bool` ; checks whether field manager exists. |

## `field.py`

| Signature | Returns / does |
| --- | --- |
| `class Field(o.Module)` | Manager for one field folder and its string properties. |
| `Field.__init__(self, fields_path, name)` | `None` ; creates field folder and stores its path. |
| `Field._get_prop_file_path(self, prop_name)` | `str` ; returns property file path inside field folder. |
| `Field.set(self, prop_name, value=None)` | `None` ; writes field property text, empty if `None`. |
| `Field.get(self, prop_name)` | `str | None` ; reads field property text if file exists. |
| `Field.remove(self, prop_name)` | `None` ; deletes field property file if present. |
| `Field.has(self, prop_name)` | `bool` ; checks property file existence. |

## `subclasses.py`

| Signature | Returns / does |
| --- | --- |
| `class Subclasses(o.Module)` | Manager for `__subclasses__` directory under a class room. |
| `Subclasses.__init__(self, parent_path)` | `None` ; loads existing capitalized subclass names. |
| `Subclasses.set(self, name)` | `o.disk.Class` ; creates or returns subclass disk room. |
| `Subclasses.get(self, name)` | `o.disk.Class | None` ; returns cached subclass room if loaded. |
| `Subclasses.has(self, name)` | `bool` ; checks whether subclass name is present. |

## `instances.py`

| Signature | Returns / does |
| --- | --- |
| `class Instances(o.Module)` | Manager for `__instances__` sequence and room birth order. |
| `Instances.__init__(self, parent_path)` | `None` ; loads count and live order from `__index__`. |
| `Instances._get_index_path(self)` | `str` ; returns `__index__` file path. |
| `Instances._get_instance_path(self, version)` | `str` ; returns room path like `_<n>`. |
| `Instances.set(self, count, order)` | `None` ; writes count and live order back to disk. |
| `Instances.create(self, annotation)` | `o.disk.Instance` ; creates next instance room with explicit visible annotation. |
| `Instances.remove(self, version)` | `None` ; removes version from live order without deleting room. |
| `Instances.get(self, name)` | `o.disk.Instance | None` ; reopens room by underscored name if it exists. |

## `attributes.py`

| Signature | Returns / does |
| --- | --- |
| `class Attributes(o.Module)` | Manager for `__attributes__` name -> child id files. |
| `Attributes.__init__(self, instance_path)` | `None` ; creates directory and indexes existing attribute files. |
| `Attributes.set(self, name, id)` | `None` ; writes one child id under attribute name. |
| `Attributes.get(self, name)` | `int | None` ; reads cached or on-disk child id by name. |
| `Attributes.has(self, name)` | `bool` ; checks whether attribute entry exists. |

## `list.py`

| Signature | Returns / does |
| --- | --- |
| `class List(o.Module)` | Manager for `__list__` ordered child ids. |
| `List.__init__(self, instance_path)` | `None` ; creates list file if needed and loads ordered ids into `__items__`. |
| `List.items` | `list[int]` ; whole ordered id state. Setter rewrites full file. |
| `List.get(self, index)` | `int | None` ; returns child id at index if in range. |
| `List.set(self, index, id)` | `None` ; updates one index in cached items and rewrites file. |

## `dict.py`

| Signature | Returns / does |
| --- | --- |
| `class Dict(o.Module)` | Manager for `__dict__` key-id -> value-id mapping. |
| `Dict.__init__(self, instance_path)` | `None` ; creates dict file if needed and loads id pairs into `__items__`. |
| `Dict.items` | `dict[int, int]` ; whole mapping state. Setter rewrites full file. |
| `Dict.get(self, key)` | `int | o.undefined` ; returns value id by resolved key token. |
| `Dict.get_key_id(self, key)` | `int | o.undefined` ; resolves persisted key id from incoming key token. |
| `Dict.set(self, key, id)` | `None` ; updates one cached pair and rewrites file. |

## `atomic.py`

| Signature | Returns / does |
| --- | --- |
| `class Atomic(o.Module)` | Manager for atomic `__value__` raw bytes. |
| `Atomic.__init__(self, instance_path)` | `None` ; stores value file path and lazy cache. |
| `Atomic.set(self, value)` | `None` ; writes raw bytes and refreshes cache. |
| `Atomic.get(self)` | `bytes | o.undefined` ; returns cached or on-disk raw bytes. |
