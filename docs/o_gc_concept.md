# GC concept in `o`

## Core principle

GC in `o` is not a standalone tracing system.
It piggybacks on trusted Python object lifecycle mechanics, specifically `__del__`.

---

## Concept

1. GC in `o` is local, not global.
   No graph traversal.
   No mark-sweep.

2. When a Python wrapper object loses its last reference, Python calls `__del__`.

3. Inside `__del__`, the persistent record is explicitly released through the proper service path.

4. Release must:
   - mark the record non-active
   - zero out its stored bytes
   - return the id to the corresponding free heap

5. The lifecycle of the Python object and the persistent disk record are synchronized.

6. No background process is required.

7. No separate reachability scan is required.

8. Determinism is preserved:
   destruction happens when the wrapper dies.

9. Cascading deletion belongs to container logic, not to GC itself.

10. System invariant:
    if there is no live Python wrapper, the disk record must not remain active.

---

## Design philosophy

The goal is maximum reuse of trusted mechanisms:

- Python reference counting
- deterministic finalizers through `__del__`
- explicit service-side deletion

Instead of building a second garbage collector, `o` delegates object liveness to Python itself.

This keeps the storage model minimal, predictable, and aligned with runtime semantics.

---

## Summary

GC in `o` is not a collector.
It is a lifecycle synchronization contract.
