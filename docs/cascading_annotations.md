# Cascading annotations

## Purpose

This note captures the current idea line around cascading annotations in `o`.
It records only what was established in the conversation above.

---

## Core split

There are three different things here, and they must not be merged:

- **type identity** — what exact class this thing is
- **origin kind** — what broad kind it belongs to, such as `dict`, `list`, `int`, `str`
- **annotation** — the rule describing what this thing's children may be

The earlier problems came from trying to make one mechanism carry several of these roles at once.

---

## Two problems that led here

### 1. Annotation is not exact type identity

If a field stores only annotation, then different classes with the same annotation collapse into one meaning.

That is wrong.

So annotation must not replace type identity.

### 2. Default embodiment and type identity were mixed

`__cast_map__` was being used both as:

- default embodiment path for free Python data
- uniqueness law for annotation

That is not clean.

Embodiment of free data is one thing.
Exact type identity is another.

---

## Current direction

The chosen direction is:

- field has **origin type**
- field has **annotation**
- annotation is a setting about **who my children can be**
- annotation is **read/write**
- for now, annotation is **copied** into the attached object

So annotation here is not the exact identity of the object.
It is not a separate generated abstract class either.
It is a child-shape policy.

---

## Instance-level annotation

This means every instance must have `__annotation__`.

But that must be understood precisely.

### On class

`class.__annotation__` is the base policy of the kind.

Examples:

- `o.T.Dict` -> `dict`
- `o.T.List` -> `list`
- `o.T.Int` -> `int`

### On instance

`instance.__annotation__` is the current child-shape policy of that concrete object.

It is mutable configuration.
It is not exact type identity.

---

## Origin invariant

Instance annotation may become more specific, but it may not change origin.

So:

- class annotation: `dict`
- instance annotation: `dict[str, int]`

is valid.

But:

- class annotation: `dict`
- instance annotation: `list[int]`

is invalid.

### Law

Instance annotation may specialize class annotation, but may not change its origin.

---

## Why annotation cannot live only on field without affecting object

Example:

- `A.foo = X`
- `B.bar = X`
- `A.foo` requires `dict[str, int]`
- then someone does `B.bar['baz'] = 0.9`

If this is allowed, then `A.foo` now contains an object of wrong shape.
That is wrong.

So if an object is attached through a field with a stricter annotation, that annotation must constrain the object's mutations.

This is why simply keeping annotation on the field without any effect on the shared object is not enough.

---

## Current chosen behavior

For now, annotation is copied from field to object.

That means:

- object receives field annotation on attachment
- object then validates its children using this annotation
- object delegates narrower child annotations downstream

This is the current decision.

---

## Cascading rule

If field annotation is nested, the effect must cascade level by level.

Example:

```python
dict[dict[dict[str, int]]]
```

The outer object receives the top-level annotation.
It must then derive the annotation of its immediate children from its own `__annotation__`.

So the passing type for children must be computed locally from the object's current effective annotation.

### General law

- field sets root annotation
- attached object stores it in `__annotation__`
- each object computes the annotation of its direct children from its own `__annotation__`
- children receive narrower annotation
- this repeats recursively

---

## Local derivation

The important point is that child annotation should not be recomputed by reaching all the way back to the original field every time.

Instead:

- root field gives top-level annotation once
- object stores effective annotation locally
- object derives next-step child annotation from that local effective annotation

So each level knows only:

- its own origin kind
- its own effective annotation
- the rule for passing annotation to direct children

This keeps the recursion local and clean.

---

## Examples of cascading

### Dict

For `dict[K, V]`:

- key child gets `K`
- value child gets `V`

So if object annotation is:

```python
dict[dict[dict[str, int]]]
```

then its value child receives:

```python
dict[dict[str, int]]
```

and the next level passes further:

```python
dict[str, int]
```

and then:

- key -> `str`
- value -> `int`

### List

For `list[T]`:

- item child gets `T`

### Atom

Atoms do not pass anything further.

---

## Annotation as child policy

This line treats annotation as:

> a setting about who my children can be

So annotation is not being used here as exact object identity.
It is not a generated abstract class tree either.
It is a downstream child-shape policy.

---

## Current practical summary

- field stores origin type
- field stores annotation
- annotation is read/write
- on attach, annotation is copied into object
- every instance has `__annotation__`
- instance annotation may specialize class annotation
- instance annotation origin must match class annotation origin
- object uses its own `__annotation__` to validate and specialize direct children
- cascading happens level by level
- deeper child annotations are derived locally from the annotation of level `n`

---

## Short formula

- class says **what kind of thing I am**
- field says **what kind of children this slot expects**
- object carries current effective child policy in `__annotation__`
- each level passes narrower annotation to the next level down

---

## Status

Decision made for now:

- annotation will be copied
- it remains a read/write setting
- later this may be changed if a cleaner form appears

