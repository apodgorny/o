# Architecture: O Transport — local inter-process invalidation

**Status:** Host-local Unix Domain Socket transport. No TCP or distributed store.

## Responsibility

O already owns the application-level contract:

- `Memory` reports changed owner IDs when writes commit.
- `Sync` coalesces those IDs and dispatches subscriptions.
- `Cache` invalidates existing O entities without changing identity.

`Transport` only carries invalidation sets between processes. It never reads or transfers LMDB values. It subscribes with `Sync.subscribe(Transport.send, local_only=True)` and forwards only locally originated invalidations. Incoming messages call `Sync.receive(ids)`: the Sync worker invalidates the local cache, then notifies ordinary subscribers without echoing those messages.

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

On initial connection, O clears its local cache before `o.start()` returns. If the daemon disconnects, clients reconnect, notify local Sync with `None`, and send `None` to peers to repair possibly missed invalidations.

## Wire protocol

The first frame registers the canonical LMDB directory path; the daemon acknowledges with `true`. Every subsequent frame is either a JSON list of positive owner IDs or `null` (full invalidation):

```text
client -> daemon: "/canonical/ontology/path"
daemon -> client: true
client -> daemon: [42, 57]
daemon -> peers:  [42, 57]
client -> daemon: null
daemon -> peers:  null
```

Frames are newline-separated JSON; the path is bound to the connection and is not repeated in later frames. The daemon relays a message only to other clients registered for that pathname. Clients connected to the same pathname **must actually share the same LMDB database**.

The relay uses nonblocking `selectors`, bounds input/output buffers, and validates message types. It does not read or authorize database contents; access to LMDB is controlled separately.

## Guarantees and limitations

- Notifications are **invalidation hints**, not snapshots or proofs of commit. Existing `Sync` speculative fallback signals can also be forwarded.
- Delivery is asynchronous and **not durable**. Reconnection prompts a full invalidation, but there is no persistent replay or exact once-only guarantee.
- Existing local subscribe/unsubscribe semantics remain unchanged.
- This transport works between processes on **one host**. Across containers, the Unix socket directory and the actual LMDB files must be shared and correctly permissioned; merely running a daemon inside an ephemeral application container does not give it a host-independent lifecycle.
- TCP, cross-host consistency, deployment orchestration, and storage sharding are outside this feature.

## Validation

`root/tests/test_transport.py` verifies relay publication, cache invalidation before subscription callback, absence of notification loops, and ontology-path isolation. Existing `root/tests/test_sync.py` continues to verify in-process transaction semantics.

The separate daemon is intentionally infrastructure code; it never imports O.
