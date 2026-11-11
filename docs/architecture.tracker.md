# Architecture: Read/Write Tracker

**Status:** Implemented in `o.services.Tracker`.
**Source:** `root/services/tracker.py`.
**Tests:** `root/tests/test_tracker.py`; existing transition regression in `root/tests/test_instance.py`; `root/tests/test_tracker_public_api.py`.
**Benchmark:** `root/tests/_test_performance_tracker.py`.
**Companion contract:** [Public O API](architecture.public_api.md).

## Mandatory application API boundary

> **APPLICATIONS MUST USE ONLY THE PUBLIC O API TO QUALIFY FOR TRACKER DEPENDENCY GUARANTEES. Direct access to internal Entity, Id, Cache, Route, Memory, Zone, LMDB, `__zone__`, `__items__`, or raw atomic storage BYPASSES THE GUARANTEE.**
>
> **The public API alone is not proof of complete reactive coverage:** only operations documented as observed and verified are eligible for automatic dependency-based subscriptions. Unsupported public transformations or reflection paths must be covered by Tracker and tested before use as reactive data sources.

The authoritative list of application-facing operations, excluded internals, verified observation boundaries, and remaining limitations is in **[architecture.public_api.md](architecture.public_api.md)**. Both documents must be maintained together when Tracker's coverage changes.

## Purpose

`Tracker` observes access to persistent O objects while a caller-owned scope is active. It records **owner entity IDs** in ordinary Python lists, preserving access order and repeated IDs. The tracking mechanism is opt-in and does not require changes in domain classes, controllers, or the implementations of individual collection operations.

Outside tracking scopes, the temporary descriptors and collection wrappers are removed: ordinary cached field reads and collection methods use their original implementations.

## Public API

```python
import o

tracker = o.services.Tracker

with tracker.track('r', reads):
	...

with tracker.track('w', writes):
	...

with tracker.track('rw', reads, writes):
	...
```

| Mode | Read list | Write list |
| --- | --- | --- |
| `'r'` | Required | Not used |
| `'w'` | Not used | Required |
| `'rw'` | Required | Required |

The outputs must be Python `list` objects. They are owned by the caller and are **appended to**, not cleared or deduplicated. For mode `'w'`, the second positional argument is interpreted as the write list; `tracker.track('w', writes=writes)` is also supported. Invalid modes raise `ValueError`; missing/wrong output types raise `TypeError`.

**There is currently no `o.track(...)` shortcut.** Use `o.services.Tracker.track(...)`. The ontology should already have been started normally with `o.start()`.

## Examples

### Track dependencies when rendering a controller

```python
reads = []

with o.services.Tracker.track('r', reads):
	result = controller_get()

# In access order, including repetitions.
print(reads)
```

### Track writes in a command

```python
writes = []

with o.services.Tracker.track('w', writes):
	controller_set()

for entity_id in dict.fromkeys(writes):
	print('Written owner:', entity_id)
```

`dict.fromkeys(writes)` illustrates **optional downstream deduplication**, preserving first-seen order. `Tracker` itself keeps every recorded event.

### Observe both directions

```python
reads  = []
writes = []

with o.services.Tracker.track('rw', reads, writes):
	result = controller()

print('Read owners:', reads)
print('Written owners:', writes)
```

### Fields and collections

```python
Person = o.T.extend('TrackerDocPerson', name=str)
person = Person(name='Alex')
items  = o.List([1, 2])
prefs  = o.Dict({'theme': 'light'})
reads  = []
writes = []

with o.services.Tracker.track('rw', reads, writes):
	person.name
	person.name = 'Alexander'
	items[0]
	items.append(3)
	prefs['theme']
	prefs['theme'] = 'dark'

# person.id, items.id, and prefs.id can appear in the traces.
```

Collection events record the **container's ID**, rather than the atomic child ID. A field event records the ID of the object owning that field. Reading a child object's own field separately records that child's ID.

### Nested scopes

```python
outer = []
inner = []

with o.services.Tracker.track('r', outer):
	person.name

	with o.services.Tracker.track('r', inner):
		person.name

# outer contains both reads; inner contains only its nested read.
```

All matching active scopes receive an event. They are not exclusive to the innermost scope.

### Exceptions and cleanup

```python
reads = []

try:
	with o.services.Tracker.track('r', reads):
		person.name
		raise RuntimeError('Application failure')
except RuntimeError:
	pass

# Tracking has ended and temporary class patches are restored,
# assuming no other tracking scopes remain active.
```

## Mechanism

`Tracker` maintains separate read and write instrumentation groups. A group is installed when the first scope requesting that direction begins and removed when its last such scope ends. Overlapping `r`, `w`, and `rw` scopes therefore install the **union** of required interceptions. Restoring a group leaves the other direction active, and originally absent class attributes are deleted on cleanup.

- **Field reads (`r`/`rw` only):** install `DynamicClassAttribute` data descriptors. `__get__` catches cached reads in `instance.__dict__` and cache misses. Their `__set__` and `__delete__` transparently preserve the usual Python cache behavior, without reporting writes.
- **Field writes (`w`/`rw` only):** temporarily wrap `o.T.__setattr__`; successful assignments record the owning object's ID after normal persistence. Initial cache hydration uses `object.__setattr__` and is not counted as a write.
- **Field deletion (`w`/`rw` only):** a temporary wrapper around `o.T.__delattr__` registers a successful deletion, including when the field was not cached.
- **List/Dict reads (`r`/`rw` only):** temporary descriptors on `__items__` capture list and dictionary item-index reads. Dictionary membership (`key in mapping`) uses a temporary `o.Dict.__contains__` wrapper, avoiding a second index descriptor on ordinary dictionary lookup.
- **List/Dict writes (`w`/`rw` only):** a temporary wrapper around each class's existing `__save_items__` records structural changes. No patches to `append`, `pop`, `update`, `__setitem__`, or other individual operations are required.
- **Dynamic class publication (`r`/`rw` only):** a temporary wrapper around `o.TMeta.__publish_field__` instruments fields defined while read tracking is active.
- **Public data conversion (`r`/`rw` only):** temporary wrappers around `o.T.to_data()` and `to_data_shallow()` record the receiver, including empty objects; recursive conversion observes nested receivers. A wrapper around `Serializer._serialize_instance()` records each serialized O entity; `Tree._render_node()` similarly observes rendered O nodes. Internal `__dependants__()` remains unpatched to avoid imposing read overhead on garbage traversal during writes.
- **Class enumeration (`r`/`rw` only):** temporary wrappers around `o.TMeta.__instances__` and `__subclasses__` record the class ID even for empty results.
- **Entity existence (`r`/`rw` only):** a temporary wrapper around `Entity.exists` records the requested/prospective identity (or a coarse root identity for source routes).
- **Birth/death (`w`/`rw` only):** a wrapper around `o.TMeta.__call__` records successfully constructed non-atomic entity/class identities; an `Id.unset` wrapper records non-atomic removal and class membership changes. Atomic child births and removals are omitted to minimize the overhead of normal field/collection writes. These are candidate write events, not confirmed commits.
- **Class mutation (`w`/`rw` only):** wrappers around `o.TMeta.extend`, `__setattr__` and `__delattr__` observe public class/field mutation. Route registration changes record a coarse root identity for source-route existence queries.

Original class attributes and methods are stored separately for read and write interception, then restored when each group's reference count reaches zero. The previously existing `__on_change__` hook is not used.

## Event semantics and boundaries

- **Identity:** the lists contain `instance.id`, not a field name, key, index, value, or full change record.
- **Order and repetitions:** repeated operations remain in the result. No sorting or deduplication occurs.
- **Reads:** these are instrumented Python accesses to O field/collection indexes, including accesses performed internally by O. For example, an operation that writes a collection may also read its existing index in `'r'` or `'rw'` mode. Therefore read traces describe accesses, not necessarily only explicit application-level reads.
- **Field writes:** successful assignments are recorded by the temporary `T.__setattr__` wrapper, even if the assigned value equals the previous value. Successful field deletions are also recorded.
- **Collection writes:** the save wrapper compares before/after container indexes. A no-op save with unchanged indexes does not add a write ID.
- **Atoms:** O stores atomic children as entities but exposes Python primitive values on normal field/collection access. The observation is associated with the owning field/container. Direct internal access to an atom's `__value__`, or direct calls to `Entity.value(id)`, are not individually tracked.
- **Transactions:** this is an access trace, **not** a committed-change log. It does not automatically discard write events after a rollback. Consumers that publish changes should coordinate publication with successful transaction completion.
- **Public API coverage:** direct access to internal storage or entity resolution can bypass observation. Construction, structural traversal and class membership are additionally observed, but class schema reflection, direct atomic conversion, authorization and other specialized public paths still require verification. See [architecture.public_api.md](architecture.public_api.md).
- **Scope:** only operations executed while the context is active are added. The returned lists remain usable afterward.

## Forked ontologies

Each started O fork has its own ontology classes, services, caches, and LMDB. Use the Tracker **from the same fork** as the objects being observed:

```python
import o

alice = o.fork('alice')
bob   = o.fork('bob')

alice.start()
bob.start()

Person = alice.T.extend('TrackForkPerson', age=int)
person = Person(age=20)
reads  = []

with alice.services.Tracker.track('r', reads):
	age = person.age

assert reads == [person.id]
```

Scopes from two forks can be active simultaneously; a fork's Tracker instruments its own Python classes and does not observe objects belonging to another fork. Numeric entity IDs are meaningful **within** an ontology; if traces from multiple forks are aggregated, identify the world alongside each ID.

## Concurrency

Each direction of instrumentation is installed on shared Python classes under an `RLock`, and stays installed only while at least one scope requests that direction. Individual output lists are selected by **thread-local storage** for ordinary threaded execution, or by the current **`asyncio.Task`** for async execution; the service uses no `ContextVar`.

Each async task that needs its own trace should open its own `track(...)` context. Opening a context in a parent task does not implicitly subscribe child tasks. Because instrumented class attributes are shared, code executing without its own scope may still pay descriptor dispatch overhead while another task/thread is tracking reads, but it will not append to another task's lists. A write-only scope does not install read descriptors.

## Performance benchmark

**Recommended command — no flags necessary:**

```bash
py root/tests/_test_performance_tracker.py
```

Defaults: **5 rounds**, **10,000 iterations per workload**, the original **`legacy` workload**, **graph mode**, and **all four tracking modes**: `none`, `r`, `w`, `rw`. The benchmark executes each measurement in a separate Python process with an independent LMDB and alternates mode order between rounds. It reports median and min/max microseconds per iteration plus percentage overhead relative to `none`.

**Mode specialization:** `w` now installs **no read descriptors**, so its read-only workloads should approach `none`; `r` installs no write wrappers. These are predictions for the new implementation and require a fresh run to verify.

Optional commands:

```bash
# Separate attribute read/write and instance-creation workloads.
py root/tests/_test_performance_tracker.py --workload expanded

# Benchmark the tree-mode ontology instead of graph mode.
py root/tests/_test_performance_tracker.py --tree-mode tree

# Faster exploratory run.
py root/tests/_test_performance_tracker.py --size 1000 --rounds 2

# One mode and one profiling target.
py root/tests/_test_performance_tracker.py --mode rw --profile --profile-case dict_setitem
```

Tracking wraps the complete benchmark workload, while the original benchmark times operations independently of fixture construction. Results depend on hardware, Python version, and the selected workload; no speedup or slowdown should be assumed before measuring.

## Behavior transparency and verification

Tracker's functional contract is **observation without changes to ordinary ontology behavior**: when the same operations run with no tracking and with `r`, `w` or `rw`, they must return the same values, raise equivalent exceptions, mutate the same logical entities and persist the same data.

`root/tests/test_tracker_transparency.py` verifies this contract by executing the same operation scenarios in all four modes and comparing their results. The differential tests cover persistent fields and defaults; cached and uncached reads; list/dictionary built-in methods and mutations; error classes and messages; dynamic schema definition/removal and inheritance; reconstruction; and the resulting persisted values and item-index sizes.

**Introspection caveat:** the implementation deliberately replaces selected attributes of the Python class objects during a scope. Consequently, `Class.__dict__`, `inspect.getattr_static(...)`, method identity and performance are observably different until the scope ends. This is inherent to the temporary class-patching design and is **not** covered by the claim of functional transparency. No finite test suite proves equivalence for every conceivable Python operation or extension.

## Tests

```bash
py root/test.py
```

`root/tests/test_tracker_public_api.py` covers structural traversal, nested serialization, empty enumeration, entity birth/death, and missing-entity existence.

`root/tests/test_tracker.py` covers cached and uncached reads; field assignments and deletions; mode validation; class defaults/inheritance; dynamic class publication; list and dictionary reads/writes; cache reconstruction; mode-specific interception; mixed nested scopes; exception restoration; thread/async-task separation; and simultaneous tracking in independent ontology forks.

See also: `root/tests/test_instance.py` for the replacement regression test of field transitions via `Tracker`.

## Non-goals

`Tracker` is a low-level, reversible observation service. It does not implement subscriber registration, dependency graph maintenance, Web 4.0 event delivery, transactional publication, or value-level diffs. Those responsibilities belong to consumers that interpret the collected identity traces.
