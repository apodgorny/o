# o disk API Q&A resolution — 2026-03-27

## Purpose

Capture the high-level audit of the disk API after updated docs, the questions raised during the review, and the final resolutions that closed the disk-layer dev stage.

## Scope

This document captures only the conclusions of this Q&A session about the disk substrate.
It does not define `o.T` behavior beyond what was necessary to verify disk readiness.

## Initial audit result

The first audit found an apparent inconsistency because two storage lines were simultaneously present in project history:

- obsolete universal `Store` / packed record model
- current folder-based disk geometry model

This made the system look inconsistent for `o.T` until the obsolete `Store` line was explicitly discarded.

## Resolution: `Store` is obsolete

The `Store` line was declared obsolete and removed from consideration.

After that, the active disk substrate became the folder-based geometry only:

- `Class` and `Instance` are separate disk entities
- class shape lives in folder structure
- instance embodiment lives in folder structure
- folder structure is the source of truth

## Final answers and reasons

### Normative disk substrate for `o.T`

Final answer:

- the normative substrate is the folder-based disk geometry
- `Store` is obsolete

Reason:

- only the folder-based geometry remains load-bearing for the current architecture
- class and instance structure are derived directly from folders and their position

### Instance path format

Final answer:

- instance rooms use underscored notation everywhere: `_<digits>`
- examples: `_0`, `_1`, `_2`, ...
- loader recognizes instances by `_<digits>`

Reason:

- legal Python accessor form
- direct compatibility with wl/module-style loading
- one naming law across Python access, loading, and disk folders

Important distinction:

- semantic instance id remains numeric
- canonical folder/module token is underscored

### Disk token vs Python-only adapter

Final answer:

- underscore stays on disk too

Reason:

- regular wl loading can operate directly on the folder path
- avoids translation between Python name and disk token
- makes class/instance discrimination visually obvious

### Canonical wire format for refs in `__attributes__`

Final answer:

- `__attributes__/<name>` stores the entity id as binary `Q`
- more generally, refs are `Q`

Reason:

- all reference-bearing locations use the same numeric ref law
- avoids mixed text/binary ref semantics

### Instance form vs class form

Final answer:

- class owns form
- instance does not introduce new form
- instance stores local embodied values for class-defined slots

Reason:

- keeps shape explicit and single-sourced in class
- keeps instance behavior aligned with ordinary Python class/instance semantics
- keeps `__fields__` as shape and `__attributes__` as embodiment

### Effect of later class shape changes on old instances

Final answer:

- old instances immediately see new class fields through normal resolution
- no eager backfill or auto-materialization is performed on `get`

Reason:

- `o.T` uses real Python classes and instances
- class shape remains normative for all its instances

### Behavior of `get(name)`

Final answer:

- `get` performs resolution only
- `get` does not mutate
- materialization happens only through explicit writes or other explicit birth acts

Reason:

- read remains read
- instance storage contains only embodied values, not read side-effects

### Source of class/instance chain for loader

Final answer:

- folder structure is SOT
- all instances are subfolders of class
- the entire chain is available from folder position
- no extra persisted `proto` file is required for this purpose

Reason:

- folder geometry already contains the necessary structural truth
- loader can recover class/instance chain from position alone

## Final disk-layer invariants

The session closed with the following disk-layer invariants accepted:

- folder structure is SOT
- `Store` is obsolete
- `Class` and `Instance` are separate disk entities
- instance rooms are always `_<digits>`
- refs are always `Q`
- class owns form
- instance owns local embodied values
- `get` performs resolution only and does not materialize
- Python class/instance semantics remain normative for behavior
- folder geometry is sufficient to recover class/instance chain

## High-level verdict

Disk API is sufficiently consistent to clear the disk dev stage.

The remaining open implementation questions do not belong to disk geometry anymore and should be handled in `o.T`, including:

- exact Python object reconstruction in `o.T`
- container-kind restoration in `o.T`
- resolution order implementation in `o.T`
- single-wrapper / in-memory identity handling in `o.T`

## Resolution

Disk dev stage is cleared.

What remains is not a disk substrate question, but an `o.T` layer question.

