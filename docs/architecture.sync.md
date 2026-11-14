# Architecture: Sync — owner-ID invalidation delivery

**Status:** Implemented in-process notification service; not an inter-process
transport or a durable event log.

**Sources:** `root/services/sync.py`, `root/services/memory.py`,
`root/services/ontology.py`.
**Tests:** `root/tests/test_sync.py`, `root/tests/test_write_tracking.py`.
**Related:** [Tracker](architecture.tracker.md),
[application object API](architecture.public_api.md),
[ontology forks](architecture.fork.md).

## Responsibility

Three separate owners provide reactive state:

1. **Tracker** records IDs of persistent objects *read* by a computation.
   It neither intercepts writes nor registers subscribers.
2. **Memory/Zone** persist changes and supply the affected owner IDs to
   **Sync**, independently of Tracker scopes.
3. **A consumer** (for example Web) owns the cached computation, its ID
   dependencies, subscription lifetime, refetch policy, and network delivery.

The necessary correctness condition within one ontology world is:

~~~text
result_before != result_after  =>  read_ids_before ∩ committed_write_ids != ∅
~~~

Tracking the public O object API and reporting corresponding write owners
are both necessary. Not every public transformation is fully observed;
see [architecture.public_api.md](architecture.public_api.md). Owner IDs
are identities, not property names, value diffs or snapshots.

## Startup, world identity, and naming

After the application has been selected via Almasi:

~~~python
import o

o.start()
sync = o.services.Sync
~~~

`Ontology.start()` initializes one Sync service/worker per world on first
startup; `Memory` binds to that world's Sync. An `o.fork('alice')` world
has a distinct Sync, classes, caches and LMDB. Numeric IDs must never be
mixed across worlds without qualifying world identity. Reopening an existing
world's Memory does not construct a new worker.

`o.start(sync=False)` is **LMDB disk-flush durability**. It does **not**
disable the `o.services.Sync` notification service. Likewise,
`tree_mode=None` restores the persisted topology mode (or defaults to
graph for a new world), independent of notifications. See
[architecture.fork.md](architecture.fork.md).

## Subscriber API

| Call | Contract |
| --- | --- |
| `sync.subscribe(callback)` | Observe every owner change |
| `sync.subscribe(callback=callback)` | Same, explicit keyword |
| `sync.subscribe({id1, id2}, callback)` | Observe only those owner IDs |
| `sync.subscribe(frozenset(ids), callback)` | Immutable-set variant |
| `sync.subscribe(callback, local_only=True)` | Notify only for changes originating in this process |
| `sync.publish_change(ids, local=False)` | Enqueue an external invalidation |
| `sync.unsubscribe(callback)` | Remove the callback from future deliveries |
| `sync.close()` | End worker lifetime; flush queued committed batches |

`subscribe` returns the **callback**, not a separate token.
Subscriptions are keyed by callback: registering the same callback again
**replaces its filter** rather than adding another listener. The ID input
must be a `set` or `frozenset`; it is snapshotted at registration, so
mutating the caller's set later has no effect. A filtered callback receives
only matching IDs; a global callback receives the full delivered batch.

All subscriptions run through one `_update()` delivery point. Ordinary subscribers
receive local and externally received changes. A `local_only=True` subscriber
receives only local changes; Transport uses this filter to publish IPC updates
without echoing incoming messages. Incoming changes are queued with `publish_change(ids, local=False)`,
invalidate the local cache, and then notify ordinary subscribers.

A filtered **empty** set receives no ordinary change events, but still
receives a full invalidation (`None`). Memory retains its existing internal
owner ID `0` for unknown affected owners; Sync converts it to `None` only
when delivering callbacks or sending notifications through Transport.
When full and specific invalidations combine, `None` supersedes the IDs.
Unsubscribing an unknown callback is harmless.

Callbacks receive `frozenset[int] | None` and execute on the **`o-sync` worker
thread**, not the writer's thread or an asyncio task. Cross-thread consumers
must hand off to their own loop, e.g. via
`loop.call_soon_threadsafe(...)`. Subscribers may safely subscribe or
unsubscribe during dispatch: the worker copies the current mapping while
holding a short lock, then invokes callbacks without the lock. A callback
exception is logged and other callbacks still run. Slow callbacks block
subsequent worker delivery, **not** the writer's transaction path.

Example of subscription-scope replacement around the initial tracked read:

~~~python
reads    = []
callback = sync.subscribe(on_change)     # Broad scope before first read

try:
	with o.services.Tracker.track_reads(reads):
		value = o.V.counter['count']

	sync.subscribe(set(reads), callback)  # Watch the actual owners
finally:
	sync.unsubscribe(callback)
~~~

This assumes `o.V.counter` and `on_change` already exist. It only
illustrates scope ownership, not a complete reactive consumer: application
infrastructure must handle in-flight invalidation, the read/listen race,
async handoff, overlapping refetches and replacing dependencies on every
recomputation. Web owns those mechanisms.

## Producer API (O infrastructure only)

Application code changes public O objects. `MemoryBatch` collects changed
owner IDs in a local list during each LMDB write transaction. Nested writes
share the same list, and failed transactions discard it.

After the outermost successful commit, `MemoryBatch` passes that complete
list to Sync in a single call, without copying or iterating it:

~~~python
sync.publish_change(ids, local=True)
~~~

The hot path only enqueues the list. The worker independently processes each
publication, deduplicates IDs within it, filters subscribers, and forwards
local events to Transport. Unknown owner ID `0` means full invalidation
(`None`) for listeners. Missing-key or empty-prefix deletions do not notify.

If publication fails after commit, the transaction remains committed and
`MemoryBatch` raises `RuntimeError('LMDB committed; Sync publication failed')`.
Sync is not a durable event log and cannot guarantee delivery if the process
crashes after committing.

## Worker and delivery timing

`Sync.initialize()` starts one worker. It blocks on `SimpleQueue.get()`
until a change arrives, without timers or polling. `publish_change(ids, local)`
enqueues one event without copying or processing IDs on the producer side.
There is no pre-commit speculative fallback.

- `local=True`: the worker normalizes IDs, informs matching local subscribers,
  and notifies Transport through its `local_only` subscription. It does not
  invalidate the writer's local object cache.
- `local=False`: the worker invalidates affected cached objects, then informs
  ordinary subscribers. It does not re-send the change through Transport.
- Each queued event is delivered independently, in publication order. The
  worker deduplicates IDs only within that event, treats ID `0` or `None` as
  full invalidation, and isolates callback failures.
- `close()` queues a shutdown sentinel after pending events and joins the worker.

A Sync callback signals that locally committed or externally announced owner
state may have changed, not that the subscriber has applied the change.
Consumers re-read committed state through O APIs.

## Verification and non-goals

- `test_sync.py`: filtered/global/empty subscriptions, scope replacement,
  None/full invalidation, worker-thread callbacks, publication ordering,
  commit visibility, no pre-commit publication, abort, concurrent producers,
  blocking queue delivery, reentrant and failing callbacks, blocked listeners, and close.
- `test_write_tracking.py`: actual field, collection, class and instance
  ownership; transaction nesting, rollback, Zone cache recovery and
  post-commit failure.
- `_test_performance_write_tracking.py --sync native` versus
  `--sync stub` compares native Sync with no-op producer callbacks, not
  distributed transport or browser latency.

Sync itself is **in-process, non-durable, non-replayable**. Optional Transport
provides host-local invalidation forwarding; Sync never references Transport
or owns its lifecycle. There is no revision ordering, authorization or UI
responsibility in Sync.
Consumers supply those capabilities where required. Web integrates it
through an optional injected pair `Tracker` / `Sync` without making O
depend on Web; see [Web MCP architecture](https://github.com/apodgorny/web/blob/master/docs/architecture.mcp.md).
