# Architecture: Public API of O

**Status:** Normative boundary for applications; observation coverage describes the current implementation and must be verified by tests.
**Companion:** [Read Tracker and storage write invalidation](architecture.tracker.md).
**Sources:** `o.py`, `root/t.py`, `root/t_meta.py`, `root/v.py`, `root/list.py`, `root/dict.py`, `root/services/tracker.py`, `root/services/memory.py`.
**Related:** [Fork architecture](architecture.fork.md), [Tree mode](tree_mode.md).

## Foundational rule

> **Application code MUST access persistent O state through the documented public object API only. Bypassing it voids the Tracker dependency guarantee.**

**Public API is a necessary condition, not a magic guarantee for every exported method.** The read-only Tracker observes documented read boundaries. Persistent write notifications originate at O storage boundaries, not in Tracker. A reactive result requires both a verified read dependency and matching committed-write invalidation; unverified operations must be tested or excluded from automatic subscriptions.

In particular, a Python-visible method is not automatically a supported *application* API just because it is named `get`, `set`, or appears under `o.services`.

## Layers and ownership

```text
Application controllers
    |
Application services             business logic; only public O objects
    |
O public object API              o.V, o.T fields, o.List, o.Dict, modeled types
    |
O internals                      Entity, Id, Cache, Route, Memory, Zone, LMDB
    |
Persistent storage
```

Application controllers orchestrate services. Application services read and modify O through public objects. The web framework owns tracking scopes, dependency bookkeeping and subscriptions. The underlying O services are implementation details except for explicitly documented infrastructure interfaces such as `o.services.Tracker.track_reads(ids)`.

Trusted server infrastructure may require administrative APIs (authorization, migrations, storage operations). **Administrative use must not be mistaken for dependency-safe application data access.**

## Public API: ordinary applications

### Initialize and select a world

```python
import o

o.start()
other = o.fork('other')
other.start()
```

Each started ontology and fork has separate runtime state, classes, service instances and persistence. Numeric entity IDs must be qualified by their ontology when aggregating dependencies from multiple worlds. See [architecture.fork.md](architecture.fork.md).

### Declare data and access the persistent graph

```python
Finance = o.T.extend('Finance', salary=int)
Employee = o.T.extend('Employee', finance=Finance)

employee = Employee(finance=Finance(salary=200000))
o.V.employee = employee

salary = o.V.employee.finance.salary
o.V.employee.finance.salary = 250000
del o.V.employee
```

`o.T.extend(...)` defines persistent types; `o.F(...)` supplies field metadata, type and defaults. Class/field declarations and migrations are **schema operations** and are distinct from normal instance field access.

`o.V` is the persistent application root. Application code reads and writes declared instance fields with Python attribute syntax. The current implementation also permits dynamic root fields and class-level field changes; those are schema-changing operations and warrant separate observation tests.

Inside a read-tracking scope, each normal field read records the **ID of the object owning that field**. Persistent assignments and deletions notify affected owners through Memory/Zone writes. Deep nesting works when the corresponding dependency and committed-owner notification are both covered; ordinary field access need not propagate every child change to all ancestors.

`entity.id` is a persistent identity, **not a state dependency**. Reading only `id`, `type(entity)`, or other Python metadata does not mean that the underlying content was read.

### Persistent collections

```python
people = o.List([employee])
by_name = o.Dict({'alice': employee})

first = people[0]
count = len(people)
all_people = list(people)

present = 'alice' in by_name
lead = by_name['alice']
all_keys = list(by_name.keys())
all_pairs = list(by_name.items())

people.append(employee)
by_name['alice'] = employee
del by_name['alice']
```

Normal list and dictionary access, iteration, membership, length and mutators use the persistent collection contract. Tracker reads the **collection owner's ID** when its item index is accessed. Structural saves persist through O storage and notify that collection ID there, not through a Tracker write hook. This permits invalidation for insertions and removals even when a new child was absent on the previous read.

Reading `employee.finance.salary` after retrieving `employee` from a collection also registers the nested finance object's ID. Mutating the nested salary later invalidates that read even if the collection's own items did not change.

A collection can contain references, and tree mode imposes additional ownership restrictions. The tracking identity model is the same for graph and tree ontologies; topology-specific mutations still require tests. See [tree_mode.md](tree_mode.md).

## Read dependencies and committed write notifications

`Tracker.track_reads(ids)` collects read-owner IDs only. Write-owner IDs are supplied explicitly by O at persistence boundaries and passed to an optional IPL callback. These are distinct mechanisms; their identities must agree for a reactive result to become invalidated correctly.

| Operation family | Read dependencies via Tracker | Write invalidation via O persistence |
| --- | --- | --- |
| Instance fields | Owning instance ID on cached and uncached reads | Instance zone writes notify the owning instance ID |
| `o.List` / `o.Dict` | Collection ID for index, iteration, length and membership reads | Persisted collection changes notify the collection ID |
| `to_data()`, `to_data_shallow()`, `to_json()` | Converted receiver and, where traversed, nested receiver IDs | Underlying stored owners provide invalidation IDs |
| `serialize()` and `to_tree()` | IDs of serialized/rendered nodes | Relevant stored owners are notified; custom render dependencies need separate verification |
| `Class.__instances__()` | Class ID, even for empty enumeration | Instance creation/deletion notifies the class ID; changed instance state notifies its own ID |
| `Class.__subclasses__()` | Parent class ID | Class creation/deletion notifies its parent class ID |
| `Entity.exists(id/proto)` (infrastructure) | Requested/prospective ID; coarse root ID for route queries | ID mappings, lifecycle and route changes notify affected identities |
| Class schema and reflection | Read coverage is incomplete | Class/schema storage changes notify the owning class ID |

`Entity.exists` is infrastructure-facing despite Tracker instrumentation. O's `Memory`/`Zone` APIs are also internal and are not ordinary application-facing data APIs.

The read-only Tracker does **not** intercept assignments, deletions, entity construction, class changes, collection saves, or route writes to collect a separate write list. These operations report their owners through `MemoryBatch`. Atomic entity membership enumeration, certain reflective reads, custom callbacks, and specialized operations still require coverage tests.

**Interception does not mean every read path is fully observable.** Missing fields, class schema, authorization and operations outside the instrumented boundaries need separate verification.

## Public transformations and reflection: important limits

O exposes convenience APIs such as:

- `entity.to_data()`, `entity.to_data_shallow()`, `entity.to_json()`, `entity.to_tree()`
- `entity.serialize()`, `SomeType.deserialize(spec)`
- `SomeType.to_json_schema()`, `SomeType.to_prompt_schema()`, `SomeType.to_prompt()`
- `SomeType.has_persistent_instances()`, `entity.drop()`
- Python scalar operators on O atomic values

These may be useful and public, **but their complete reactive semantics have not all been proven**. Public `to_data()`, `serialize()` and `to_tree()` are observed through conversion/traversal boundaries, avoiding extra tracking in internal garbage collection. Direct atom conversion, custom render callbacks, schema reflection and operations outside those boundaries remain outside verified read coverage. `drop()` produces persistence-level invalidations for deleted entities and affected membership owners; full lifecycle and reference coverage still needs dedicated tests.

If a service wants a fully reactive result today, prefer reading and composing normal object fields and collections explicitly. If a higher-level public method is needed, add observation and a read/change/re-read regression test before depending on it for subscriptions.

## Disallowed application access

An application service claiming automatic dependency/invalidation correctness **MUST NOT** bypass public objects using:

- `o.services.Memory` or LMDB reads/writes, zones, disk keys, `__zone__`, `__items__`, `__key_ids__`, or `__value__`
- `o.services.Entity.get()/value()/cast()`, `o.services.Id`, `o.services.Cache`, `o.services.Route` to read or mutate domain state directly
- `object.__getattribute__`, `object.__setattr__`, direct `__dict__` inspection or mutations to bypass normal persistent field access
- Direct invocation of internal `__read__`, `__write__`, `__cast_in__`, `__cast_out__`, `__save_items__`, `__load_items__` and similar lifecycle/storage hooks

Some internals are intentionally called **by O itself** while executing public operations; that is legitimate. The restriction applies to application code crossing the abstraction boundary.

The fact that `Tracker` itself may use internal O facilities to instrument an operation does not grant application code permission to do so.

## Reactive correctness condition

Let `R` be owner IDs observed while computing one result, and `W` be owner IDs **confirmed after a committed mutation**, within the same ontology world:

```text
A change capable of changing the result must intersect its prior
read dependencies, or the result can remain stale.

          result_before != result_after
                   implies
                   R_before ∩ W_committed != ∅
```

This is a necessary correctness condition, not a claim that all public transformations already satisfy it.

`Tracker` collects **reads only** and does not determine transaction success. `MemoryBatch` calls `ipl.pre_invalidate(owner_id)` during writes, then calls `ipl.invalidate()` once **after** a successful outermost commit when at least one owner was notified. Pre-invalidation alone is not proof of a commit; rollback sends no confirmation. IPL must distinguish these phases. The PR supplies local callbacks, not a verified IPC transport or Web 4.0 subscription implementation.

Each infrastructure write supplies an explicit owner ID or iterable of affected IDs; `0` denotes full invalidation for unknown ownership. `Zone` usually supplies its cached owner ID, with an optional per-operation override. `Memory` does not parse LMDB key names to derive identities. Deleting a missing key or an empty prefix emits no notification. These facilities remain **internal** rather than part of the application object API.

Nested write scopes share a transaction. A nested failure poisons the outer write even if the nested exception is caught. Failed writes roll back LMDB and clear tracked Zone write caches. Internal reads through `Memory` during an active write see pending writes and deletions. If final IPL confirmation raises, the database remains committed and O raises `RuntimeError('LMDB committed; IPL confirmation failed')`. Callers must not treat this as a rollback.

When a valid committed invalidation intersects the previously observed IDs, the consuming layer may re-execute its computation under read tracking and **replace** the dependency set. The dependency lifecycle, network transport and reconnect/revision behavior belong to consumers, not to Tracker itself.

Coverage must be established **with tests**, including initially absent fields, empty collections/enumerations, nested references, class changes and tree-mode authorization. These gaps are recorded rather than silently represented as guarantees.

## Verification and performance

Relevant tests and benchmarks:

- `root/tests/test_tracker.py`: read instrumentation, cached/uncached fields, collections, nested scopes, threads/tasks and forks.
- `root/tests/test_tracker_transparency.py`: public behavior with no read tracking versus `'r'`.
- `root/tests/test_tracker_public_api.py`: traversal, empty enumerations, lifecycle dependency intersections and existence checks.
- `root/tests/test_write_tracking.py`: explicit write owners, IPL callbacks, commit/rollback boundaries and write-cache recovery.
- `root/tests/_test_performance_tracker.py`: compare `none` with `r`, not removed `w`/`rw` modes.
- `root/tests/_test_performance_write_tracking.py`: compare no IPL with local no-op IPL callbacks; network IPC is outside the benchmark.

Tracker read interceptors remain **temporary**. Outside active read scopes original Python descriptors must be restored. IPL write notifications are independent of Tracker scopes. A new feature must be verified for both read dependencies and committed write-owner coverage before claiming reactive correctness.

See [architecture.tracker.md](architecture.tracker.md) for read instrumentation, storage notification contracts and transaction caveats.
