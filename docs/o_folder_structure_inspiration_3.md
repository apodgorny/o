# o folder structure inspiration 3

Supplemental to the previous folder-structure notes. This file captures the new discoveries from the current conversation.

## 1. Room state is `__version__` plus `__items__`

For ordered rooms, room state is not a single file anymore. It is the pair:

- `__version__` — the next birth number to issue
- `__items__` — the current ordered live set

For sequence-like rooms, it holds:

- `count` — the next birth number to issue
- `order` — the current ordered live set

This preserves history without forcing renumbering after deletion.

---

## 2. `count` is birth count, not live length

`count` does **not** mean how many live children currently exist.
It means the number of birth-slots already issued, or equivalently the next version id to issue.

So:

- create child → `version = count`, then `count += 1`
- delete child → remove version from `order`
- deletion does not change old birth numbers

This makes version ids stable enough to participate in canonical addressing.

---

## 3. Sequence should stay minimal

A good split was found:

`Sequence` should not pretend to be a full user-facing Python list.
It should only persist and expose the ordered room state.

So the minimal shape is:

- public `count`
- public `order`
- public `read()`
- public `write()`

Upper layers such as `o.List` will:

- compute the new order in memory
- mutate `sequence.order`
- mutate `sequence.count` if new births are issued
- call `sequence.write()` exactly once

This preserves the invariant that one logical list act can correspond to one disk write.

---

## 4. One logical list act must become one write

This became a major architectural split.

Operations such as:

- full list replacement
- slice replacement
- insertion of sublists
- deletions of slices

must not become several low-level writes if they are one logical act.

Therefore:

- list semantics belong in `o.List`
- room-state persistence belongs in `Sequence`

`o.List` computes the full resulting order, then commits it in one `write()`.

---

## 5. Instances are not the same thing as list positions

A critical distinction was found:

- instance birth order is stable
- list indexing is not stable

Therefore these must split.

### Positional access

```text
foo[12]
```

means current list position and is allowed to change.

### Canonical created-child access

```text
foo._12
```

means the child born as version `12`.
This is stable and can participate in `protopath`.

So:

- `[]` is mutable positional access
- `._n` is immutable creation-order access

This is the correct split.

---

## 6. `idx` was the wrong concept

Earlier, one number was trying to play several roles at once:

- current position
- identity
- order of creation

That was wrong.

The conversation discovered that these are different things.

For ordered rooms we need:

- mutable position in `order`
- immutable birth number for canonical addressing

So the stable part is not "index" but birth order / creation version.

---

## 7. `protopath` must use birth-based access, not positional access

Because list positions can shift, they must not be part of canonical identity.

Therefore:

```text
foo._12.bar._3
```

is valid as canonical path logic.

But:

```text
foo[12].bar[3]
```

is only a current view, not canonical identity.

This keeps `protopath` stable even when list order changes.

---

## 8. A temporary false symmetry was revealed

At one point it looked beautiful to make:

- class instances
- list items

be handled exactly the same way.

Later we found the deeper distinction:

- class instances are births inside lineage
- list items are members inside sequence order

This means they share some room mechanics, but not the same ontology.

The important shared mechanic is ordered room state, not full sameness of meaning.

---

## 9. Containers likely store references, not embodied child subtrees

A strong idea appeared:

containers may be better understood as storing references rather than containing full embodied child subtrees.

This is especially compelling for:

- `o.List`
- `o.Dict`

because it makes container membership a relation rather than a forced subtree embodiment.

This still leaves a meaningful exception:

- class instances really do feel like they live under the class lineage

So the architecture may distinguish:

- class lineage births
- container reference membership

This is not yet the final law, but it is an important discovery.

---

## 10. For `o.Dict`, hard links are probably the wrong lookup basis

A key insight emerged:

Using hard links to whole subtrees as dict-key lookup basis is too heavy.

For dict keys, what is needed is not another place to live, but a small stable identity token.

So for dictionary lookup, canonical ids are more promising than hard-linking entire key subtrees.

This gives a cleaner distinction:

- hard links may still be useful for multi-placement or co-living
- canonical ids are better for addressability and lookup

---

## 11. Dict items want to be pair-entities

A useful shape was found for dict items:

```text
path/
	0/
		key
		value
	1/
		key
		value
```

This is better than parallel `__keys__/` and `__values__/` rooms, because a dict is a collection of pairs, not two separate collections pretending to be one.

The remaining open question is what exactly `key` and `value` store:

- canonical ids
- refs
- or some other canonical token form

But the pair-entity shape itself is strong.

---

## 12. Sequence is a room-state object, not a list object

By the end of the conversation, the right minimal identity of `Sequence` became clear.

It is not:

- a full list implementation
- a user-facing collection
- a semantic container API

It is:

- a persistent ordered room-state object

Its job is only to hold and commit:

- `count`
- `order`

That is the clean separation of concerns.

---

## 13. Disk-memory simultaneity is preserved by explicit commit

When upper layers mutate `order` / `count` and then call `write()`, the room state on disk is updated immediately after the logical act completes.

So the desired law remains:

- memory state changes
- disk state is committed right after

The split does not remove simultaneity. It makes the simultaneity explicit at the correct level.

---

## 14. Core distinction discovered in this conversation

The deepest discovery of this conversation may be this:

```text
position != birth
membership != lineage
lookup != co-living
```

Which means:

- list position is not canonical identity
- instance lineage is not the same thing as container membership
- dict lookup token is not the same thing as object embodiment

This split clarifies the architecture substantially.
