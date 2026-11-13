# Architecture: O Transport — local inter-process invalidation

**Status:** Host-local Unix Domain Socket transport. No TCP or distributed store.

## Responsibility

O already owns the application-level contract:

- `Memory` reports changed owner IDs when writes commit.
- `Sync` coalesces those IDs and dispatches subscriptions.
- `Cache` invalidates existing O entities without changing identity.

`Transport` only carries invalidation sets between processes. It never reads or transfers LMDB values. Remote notifications enter `Sync.receive(ids)`, invalidate the local cache, and notify subscribers without broadcasting the same message again.

## Layout

```text
o/
├── o.py
├── root/
│   ├── services/
│   │   ├── sync.py
│   │   ├── cache.py
│   │   └── transport.py  # Almasi O.Transport service
│   └── tests/
│       └── test_transport.py
└── daemons/
    └── transport.py      # standalone relay process, not an O carrier
```

The service derives the daemon script path from its own `__file__` with `os.path`. The editable/source layout must be retained; the repository's current setuptools `py-modules` packaging is not yet a complete standalone wheel distribution of the Almasi `root/` namespace.

## Startup and lifetime

`o.start()` initializes `Transport` after `Sync`, `Memory` and ontology classes. The first client starts the daemon if its Unix socket is absent. A nonblocking OS file lock prevents simultaneous processes from creating competing relays. Other clients connect to that same socket.

The daemon stops approximately three seconds after the final client disconnects. It is a normal subprocess, not a second O ontology or an Almasi service. The socket directory defaults to a private directory named `o-transport-<uid>` beneath `tempfile.gettempdir()`. `O_TRANSPORT_DIR` may specify a shared, private directory for a deployment; it must be owned by the calling UID and inaccessible to group/other users.

On initial connection, O synchronously refreshes its caches before `o.start()` returns. If the daemon later disconnects, clients reconnect and enqueue ID `0`, which invalidates all subscriptions and clears potentially stale caches after missed messages.

## Internal wire protocol

One JSON array per newline-terminated frame:

```text
client -> daemon: ['join', canonical_ontology_path]
daemon -> client: ['ready', canonical_ontology_path]
client -> daemon: ['change', canonical_ontology_path, [id, ...]]
daemon -> peers:  ['invalidate', canonical_ontology_path, [id, ...]]
```

The arrays above describe the message schema; on the wire they use JSON double-quoted strings.

Each client has one registered ontology. The daemon broadcasts only to other clients registered under the same `os.path.realpath()` pathname. The integer `0` means full invalidation and supersedes other IDs. Each client must see the **same LMDB database** at that canonical pathname, not merely have an equal pathname inside an isolated container.

The relay excludes the sender, coalesces duplicate IDs per message, rejects malformed frames, and bounds per-connection buffers. Socket file permissions are restrictive. The daemon does not authorize access to ontology data; LMDB access and permissions are controlled outside this transport.

## Guarantees and limitations

- Notifications are **invalidation hints**, not snapshots or proofs of commit. Existing `Sync` speculative fallback signals can also be forwarded.
- Delivery is asynchronous and **not durable**. Restart/reconnection prompts a full invalidation, but there is no persistent replay or exact once-only guarantee.
- Existing local subscribe/unsubscribe semantics remain unchanged.
- This transport works between processes on **one host**. Across containers, the Unix socket directory and the actual LMDB files must be shared and correctly permissioned; merely running a daemon inside an ephemeral application container does not give it a host-independent lifecycle.
- TCP, cross-host consistency, deployment orchestration, and storage sharding are outside this feature.

## Validation

`root/tests/test_transport.py` verifies relay publication, cache invalidation before subscription callback, absence of notification loops, and ontology-path isolation. Existing `root/tests/test_sync.py` continues to verify in-process transaction semantics.

The separate daemon is intentionally infrastructure code; it never imports O.
