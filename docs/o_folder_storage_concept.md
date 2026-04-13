# `o` as Folder-Based Storage Concept

## Core Ontology

There are two structures:

- **`IS-A`** — ontology / form / inheritance
- **`HAS-A`** — retention / liveness / ownership

Things are garbage-collected if nobody **`HAS-A`** them.

Folder structure belongs to **`IS-A`**.

If multiple things `HAS-A` the same thing, this is like beautiful **hard-links**.

So:

- **`IS-A`** is a tree of form
- **`HAS-A`** is a graph of retention

## Entity and File Distinction

An `o.Object` is a **folder**.

Items within are **instances**, therefore they are also **folders**.

Files are just **files**.

So:

- entity = folder
- attachment = file

A child entity is not a file.
A file is not an `o` entity.

## Addressing

The whole `HAS-A` structure is represented by elements of the `IS-A` tree.

This is the idea behind notation like:

- `foo[12]`

Instances live as elements of the ontology tree.

## Storage Shape

Actual data can be stored as files within the entity folder.

- class metadata lives under reserved class-side folders
- instance data lives inside the instance folder itself
- attachment files may be dropped in directly if desired

Current instance-side files are:

- `__value__` for atomic value state
- `__list__` for ordered refs
- `__dict__` for keyed refs
- `__attributes__/` for named attribute refs

## Names and Indices

For container entries:

- **name** is the key for named entries
- **index** is the key for ordered entries

But Linux folders themselves do not provide meaningful reorderable list order.
So folder order must not be relied on for list behavior.

## Instance Files and `__index__`

A workable shape is:

- `__list__` — stores ordered instance refs
- `__dict__` — stores keyed instance refs
- `__value__` — stores atomic instance ref
- `__attributes__/` — stores named attribute refs
- `__instances__/__index__` — stores class instance count and live order

Meaning:

- instance-side files store per-instance shape and refs
- `__instances__/__index__` stores the class-side instance catalog

## List Behavior

List-like instance behavior can exist **only if** ordering is stored explicitly, not derived from filesystem order.

So list behavior comes from `__list__`, not from the order Linux returns directory entries.

## Class vs Instance Distinction

Subclass and instance are both folders / entities, but they are distinguished spatially.

A class folder should have a reserved subfolder:

- `__subclasses__/`
- `__instances__/`
- `__fields__/`

Then:

- capitalized child folders inside `__subclasses__/` are **subclasses**
- entries inside `__instances__/` are **instances**
- `__subclasses__/` is the subclass catalog manager folder
- `__fields__/` is the field manager folder

This means instances do not live in the same room as subclasses.

Instances are also a list-like structure.
So they should not be treated as ordered purely by folder names.

A workable form is:

- `__subclasses__/`
	- `<SubclassName>/`
	- `<SubclassName>/`
- `__instances__/`
	- `__index__`
	- `_<stable instance version>/`
	- `_<stable instance version>/`

So:

- subclass classes live as real child class folders inside `__subclasses__/`
- instance folders use stable underscored version ids
- list order of instances is held separately in `__index__`
- instance id is not the same thing as list position

This preserves list behavior without making reorder depend on renaming instance folders.

## Read / Write Model

The dominant operations are expected to be mostly:

- **read dir**
- **write dir**

This means the folder model is practical if the directory itself acts as the write unit.

The desired simplification is:

- **read / write only**

That is:

- minimize extra folder machinery
- avoid relying on extra directory behavior
- keep the system centered around direct read/write

## Performance Direction

The service becomes much simpler in this model.

The folder structure naturally provides namespace and placement.

The current model works if classes use:

- `__fields__/`
- `__subclasses__/`
- `__instances__/__index__`

## Inheritance

Inheritance will often amount to subtree copying, especially because generated properties created on object creation will often require it.

But the rule is:

- **copy only when required**
- and this applies to both **shape** and **data**

Not:

- always copy shape
- optionally copy data

But:

- copy shape only when required
- copy data only when required

It will be required often, but not always.

## Exactness Invariant

Disk must be an **exact replica** of what is materialized in memory.

Therefore:

- if something is materialized in memory, it must exist on disk correspondingly
- if something is not materialized, it does not need to be copied

This applies both to shape and data.

## Protected Invariant

**Simultaneity in order** is protected.

It must not be traded away for speed.

So acceleration is allowed only inside that invariant, not by weakening it.

## Summary Formula

- `IS-A` = tree of form
- `HAS-A` = graph of retention
- entity = folder
- attachment = file
- `__fields__` = field schema folders
- `__subclasses__` = subclass catalog
- `__instances__/__index__` = class instance order / indexing
- `__list__` = ordered instance refs
- `__dict__` = keyed instance refs
- `__value__` = atomic instance ref
- `__attributes__` = named instance refs
- copy only when required
- exact replica of materialized memory on disk
- simultaneity in order is protected
