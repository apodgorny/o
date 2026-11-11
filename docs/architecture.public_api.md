# Architecture: Public API of O

**Status:** Normative boundary for applications; observation coverage describes the current implementation and must be verified by tests.
**Companion:** [Read/Write Tracker](architecture.tracker.md).
**Sources:** `o.py`, `root/t.py`, `root/t_meta.py`, `root/v.py`, `root/list.py`, `root/dict.py`, `root/services/tracker.py`.
**Related:** [Fork architecture](architecture.fork.md), [Tree mode](tree_mode.md).

## Foundational rule

> **Application code MUST access persistent O state through the documented public object API only. Bypassing it voids the Tracker dependency guarantee.**

**Public API is a necessary condition, not a magic guarantee for every exported method.** Tracker observes specific read and write boundaries. Operations outside the verified observable subset must either be instrumented and tested or be excluded from automatically reactive results.

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

Application controllers orchestrate services. Application services read and modify O through public objects. The web framework owns tracking scopes, dependency bookkeeping and subscriptions. The underlying O services are implementation details except for explicitly documented infrastructure interfaces such as `o.services.Tracker.track(...)`.

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

Each normal read of a tracked field records the **ID of the object owning that field**. Each successful assignment or deletion records that same owner ID. Deep nesting works without propagating writes up to parents, because access to each nested field observes its owner.

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

Normal list and dictionary access, iteration, membership, length and mutators use the persistent collection contract. Tracker reads the **collection owner's ID** when its item index is used and writes the same ID when the index changes via `__save_items__`. This catches insertions/removals even when the newly inserted child was absent during the previous read.

Reading `employee.finance.salary` after retrieving `employee` from a collection also registers the nested finance object's ID. Mutating the nested salary later invalidates that read even if the collection's own items did not change.

A collection can contain references, and tree mode imposes additional ownership restrictions. The tracking identity model is the same for graph and tree ontologies; topology-specific mutations still require tests. See [tree_mode.md](tree_mode.md).

## Current Tracker coverage

The following table describes what is actually intercepted by the current Tracker implementation, including the new experimental observation hooks. Atomic entity *membership enumeration* is not yet a fully reactive operation because births/deaths of atomic child values are deliberately excluded.

| Operation family | Current observed dependency | Notes |
| --- | --- | --- |
| Instance field read/write/delete | Instance ID | Cached and uncached values; missing field behavior is not yet a complete schema dependency |
| `o.List` / `o.Dict` reads and mutations | Collection ID | Normal indices, iteration, membership and structural saves |
| Public `to_data()`, `to_data_shallow()`, `to_json()` | Converted object ID, including nested `to_data()` receivers | Empty objects and nested conversion are observed; internal `__dependants__()` is not patched |
| Public `serialize()` and `to_tree()` | Each serialized or rendered O object ID | Observed at Serializer/Tree traversal boundaries; custom rendering logic may depend on external state |
| Persisted class instance enumeration `Class.__instances__()` | Class ID on read; class ID on construction/drop | An empty enumeration is observable |
| Subclass enumeration `Class.__subclasses__()` | Parent class ID | `Class.extend(...)` registers the parent on class extension |
| Entity existence `Entity.exists(id/proto)` | Requested/prospective entity ID | Infrastructure-facing; route-style queries use a coarse global identity |
| Successful non-atomic entity creation and deletion | New/deleted entity ID and its class ID | Atomic child births/deaths are intentionally excluded to protect common mutation performance |
| Class extension / field definition mutations | Affected class ID | Broad write observation; complete class-schema *read* coverage is not established |

**Interception does not imply that all possible code paths within a method are covered.** In particular, direct atomic-value reads, class schema reflection and administrative authorization APIs require further verification.

## Public transformations and reflection: important limits

O exposes convenience APIs such as:

- `entity.to_data()`, `entity.to_data_shallow()`, `entity.to_json()`, `entity.to_tree()`
- `entity.serialize()`, `SomeType.deserialize(spec)`
- `SomeType.to_json_schema()`, `SomeType.to_prompt_schema()`, `SomeType.to_prompt()`
- `SomeType.has_persistent_instances()`, `entity.drop()`
- Python scalar operators on O atomic values

These may be useful and public, **but their complete reactive semantics have not all been proven**. Public `to_data()`, `serialize()` and `to_tree()` are observed through their own conversion/traversal boundaries, avoiding extra tracking work in internal garbage collection. Direct atom conversion, custom render callbacks, schema reflection, and operations that do not invoke these boundaries remain outside the verified guarantee. `drop()` is observed through ID removal, but lifecycle and reference effects beyond the deleted entity/class require dedicated tests.

If a service wants a fully reactive result today, prefer reading and composing normal object fields and collections explicitly. If a higher-level public method is needed, add observation and a read/change/re-read regression test before depending on it for subscriptions.

## Disallowed application access

An application service claiming automatic Tracker correctness **MUST NOT** bypass public objects using:

- `o.services.Memory` or LMDB reads/writes, zones, disk keys, `__zone__`, `__items__`, `__key_ids__`, or `__value__`
- `o.services.Entity.get()/value()/cast()`, `o.services.Id`, `o.services.Cache`, `o.services.Route` to read or mutate domain state directly
- `object.__getattribute__`, `object.__setattr__`, direct `__dict__` inspection or mutations to bypass normal persistent field access
- Direct invocation of internal `__read__`, `__write__`, `__cast_in__`, `__cast_out__`, `__save_items__`, `__load_items__` and similar lifecycle/storage hooks

Some internals are intentionally called **by O itself** while executing public operations; that is legitimate. The restriction applies to application code crossing the abstraction boundary.

The fact that `Tracker` itself may use internal O facilities to instrument an operation does not grant application code permission to do so.

## Reactive correctness condition

Let `R` be the IDs observed while computing one result and `W` be the IDs of a later committed mutation, **within the same ontology world**:

```text
A change capable of changing the result must intersect the previously
observed dependency set, or the result may remain stale.

          result_before != result_after
                   implies
                   R_before ∩ W != ∅
```

The tracker collects access events; it does **not** determine whether a transaction committed. The consumer must publish invalidations after successful commit, discard rolled-back write traces, and account for changes made outside the tracked process or through external sources.

After an intersection, the web layer re-executes the service call under read tracking and **replaces** its dependency set. Thus newly reached children enter the next `R`; no global graph traversal is needed.

The coverage must be established **with tests**, including initially absent fields, initially empty collections/enumerations, nested references, class changes and tree-mode authorization. Those gaps are listed here instead of being silently represented as guarantees.

## Verification and performance

Relevant tests:

- `root/tests/test_tracker.py`: original field/collection observation and scope isolation
- `root/tests/test_tracker_transparency.py`: behavioral equivalence across `none/r/w/rw`
- `root/tests/test_tracker_public_api.py`: structural traversal, empty enumerations, births/deletions and existence checks
- `root/tests/_test_performance_tracker.py`: performance regression baseline

New observation hooks must remain **temporary and mode-selective**. Outside active Tracker scopes the original Python methods/descriptors must be restored. Adding a feature must not imply a zero-overhead promise without fresh measurement.

See [architecture.tracker.md](architecture.tracker.md) for the instrumentation mechanics and transaction limitations.
