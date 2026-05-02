# Lifecycle Invariants

## Instance Lifecycle

### Definitions

- **instance** — runtime embodiment of a class
- **__refcount__** — number of incoming holding relations from linked owners
- **dependants** — children reachable via HAS_A (attrs, list items, dict items)

### Laws

- `__refcount__ > 0  => alive`
- `__refcount__ == 0 => collectable`

#### On link

```
__refcount__ += 1
if 0 -> 1:
    propagate to dependants
```

#### On unlink

```
__refcount__ -= 1
if 1 -> 0:
    propagate to dependants
    delete instance
```

- Propagation happens only on threshold crossings (`0 ↔ 1`)

### Root

- `o.V.__refcount__ = 1` (constant)

---

## Temporary Classes Lifecycle

### Definitions

- **temp class** — runtime-defined class not yet stabilized by instances
- **instance_count** — number of live instances of the class
- **temp_classes** — session-scoped set of temp classes

### Laws

#### On creation

```
temp class -> add to temp_classes
```

#### On first instance

```
instance_count: 0 -> 1
=> remove from temp_classes
```

#### On last instance removal

```
instance_count: 1 -> 0
=> delete class immediately
```

#### On restart

```
delete all classes remaining in temp_classes
```

### Invariants

- `temp_classes` is a **birth shield only**
- Classes that have had instances are no longer protected
- No class returns back to `temp_classes`

---

## Persistent Classes

- Non-temporary classes are **not collectable by GC**

### Reason

```
they are reachable by name via __proto__
```

- Such classes must be deleted explicitly
- GC operates only on instances and temporary classes
