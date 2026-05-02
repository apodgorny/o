# Garbage Collection Invariants

## Core Idea

Garbage Collection is fully centralized in `o.services.Garbage`.

Classes and instances must not contain GC logic beyond emitting lifecycle events.

---

## 1. Holding Edge Law

Every persistent slot is a holding edge.

Holding edges are also called **hands**.

Hands include:

- object attribute values
- list items
- dict keys
- dict values

Local Python variables are not persistent holding edges.

Therefore:

```text
persistent hands define refcount
local Python refs do not define refcount
```

---

## 2. Refcount Law

`refcounts` count direct persistent hands holding an instance.

If the same instance is stored multiple times, each slot counts independently.

Therefore:

```text
same instance in two slots -> refcount +2
remove one slot           -> refcount -1
```

Refcount is local to the held instance.

---

## 3. Boundary Propagation Law

Refcount propagation to `__dependants__` happens only when liveness crosses zero.

```text
0 -> 1  means instance becomes held
        propagate +1 to dependants

1 -> 0  means instance becomes unheld
        propagate -1 to dependants

1 -> 2  no propagation
2 -> 1  no propagation
```

This prevents duplicated hands on the same object from duplicating the whole dependency subtree.

Formula:

```text
slot multiplicity = local refcount
subtree liveness  = boundary propagation
```

---

## 4. Dependants Law

`instance.__dependants__` returns the direct instances held by this instance's own persistent hands.

Garbage propagation must go through `__dependants__` only inside `o.services.Garbage`.

Classes, containers, and instances may expose dependants, but they must not own propagation policy.

---

## 5. Garbage Storage Law

When an instance refcount drops to zero, it is not deleted immediately.

It is placed into garbage storage.

```text
refcount == 0 -> garbage.set(instance.id, instance.proto)
```

Garbage storage maps:

```text
garbage key   = entity.id
garbage value = entity.proto
```

The value is `proto` because physical cleanup uses prefix removal:

```text
Memory.unset_all(proto)
```

---

## 6. Link Law

On instance link:

```text
old_count = refcounts.get(instance.id, 0)
count     = old_count + 1

refcounts.set(instance.id, count)
garbage.unset(instance.id)

if old_count == 0:
    propagate link to instance.__dependants__
```

Meaning:

- every hand increments local refcount
- any new holding edge removes the instance from garbage
- dependants receive propagated link only when the instance becomes newly held

---

## 7. Unlink Law

On instance unlink:

```text
old_count = refcounts.get(instance.id, 0)
count     = max(old_count - 1, 0)

if count == 0:
    refcounts.unset(instance.id)
    garbage.set(instance.id, instance.proto)

    if old_count == 1:
        propagate unlink to instance.__dependants__
else:
    refcounts.set(instance.id, count)
```

Meaning:

- every removed hand decrements local refcount
- refcount does not go below zero
- zero-ref instances are marked as garbage, not immediately deleted
- dependants receive propagated unlink only when the instance becomes unheld

---

## 8. Temp Class Law

Temp classes are runtime-created unnamed classes.

A temp class has:

```text
cls.__is_temp__ == True
```

Temp classes cannot be subclassed.

If a temp class is used as a base, the system must raise.

Therefore a temp class can only be kept alive by its instances.

---

## 9. Temp Class Garbage Law

When a temp class is born, it is added to garbage immediately.

```text
temp class born -> garbage.set(cls.id, cls.proto)
```

When the first instance of a temp class is created, the temp class is removed from garbage.

```text
instancecount 0 -> 1 -> garbage.unset(cls.id)
```

When the last instance of a temp class dies, the temp class is returned to garbage.

```text
instancecount 1 -> 0 -> garbage.set(cls.id, cls.proto)
```

Non-temp classes do not participate in `instancecounts`.

---

## 10. Instancecount Law

`instancecounts` are only relevant for temp classes.

They are not general class instance statistics.

They are temp-class liveness counters.

```text
on temp instance create:
    instancecounts[cls.id] += 1

on temp instance delete:
    instancecounts[cls.id] -= 1
```

When count drops to zero:

```text
instancecounts.unset(cls.id)
garbage.set(cls.id, cls.proto)
```

---

## 11. Collection Law

Garbage is collected on `Garbage.initialize()`.

Collection means removing every stored memory room by proto prefix:

```text
for id, proto in garbage.items():
    Memory.unset_all(proto)

garbage.clear()
```

Startup collection is safe because local Python references do not survive restart.

---

## 12. Separation of Concerns

Classes and instances:

- emit lifecycle events
- expose dependants
- do not own GC policy
- do not propagate refcounts themselves
- do not decide collectability

`o.services.Garbage` owns:

- refcounts
- instancecounts for temp classes
- propagation through dependants
- garbage storage
- collection

---

## Summary

```text
hands define local refcount
refcount boundary crossings define dependant propagation
0 -> 1 propagates link
1 -> 0 propagates unlink
1 -> 2 and 2 -> 1 do not propagate

zero-ref instance -> garbage[id] = proto

temp class born -> garbage[id] = proto
first temp instance -> remove temp class from garbage
last temp instance -> return temp class to garbage

collect on initialize:
    unset_all(proto) for every garbage item
```
