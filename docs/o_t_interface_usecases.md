# `o.T` Interface Use Cases

## Purpose

This document captures the current user-facing feeling of `o.T`.

It is a compact description of the surface preserved by the current test layer and current architecture.

Normative references now are:

- `core/tests/test_class.py`
- `core/tests/test_instance.py`
- `core/tests/test_list.py`
- `core/tests/test_dict.py`
- `core/tests/test_atomic.py`
- `core/tests/test_annotation.py`
- `core/tests/test_gc.py`

## Current public feeling

From the outside, `o.T` is still one root typed value API.

A user approaches it mainly in four ways:

1. `o.T(value)` embodies a Python value into the right `o.*` runtime type.
2. `class MyType(o.T): ...` declares a lawful source-backed named type.
3. `o.T.SomeType.extend(...)` creates a runtime-defined subtype.
4. `o.get(id_or_proto)` reopens an existing entity while preserving its form and visible interface.

Top-level persistence is rooted through `o.V`.

## 1. Root embodiment from Python values

The base constructor `o.T(value)` is the universal entrypoint.

```python
o.T(1)         # -> o.Int
o.T(1.5)       # -> o.Float
o.T(True)      # -> o.Bool
o.T('x')       # -> o.Str
o.T(None)      # -> o.Null
o.T([1, 'a'])  # -> o.List
o.T({'a': 1})  # -> o.Dict
o.T(name='x')  # -> object-like root value
```

Current contract:

- `o.T(existing_o_instance)` returns that same instance
- unsupported root values raise `TypeError`
- `kwargs` on root `o.T` create object attrs
- embodiment is recursive

## 2. Nested embodiment is automatic

Users can pass nested Python trees and expect recursive embodiment.

```python
root = o.T([
	1,
	'v',
	{'k': [2, 3.0, None]},
	[True, {'x': 10}],
])
```

Current visible law:

- nested `list` values become `o.List`
- nested `dict` values become `o.Dict`
- atomic leaves become the matching atomic wrappers
- leaf reads surface Python values
- nested containers still surface as `o.List` / `o.Dict`

## 3. Subclassing `o.T`

Named type declaration is lawful when it is source-backed.

```python
class User(o.T):
	name: str
	age: int
```

Current contract:

- the class is structural and persistent
- constructing it produces that subclass, not a generic `o.Object`
- kwargs become object attrs
- declared fields are validated
- undeclared attrs are still currently allowed

Runtime-defined named classes are created through `extend()`, not by direct ad hoc class declaration.

## 4. Structured subclasses feel object-like

```python
class User(o.T):
	name: str
	age: int

u = User(name='alex', age=33)

assert u.name == 'alex'
assert u.age == 33
```

Current expected behavior:

- attribute read works
- attribute write works
- attribute delete works
- defaults live on the class and are inherited naturally
- non-atomic child attrs surface as wrappers
- atomic child attrs surface as Python values

## 5. Containers keep their own surface

List behavior and object-attr behavior are independent.

```python
x = o.List([1, 2, 3], title='numbers')

assert x[0] == 1
assert x.title == 'numbers'
```

Likewise for dict:

```python
d = o.Dict({'a': 1}, title='scores')

assert d['a'] == 1
assert d.title == 'scores'
```

This is part of the current interface feel:

- list / dict special semantics
- object attrs on the same entity

## 6. Reload preserves form and values

`o.get(id)` and `o.get(proto)` must preserve visible form.

Current promise:

- source-backed classes reopen through `__route__`
- runtime-defined classes reopen structurally from disk lineage
- reopened instance preserves object attrs
- reopened instance preserves list / dict / atomic value form

So reload is not just byte recovery.
It is form-preserving re-entry.

## 7. Root persistence through `o.V`

`o.V` is the singleton root value instance.

Current law:

- attach something to `o.V` -> it survives reload
- remove the last owning edge from `o.V` and elsewhere -> it may be released

This is the current public persistence model.

## Summary

The current user-facing formula is:

> `o.T` is the single public root for embodiment, declaration, reopening, and working with typed persistent values, while `o.V` is the single root value that keeps top-level state alive across reloads.
