# Architecture: Independent Ontology Forks

**Status:** Implemented in O, built on Almasi runtime forks.  
**Scope:** Explicitly started, independently persisted ontology worlds within one application.

## 1. Idea

An O fork is a **separate ontology world**: it has its own runtime types, entities, services, caches, and LMDB store. All worlds reuse the same O implementation and Almasi's filesystem-driven loader.

The two public operations intentionally have different jobs:

- `fork(name)` **selects or allocates** an isolated O runtime, without starting persistence.
- `start(...)` **opens or creates** that runtime's LMDB and initializes the ontology.

> Fork chooses a world. Start brings that world into operation.

This preserves explicit control of startup and avoids filesystem side effects when a fork is merely named.

## 2. Public lifecycle

These calls run after the Almasi application has been selected:

```python
import o

o.start()                  # Start the canonical/default ontology.

alice = o.fork('alice')    # Allocate a named world in memory.
alice.start()              # Open/create alice's LMDB and initialize O.

bob = o.fork('bob')
bob.start(tree_mode=True)  # A different world with its own topology mode.

assert o.fork('alice') is alice
assert o['alice'] is alice
assert o['default'] is o
```

The current startup signature is:

```python
o.start(sync: bool = False, tree_mode: bool | None = None, multiprocess: bool = False)
```

`start()` returns `None`; `fork(name)` returns a library instance. There is **no** public `path` argument.

**Not lazy startup:** `fork()` creates the in-memory namespace only. No LMDB is opened, no storage directory is created, and no ontology initialization occurs until the corresponding `start()` is called. Starting one fork does not start the others.

## 3. Automatic storage ownership

O determines persistence locations using the selected Almasi application:

```text
application directory (app.__lib_path__)
└── ontology/
    ├── default/
    │   └── LMDB environment
    ├── alice/
    │   └── LMDB environment
    └── bob/
        └── LMDB environment
```

The path calculation is:

```python
name       = o.__dict__.get('__fork_name__', 'default')
o.DATA_DIR = os.path.join(o.__app__.__lib_path__, 'ontology', name)
```

Here `o` means the **current fork-local O module binding** when called within that fork. `app.__lib_path__` is the directory containing the application's defining Python module, not the process working directory and not O's own source directory.

- `o.start()` uses `ontology/default`.
- `o.fork('alice').start()` uses `ontology/alice`.
- An existing directory is reopened; an absent LMDB is created on startup.
- The application root must be available via `o.__app__`. Otherwise `start()` raises `RuntimeError`.
- Paths are chosen internally by O. Calling `start(path=...)` is no longer supported.

Older architecture notes referring to caller-relative paths or `start(path=...)` describe the previous API. These paths are not automatically migrated into the new per-world layout.

## 4. Fork identity and name rules

O specializes Almasi's generic fork implementation in `Ontology.fork(name)`:

1. Validate the name as a single safe filesystem-directory component: a string other than `''`, `'.'`, or `'..'`, with no path separators.
2. Find an existing named world in the source registry; return it if present.
3. Otherwise allocate a fresh Almasi namespace, then bind its `start` and `fork` shortcuts to **its own** `Ontology` service.
4. Return the fork without initializing LMDB or loading its ontology data.

`o.fork('default')` resolves to the canonical/default O. Repeated `o.fork('alice')` is **idempotent**. That deliberately differs from generic `A.fork('alice')`, which raises on a duplicate name.

O resolves names against the source world for the current fork, rather than using Almasi's general-purpose nested-fork hierarchy. Application code should treat O names as distinct sibling ontology identities, not as nested database paths.

## 5. What is isolated

```text
             O source code / Almasi machinery
                         |
           +-------------+-------------+
           |             |             |
        default         alice          bob
           |             |             |
        O classes     O classes     O classes
        services      services      services
        caches        caches        caches
           |             |             |
         LMDB          LMDB          LMDB
       default/        alice/         bob/
```

Each started world has its own resolved O types (including `T`), service singletons (including `Memory` and notification `Sync`), entity/cache state, `TREE_MODE`, and on-disk LMDB data. A type created in one world does not thereby appear in another. A write to Alice's LMDB is not a write to Bob's.

Almasi provides runtime isolation through forked module globals, type identities, and service instances. O supplies its own startup and storage mapping. No source files, persistent records, or existing ontology graphs are copied by `fork()`.

## 6. What `start()` initializes

`Ontology.start()` orchestrates the complete world startup:

1. Verify that the active Almasi application exists; derive and assign the fork's absolute `DATA_DIR`.
2. Validate `tree_mode` (only `True`, `False`, or `None`).
3. Initialize `Cache` and the in-process `Sync` worker on first start, then initialize or reopen `Memory` using the selected LMDB path and durability `sync` policy. The existing Sync worker is retained on Memory reopen.
4. Read the stored `system/tree_mode` value and establish `o.TREE_MODE`; reject a conflicting explicit mode.
5. Initialize `Id`, `Route`, and `Garbage`.
6. Load ontology component classes; leave test-runner helper files outside fork startup.
7. Ensure the root value through `Entity.ensure_value()` and expose `o.V`.

On a subsequent explicit `start()` call, the Memory environment is reopened and loaded cache state is invalidated. Reopening is not an in-place switch of a live ontology's topology. Treat startup as a lifecycle boundary, not as an ordinary data operation.

`multiprocess=False` is the default and does not start the Unix socket transport. `multiprocess=True` enables the shared-host invalidation relay for the current ontology. Once started, Transport remains active until process exit: a later `start(multiprocess=False)` does not disable it. The choice to enable IPC is per fork and independent of LMDB durability `sync`.

## 7. Topology and durability are per world

### `tree_mode`

- New worlds use graph mode (`False`) if `tree_mode` is omitted.
- Explicit `tree_mode=True` creates a new tree-mode ontology.
- Existing worlds restore the recorded mode when `tree_mode=None`.
- Supplying a conflicting mode for an existing world raises `ValueError`.
- Legacy data with no recorded mode is treated as graph-mode data.

The persisted mode is stored in that world's LMDB under `system/tree_mode`.

### `sync`

- `sync=False` is the default: fewer disk flushes, higher throughput, weaker protection against OS/power-loss crashes.
- `sync=True` asks LMDB to synchronize commits for stronger crash durability.
- Each world can choose its policy when opened. Changing policy requires an explicit reopening, not a casual mutation of a config value.

LMDB's transaction guarantees remain distinct from whether a recent committed write survives a power failure. This `sync` parameter is unrelated to [O Sync change notifications](architecture.sync.md), which remain enabled.

## 8. Why `memory.py` did not change

`Memory.initialize()` already accepts the path selected by O and opens LMDB from `o.DATA_DIR`. The fork-aware Almasi module loader makes `import o` within fork-loaded `memory.py` resolve to that specific O world. Each fork consequently gets its own `Memory` class and singleton service.

The implementation boundary is intentional:

- `o.py` exposes the default `start` and `fork` service methods.
- `root/services/ontology.py` selects/reuses forks, binds methods, computes paths, and coordinates startup.
- `root/services/memory.py` continues to own LMDB opening and transactions **without fork-specific modifications**.

This keeps fork branching out of persistence hot paths.

## 9. Guarantees and non-goals

| Concern | Current contract |
| --- | --- |
| Calling `fork(name)` | In-memory allocation only; idempotent by name |
| Calling `start()` | Opens/creates the chosen LMDB and initializes O |
| Default world | Canonical `o`, storage under `ontology/default` |
| Named world | Its own classes, services, cache, and LMDB |
| Python source and Almasi runtime | Shared implementation |
| Application root | Shared, process-wide `a.__app__` selection |
| Copying existing world data | Not performed |
| Migrating old on-disk layout | Not performed |
| Cross-process cache invalidation | Not provided by this fork mechanism |
| Authorization / tenant boundaries | Application responsibility |

A fork is a strong organizational boundary for runtime and persisted ontology state, **not** by itself an access-control mechanism. Code holding references to several forks can access several worlds; isolate access at the application service/API layer.

## 10. Verification and related architecture

`root/tests/test_fork.py` exercises lazy allocation, repeatable named lookup, independent LMDB paths, service/type isolation, tree-mode separation, repeated startup, and cross-process persistence.

The key invariants are: **no disk I/O from fork allocation; each started name maps to its own persistent world; the same name selects the same in-process world.**

See [Almasi's generic fork architecture](https://github.com/apodgorny/almasi/blob/master/docs/architecture.fork.md) for the underlying loader, module-global isolation, service identity, and generic nested-fork behavior. Historical O docs (including `architecture_2026-11-07.md` and `tree_mode.md`) may still mention the superseded path-based startup signature.
