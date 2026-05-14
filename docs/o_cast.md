# `o.cast`

## Purpose

This note records the cast rule now used by `o` for field assignment and typed container mutation.

The rule is:

```text
declared type wins over raw value shape
```

Meaning:

- a field does not decide from `dict` or `list` shape alone
- the declared field type is the source of truth
- typed containers continue that rule for their direct children

---

## Core law

Before this change, many write paths did this:

```python
o.T(value)
```

That made `dict` become generic `o.Dict` and `list` become generic `o.List`, even when the schema already knew more.

Now the write path does this:

```python
o.cast(type_cls, value)
```

Meaning:

- `Child` field + raw `dict` -> `Child(**value)`
- `list[Child]` field + raw `list[dict]` -> typed list, then each item becomes `Child`
- `dict[str, Child]` field + raw `dict[int, dict]` -> typed dict, then keys become `str` and values become `Child`

---

## Where the rule applies

The rule is used at mutation entrypoints where type was previously guessed from raw shape:

- object field assignment
- typed list birth
- typed list `append`
- typed list `__setitem__`
- typed dict birth
- typed dict `__setitem__`

This keeps one cast law instead of separate ad hoc repairs in callers.

---

## Existing `o.T` instance rule

There is one important refinement:

```text
existing `o.T` instance passes through only if it already matches the requested class
```

If a typed class receives another `o.T` instance of a different class, `o` first converts it to visible data and then casts again through the declared type.

This is what allows:

```python
TypedChildren(o.List([{'name': 'alex'}]))
```

to become a real typed `list[Child]` instead of preserving the generic list unchanged.

---

## Inherited field metadata

The new cast path needs `field.type`.

That exposed one older asymmetry:

- `__has_field__` already resolved inherited fields through `__mro__`
- `Accessor.type` did not

The fix was to resolve a `__field_owner__` through `__mro__` and read field metadata from that owner class.

This keeps one inheritance law for fields:

```text
field existence and field metadata come from the same owner in `__mro__`
```

---

## Serialization effect

The runtime now keeps stricter typed container identity.

For example, a field declared as:

```python
tags = list[str]
```

may exist at runtime as an embodied generic list class rather than plain `o.T.List`.

That is correct inside runtime, but exposing internal anonymous `Generic_...` names in serialized surface made the output noisy.

So the serializer uses this surface rule:

```text
keep runtime truth inside `o`
show stable origin surface for anonymous generic list/dict containers
```

Meaning:

- anonymous `Generic_...` list instances serialize as `o.T.List`
- anonymous `Generic_...` dict instances serialize as `o.T.Dict`
- named typed classes such as `TopicList` keep their own public class name

This keeps strict runtime behavior and a calmer serialized form.

---

## Summary

The cast rule now is:

```text
schema decides type
containers continue that rule to direct children
serializer hides anonymous generic container names but keeps named public classes
```
