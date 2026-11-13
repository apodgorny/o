# Architecture: Tracker — persistent read dependencies

**Status:** Implemented read dependency tracking. The separate Sync service owns write-owner notification delivery; browser transport belongs to consumers.
**Sources:** `root/services/tracker.py`, `root/services/memory.py`, `root/services/sync.py`, `root/t.py`, `root/t_meta.py`, and the O persistence services.
**Tests:** `root/tests/test_tracker.py`, `root/tests/test_tracker_public_api.py`, `root/tests/test_tracker_transparency.py`, `root/tests/test_write_tracking.py`.
**Benchmarks:** `root/tests/_test_performance_tracker.py`, `root/tests/_test_performance_write_tracking.py`.
**Companions:** [Public O API](architecture.public_api.md), [Sync delivery](architecture.sync.md).

## Mandatory application API boundary

> **Applications use the documented public O object API for persistent domain state.** Direct access to `Memory`, `Zone`, `Entity`, `Id`, `Cache`, `Route`, LMDB, `__zone__`, `__items__`, or raw atomic storage bypasses the application's automatic dependency/invalidation guarantee.

The public API is necessary but does not guarantee complete reactive coverage for every exported method. Only verified operations and matched read/write owner identities qualify for automatic dependency-based subscriptions. See [architecture.public_api.md](architecture.public_api.md).

`Tracker` is a documented infrastructure interface. `Memory` and `Zone` are internal persistence interfaces for O and trusted infrastructure, **not** application-domain APIs.

## Two independent responsibilities

- **Tracker:** observes reads of persistent O objects while a caller-owned scope is active, recording owner entity IDs in caller-supplied lists.
- **Memory/Zone/Sync:** persist O changes and asynchronously deliver explicit affected-owner IDs, independently of Tracker scopes or Python read interception.

The intended coherence relationship is **read dependency ID ↔ committed write owner ID** within the same ontology world. Neither a read trace nor a pre-commit notification is, by itself, a complete subscription system.

## Read Tracker public API

```python
import o

ids = []

with o.services.Tracker.track_reads(ids):
	result = o.V.some_field

print(ids)
```

- `track_reads(ids)` is the only read-tracking entry point; it has no `mode` parameter and no write-tracking counterpart.
- `ids` must be a Python `list`, otherwise a `TypeError` is raised.
- IDs are **appended** in access order with duplicates retained. The `ids` list is owned by the caller; the tracker neither clears nor deduplicates it.
- Tracking is opt-in; only accesses inside the scope are recorded. There is no `o.track_reads(...)` shortcut.
- Normal usage requires an already started ontology (`o.start()`).

### Fields and collections

```python
Person = o.T.extend('TrackerDocPerson', name=str)
person = Person(name='Alex')
items  = o.List([1, 2])
prefs  = o.Dict({'theme': 'light'})
ids    = []

with o.services.Tracker.track_reads(ids):
	person.name
	items[0]
	len(items)
	prefs['theme']

# The owning person, list and dict IDs can appear in ids.
```

A field read records the owning instance ID. List/dictionary item-index operations record the collection ID rather than the ID of an atomic child. Reading a nested child's own field also records that child's ID.

Assignments may occur inside a read scope, but **there is no separate write trace**. Reads performed as part of mutation logic may still appear in `reads`.

### Nested scopes

```python
outer = []
inner = []

with o.services.Tracker.track_reads(outer):
	person.name

	with o.services.Tracker.track_reads(inner):
		person.name

# outer sees both reads; inner sees its nested read.
```

Each active scope for the current thread or async task receives matching reads. Scopes may overlap, and the last exiting scope restores the original descriptors. An exception does not leave a completed scope's tracking installed.

## Read interception mechanism

Tracker temporarily installs only the instrumentation needed to observe reads:

- **Fields:** `DynamicClassAttribute` intercepts cached accesses and cache misses while preserving normal set/delete behavior without logging writes.
- **Collections:** descriptors around `__items__` observe list/dictionary indexing, iteration, membership and length; dictionary membership also uses `Dict.__contains__` interception.
- **Dynamic fields:** `TMeta.__publish_field__` instruments fields published while tracking is active.
- **Conversion:** public `to_data()` and `to_data_shallow()` calls record their receivers; nested conversion records the traversed entities. `to_json()` uses the data conversion path.
- **Serialization and rendering:** `Serializer._serialize_instance()` and `Tree._render_node()` observe participating entities.
- **Class enumeration:** `Class.__instances__()` and `Class.__subclasses__()` record their owning class, including an empty result.
- **Existence checks:** `Entity.exists(...)` tracks a requested/prospective identity, or the root identity for route-style queries. This is infrastructure observation, not a general application API.

Original class attributes/descriptors are restored when the last read scope closes. No write interceptors are installed on `T.__setattr__`, `T.__delattr__`, collection saves, constructors, class mutators, or route operations.

Direct atom conversion, some schema reflection, custom rendering callbacks and administrative authorization remain outside fully verified read coverage. Observing a method does not prove that every dependency of an arbitrary computation is recorded.

## Storage write notifications belong to Sync

The O persistence layer reports **explicit changed-owner IDs** to its
`Sync` service. Tracker does not determine those IDs, intercept writes,
manage subscribers, or interpret transaction state. Owner ID `0` requests
a full invalidation when ownership is unknown.

The former `Memory.ipl`, `pre_invalidate()` and `invalidate()` callback
API **no longer exists**. Current infrastructure calls
`Sync.register_change(txn_id, owner_id)` inside the write transaction;
`Sync.register_change_commit(txn_id)` follows a successful outer commit,
while `Sync.register_abort(txn_id)` handles rollback. Only code inside O
persistence may use these producer methods; application services use the
public persistent object API.

Ordinary Sync notifications arrive after commit, but long-running writes
may emit a **speculative fallback invalidation** before commit; a later
rollback cannot retract it. A callback is therefore **not** evidence of
commit. See [architecture.sync.md](architecture.sync.md) for worker
lifecycle, filtered subscriptions, batching, fallback and error behavior.

## Event and correctness semantics

Read traces contain integer owner IDs in access order; they are not property names, full values, JSON paths or change records. They do not represent a log of committed changes.

For a previously calculated result with read IDs `R`, and a later **committed** change with affected owner IDs `W`, the necessary coherence condition within one ontology is:

```text
result_before != result_after  =>  R_before ∩ W_committed != ∅
```

A consumer receiving an intersecting invalidation can re-run its
computation under read tracking and **replace** its dependency set.
Speculative Sync notifications must be treated as hints to refetch, not
committed values. Tracker does not own subscriptions, result caching,
network delivery, reconnection or replay.

## Forked ontologies

Each fork has distinct ontology classes, services, caches and LMDB. Always use the tracker belonging to the world being read:

```python
import o

alice = o.fork('alice')
alice.start()

Person = alice.T.extend('TrackForkPerson', age=int)
person = Person(age=20)
ids    = []

with alice.services.Tracker.track_reads(ids):
	age = person.age

assert ids == [person.id]
```

Numeric IDs must be qualified by ontology identity when aggregating dependencies across forks. A tracker for one world does not observe another world's entities.

## Concurrency of read observation

The installation/removal of read interceptors is protected by an `RLock`. Active output lists are scoped to a thread or the current `asyncio.Task`; `ContextVar` is not used. Each async task requiring observation opens its own scope. A task without one does not append to another task's trace, although globally installed descriptors can add dispatch overhead while another scope is active.

This describes **Tracker observation scope isolation**, not thread safety of arbitrary `Memory` transactions.

## Benchmarks

```bash
# Read tracking overhead: default 5 rounds, 10,000 iterations, graph mode.
py root/tests/_test_performance_tracker.py

# Only the supported modes: none and r.
py root/tests/_test_performance_tracker.py --mode r --workload expanded
py root/tests/_test_performance_tracker.py --size 1000 --rounds 2

# Compare native Sync with a no-op producer stub.
py root/tests/_test_performance_write_tracking.py --size 1500 --rounds 3 --sync native
py root/tests/_test_performance_write_tracking.py --size 1500 --rounds 3 --sync stub
```

The Tracker benchmark retains `none` and `r` as **measurement labels** (or `all`), not arguments to `Tracker.track_reads(ids)`; there are no `w`/`rw` tracker modes. The write benchmark compares local Sync behavior with a stub; it does **not** measure MCP or network latency. Measurements use fresh storage.

## Verification and limits

```bash
py root/test.py
```

- `test_tracker.py`: cached and uncached field/collection reads, nested scopes, field publication, exception cleanup, async/thread observation and fork isolation.
- `test_tracker_public_api.py`: structural reads, conversion, enumeration, lifecycle dependency intersections and existence checks.
- `test_tracker_transparency.py`: normal behavior with no tracking versus `'r'`, including failure and schema/mutation cases.
- `test_write_tracking.py`: explicit owner IDs, Sync calls, outer commit confirmation, rollback, nested failures, Zone-cache recovery and post-commit confirmation errors.
- `test_sync.py`: filtered subscriptions, full invalidation, speculative fallback, concurrency, worker behavior and shutdown.

The functional read-tracking contract is observation without changing the ordinary public object's results, mutations or persistence. Temporary instrumentation does change class introspection (`__dict__`, descriptor identity, `inspect.getattr_static(...)`) while active, so that introspection is outside the transparency claim.

**Non-goals:** Tracker does not register subscriptions, observe writes, perform value-level diffs, implement network IPC, or coordinate Web 4.0 rendering. The consuming layer must apply the documented dependency condition and handle the lifecycle of subscriptions and updates.
