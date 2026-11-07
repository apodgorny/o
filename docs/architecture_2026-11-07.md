# Architecture update — 2026-11-07

## Lifecycle and ownership

- `import o` publishes the Almasi-derived namespace via `a.extend('o')`; it does **not** open storage. Initialization remains an explicit application decision.
- `o.start(path=None, sync=False)` starts the ontology once: choose a storage path, initialize Cache → Memory → Id → Route → Garbage, load ontology classes, then ensure `o.V`. The default path is `ontology/` beside the caller's Python file; an explicit path takes precedence.
- `Ontology` owns startup orchestration; `Memory` owns the LMDB environment and transaction boundaries. Other services should not independently decide the durability policy.

| Responsibility | Service / type |
| --- | --- |
| Loaded entities and annotation → prototype mappings | `o.services.Cache` (`entities`, `cast_map`, `register`, `unregister`) |
| Entity resolution, casting, primitive value extraction | `o.services.Entity` |
| Deterministic identifiers and persisted ID → prototype mapping | `o.services.Id` |
| Persistent route metadata | `o.services.Route` |
| Persistent schema changes | `o.services.Migration` |
| LMDB persistence and nested read/write batches | `o.services.Memory` |
| References, unlinking and garbage collection | `o.services.Garbage` |
| Ontology class/instance lifecycle | `o.TMeta` / `o.T` |

Services have singular names (`Id`, `Route`, `Migration`); older `Ids`, `Routes`, `Migrations` names were retired. Persistent `ids/` and `routes/` prefixes were retained. Class-name and instance-version predicates now belong to `TMeta`. Application startup still uses `o.start(...)`, not import-time initialization.

## ID and mutation invariants

- `Id.hash(proto)` computes an identifier without I/O; `Id.set(proto)` persists its mapping. `TMeta.__getattr__` and initial class-ID calculation are read-only; class creation writes the mapping once.
- `T.__read__` reconstitutes an already persisted instance without writing its ID again.
- `Dict.__setitem__` reuses an existing persistent key instead of allocating a duplicate on every value update.
- Existing `Memory.write()` nesting shares a transaction. Changes above remove redundant work; they do not change entity identity, on-disk ID/route formats, or public container semantics.

## LMDB durability

```python
import o

o.start()                           # Fast default: sync=False
o.start('/path/to/ontology', sync=True)  # Alternative at startup: durable commits
```

The two calls are **alternatives for separate process starts**, not calls to make sequentially: services are initialized once. `sync=False` avoids forcing OS buffers to disk on every commit; a power failure or OS crash may lose recent commits and, depending on filesystem/write ordering, may corrupt the database. Normal transaction isolation is retained. `sync=True` requests per-commit disk synchronization and stronger crash durability. See [py-lmdb documentation](https://lmdb.readthedocs.io/en/latest/#environment-class). Changing policy requires reopening the environment, not calling `start()` again.

## Performance methodology and results

- `py root/tests/_test_performance.py` runs the **legacy** workload by default; `--workload expanded` additionally separates attribute reads/writes and creates instances. `--size N` controls iterations.
- Each run uses a disposable, empty LMDB; fixture creation is excluded. The default timer is wall-clock with internal method instrumentation disabled. `--instrumented` enables the `o.Timer` breakdown; inclusive nested method timings overlap and cannot be added.
- On macOS 14.5 / Python 3.11.14, one 5,000-iteration legacy run changed as follows after enabling `sync=False`:

| Scenario | `sync=True` | `sync=False` |
| --- | ---: | ---: |
| List item update | 5,166 μs/iter | 59.2 μs/iter |
| Dict item update | 3,862 μs/iter | 56.7 μs/iter |
| Two attribute reads + two writes | 8,122 μs/iter | 127.9 μs/iter |
| Class definition | 4,270 μs/iter | 149.4 μs/iter |

These are observed runs, **not** a guarantee or a rigorous multi-run comparison. The months-earlier BEFORE measurements used different workloads/instrumentation; compare historical revisions only under the same benchmark and storage policy. Fast `sync=False` results must not be presented as a code-only optimization.

## Cross-repository changes, tests, and recovery

- In `apodgorny/almasi`, the attribute-resolution cache required test-runtime cleanup in `test_service.py` and `test_module.py`. `lib/timer.py` now stacks same-name start times so recursive instrumentation does not overwrite the outer measurement.
- Added regression tests covering service layout, read-only ID lookup/reconstruction, registered new-class IDs and dictionary key reuse.
- Run `py root/test.py`, then the legacy and expanded performance workloads to validate a checkout. The changes listed here were reviewed structurally; benchmark outputs come from local runs, not CI validation in this session.
- Before the service refactor, the original `o` commit was preserved on [`backup-2026-11-07-before-services`](https://github.com/apodgorny/o/tree/backup-2026-11-07-before-services); `apodgorny/_o` also received a source snapshot (binary `.DS_Store` files excluded). The backup branch is the exact pre-refactor Git snapshot.
