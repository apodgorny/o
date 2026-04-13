# Annotated types

## Purpose

This note captures the current reasoning around annotated types in `o`.
It records only what was established in the conversation above.

---

## Why this is needed

There are two different things that must both remain true:

- strict typing of containers must be preserved on disk
- canonical class identity must stay clean and reusable

If these are merged, the system starts creating strange exact classes for full nested annotations.
That is what we want to avoid.

---

## Core split

Annotated types in `o` are built from two different layers:

- `type`
- `annotation`

They must not be merged.

### `type`

`type` is the exact runtime class identity.

Examples:

- `o.Int`
- `o.Str`
- `o.List`
- `o.Dict`
- `o.T.MyClass`

`type` stays shallow.

### `annotation`

`annotation` is the strict typing policy.

Examples:

- `int`
- `list[str]`
- `dict[str, int]`
- `dict[str, o.T.MyClass]`

`annotation` carries the full container restriction.

There is now one more important split on top of that:

- field stores exact embodied class identity
- class stores its own annotation

So field and class do not carry the same annotation role.

---

## Disk law

Strict typing on a container must still be stored on disk.

The cleanest way to store it is as the full complex annotation.

This means:

- disk must keep the full annotation
- `type` must still be stored separately
- `type` must not try to encode the full nested annotation

So for a container field or class we store:

- shallow canonical `type`
- full strict `annotation`

But this now needs one important refinement.

### On field disk

Field no longer stores its own separate `annotation`.

Field stores only:

- `type`
- `default`
- other field props

Field annotation is derived back through the embodied class stored in `type`.

### On class disk

Class itself must store its own annotation on disk.

So class annotation belongs to class disk entity, not to field.

This means:

- field strictness is recovered through field `type`
- class strictness lives on class itself

This removes duplication between field annotation and class annotation.

---

## Shallow type law

We only need to set `type` on the container itself.

We do not need to set deeper exact types per nested annotation node.

The reason is that deeper object boundaries can already be represented by `o.T.MyClass`.

Example:

- `dict[str, o.T.MyClass]`

Here:

- root `type` is `o.Dict`
- full `annotation` is `dict[str, o.T.MyClass]`
- the rest of the structure is held by `o.T.MyClass`

So exact type identity stays shallow, while annotation stays strict.

This is also why field `type` is now the id of the embodied class, not the id of the shallow origin class.

So the law is no longer:

- annotation -> origin -> class id

It is now:

- annotation -> embodied class -> class id

---

## Depth rule

Annotations used for class definition should go no deeper than two levels in the resulting class graph.

Example:

- `dict[str, o.T.MyClass]`

is the intended form.

That means:

- container annotation may still contain object references
- once an object boundary is reached, the remaining shape belongs to that object class

So recursion should go down until only that much is left, define the last class there, and then move back up toward the root.

This means class embodiment is bottom-up.

Because of that, this law belongs to class birth, not to an already-born class object.

So embodiment of class annotations belongs on the metaclass side.

The current line is:

- class `__embody__` resolves annotation into canonical class
- recursion goes to inner args first
- then comes back up to build the outer generic class

---

## Dynamic generic classes

Only the top class may be user-named.

This top class may be defined directly by the user.

All inner classes created during annotation expansion are different:

- they are created only dynamically
- they are not user-named
- they may be reused by later definitions

So non-top classes are effectively nameless in intent, even though they still need legal class names in the system.

Their names should therefore be generic.

---

## Generic class names

Underscores in class names are now allowed.

So generated generic class names may use that freedom.

What matters is not user-facing beauty of those names, but that:

- they are generic
- they are legal
- they are reusable

The top class may still be user-named, but non-top generated classes are generic in intent.

---

## Annotation ownership

Own `__annotation__`` belongs only to canonical type levels:

- level 2 origin classes
- level 3 generic classes

User-defined annotated classes above them do not own annotation.
They only inherit it.

So:

- annotation is written to disk only on canonical type nodes
- user-defined annotated classes do not write their own annotation to disk

---

## Generic placement

Generic classes live only directly under shallow origin classes.

Examples:

- `o.T.List.Generic_...`
- `o.T.Dict.Generic_...`

Rejected shapes:

- generic under generic
- generic under user-defined class

Nested complexity is represented by separate canonical generics at their own origin kinds, not by sequential generic chains.

---

## Visible annotation law

Visible annotation must stay human.

So we do not expose:

- `list[o.Str]`
- `list[o.Str.Str]`

We expose:

- `list[str]`

Simple embodied atomics collapse back to Python origins in visible annotation:

- `o.Str -> str`
- `o.Int -> int`

Depth still stays bounded:

- immediate child shape may remain in annotation
- deeper structure must cross a class boundary

---

## Top class relation to generic base

For:

- `class X(o.T, list[str])`

the generic class is:

- real Python base
- real proto parent
- real disk parent

So annotated user-defined classes live under the generic branch, not directly under plain `o.T`.

---

## `__cast_map__` law

Generic annotated types should participate in caching through `o.__cast_map__`.

This is what unifies all annotated types.

Simple built-in kinds already fit this line naturally:

- `int`
- `str`
- `list`
- `dict`

Since all simple types are implemented separately, they only need a cast-map lookup.

Generic annotated types follow the same overall law, but are cached by annotation rather than only by shallow origin.

This means:

- simple canonical types are restored through cast-map lookup
- generic annotated types are also restorable from cast-map by annotation

So annotated type resolution is unified under one caching mechanism.

This means `__cast_map__` is no longer only:

- origin -> class

It is now also:

- full annotation -> embodied generic class

This is what allows generic annotated classes to be reused instead of recreated.

---

## No weird exact classes

This line explicitly rejects creation of strange exact classes for every full nested annotation.

Examples of what we do **not** want:

- class for `dict[int, str]`
- class for `list[dict[str, int]]`

Instead, the exact canonical classes remain only:

- `o.Dict`
- `o.List`
- `o.Int`
- `o.Str`
- user-defined object classes such as `o.T.MyClass`

The full strictness lives in annotation, not in exploding exact type identity.

This is still true even after embodiment.

Embodiment does not mean:

- create one weird exact class per written annotation forever

It means:

- recursively create or reuse canonical generic classes
- keep them cached by annotation
- keep exact field identity shallow through stored `type`

---

## Root-only annotation birth

Clarity improves if annotations are allowed only on base `o.T`, not on other types.

That means:

- only root class birth may take annotation directly
- after that, origin becomes the base class

So annotation is used only at the point where the root kind is born.

After that:

- inheritance continues through classes
- not through repeated annotation mixing

This keeps origin clean and prevents annotation from floating around deeper in the inheritance chain.

The resulting rule is:

- `class X(o.T, annotation)` is allowed
- `class Y(Base, annotation)` is not allowed when `Base` is not `o.T`

After root birth, inheritance should continue through classes, not by injecting annotation again.

This also means `extend(...)` does not need a separate special law here.
It goes through the same `__new__` path and is restricted there.

---

## Class annotation cycle

Class annotation now has its own complete cycle.

### In memory

Class keeps annotation in:

- `cls.__annotation__`

### On disk

Class disk entity keeps annotation in its own annotation file.

So class annotation is not reconstructed from fields.
It lives on class itself.

### Binding law

The current binding line is:

- if source namespace defines `__annotation__`, it wins
- otherwise annotation is loaded from class disk entity
- live class receives normalized `o.Annotation(...)`
- disk class stores the plain annotation form

This keeps source definition and disk reloading in one cycle.

---

## Definition split

Annotated type work led to a cleaner split in class definition.

`__define__` now does not own the whole class namespace.

It separates:

- field declarations
- ordinary Python namespace

So:

- methods survive
- underscored names survive
- field declarations are removed from ordinary namespace
- fields are collected separately

This matters for annotated types because `__annotation__` must survive ordinary class birth instead of being confused with field declaration.

The current rule is:

- names starting with `_` are not treated as fields in `__define__`

This keeps `__annotation__` on the class side where it belongs.

---

## Source authority

When a class is defined from source, its own field definition is authoritative.

That means:

- own field disk folder is wiped
- then fields are defined again from source

This is not a diff-based update.
It is replacement of the class's own field definition.

This matters for annotated types too, because old strict field shape must not survive after source definition changed.

The law applies only to own field layer of that class.

---

## Ordinary namespace survives

A class defined in Python file may have more than fields.

It may also have:

- methods
- descriptors
- other ordinary attrs

So field machinery must not consume the whole class namespace.

This was an important discovered consequence of the annotated-type work:

- field semantics live in `o.Fields`
- ordinary class body must still survive ordinary `super().__new__(...)`

Without that, top classes born on top of embodied generic bases would lose their real class body.

---

## Summary

The current chosen line is:

- strict container typing must be preserved on disk
- the cleanest stored form for that is full annotation
- exact runtime `type` stays shallow and canonical at the field surface
- deeper structure is represented by object classes such as `o.T.MyClass`
- recursion goes down until that object boundary is reached, then comes back up
- class embodiment belongs to metaclass birth law
- only the top class may be user-named
- inner generated classes are dynamic and generic
- generated generic classes are reusable and cached by full annotation
- generic annotated types participate in `o.__cast_map__`
- annotated types are thus unified under one caching mechanism
- we do not create strange exact classes for full nested annotations
- annotation should be allowed only on root `o.T` birth, not deeper in ordinary subclassing
- field stores only embodied `type` id, not separate annotation
- class annotation lives on class and on class disk entity
- `__define__` separates fields from ordinary namespace and ignores underscored names
- source definition is authoritative for own field layer
