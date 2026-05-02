# Garbage Collection Invariants

## Core Idea

Garbage Collection is fully centralized in `o.services.Garbage`.

Classes and instances must not contain any GC logic beyond emitting lifecycle events (link/unlink).

---

## 1. Slot-based Refcount Consistency

- Every slot (attribute, list item, dict entry) represents an independent holding edge.
- When a slot is removed or replaced:
  - The child receives a corresponding `__unlink__()` call.
- If the same object is stored multiple times:
  - It receives multiple unlink calls.
  - Refcount is decremented correctly for each edge.

---

## 2. Garbage Instead of Immediate Deletion

- When `__refcount__` reaches `0`:
  - The object is NOT immediately deleted.
  - It is placed into Garbage storage:

```
garbage:<proto>
```

- Garbage storage is managed exclusively by `o.services.Garbage`.

---

## 3. Refcount Ownership

- All refcount operations are centralized:
  - increment
  - decrement
  - read
  - write

- These operations must go through `o.services.Garbage`.

- Classes must not:
  - store lifecycle logic
  - decide collectability
  - perform deletion

---

## 4. Garbage Drain Triggers

### 4.1 On `del`

- On every `del` call (class or instance):

```
if Garbage is not empty:
    clear Garbage
```

- This guarantees:
  - no accumulation
  - bounded cleanup latency

---

### 4.2 On Restart

- On system startup:

```
clear all Garbage
```

- Ensures:
  - clean state
  - no leftover dead objects

---

## 5. Separation of Concerns

- Classes:
  - define structure
  - emit lifecycle events (link/unlink)

- Garbage Service:
  - owns refcount
  - owns collectability
  - owns deletion
  - owns garbage storage

---

## Summary

```
slots define edges
edges define refcount
refcount == 0 -> move to garbage
garbage cleared on:
    - every del
    - restart
```
