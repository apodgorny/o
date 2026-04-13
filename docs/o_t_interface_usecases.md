# `o.T` Interface Use Cases

## Purpose

This document describes how a user saw `o.T` in the old interface.

The goal is not to freeze old internals.
The goal is to preserve the same user-facing feeling and affordances while rebuilding.

The material here is derived mainly from:

- `core/old_tests/test_t.py`
- `core/old_tests/test_embodiment.py`
- `core/old_tests/test_definition.py`
- `core/old_tests/test_runtime_types_in_containers.py`
- `core/old_tests/test_t_protocol.py`
- `core/old_tests/test_python_delegation.py`
- `core/old_tests/test_object.py`
- `core/old_tests/test_nested.py`
- `core/old/t.py`
- `core/old/_t_meta.py`

Some cases below are test-proven directly.
Some are clearly part of the intended old public surface because they are implemented explicitly in the old metaclass and class API even if old tests around them are thinner.

## Current status

This file is historical pressure, not current normative law.

Current code has moved in several important ways:

- runtime type creation currently goes through `extend()`, not `define(...)`
- named class declaration is lawful only when it is loaded from file-backed `o.Module`
- runtime-defined named classes should use `extend()`
- ad hoc object attrs are currently allowed

So the examples below are still useful as interface memory, but where they conflict with current code, newer docs and current tests override them.

## User mental model

From the outside, `o.T` behaved like one root typed value API.

A user could approach it in four ways:

1. `o.T(value)` meant: embody this Python value into the right `o.*` runtime type.
2. `class MyType(o.T): ...` meant: define a structured user type with fields.
3. `o.T.define(...)` meant: define a runtime type dynamically.

There was also a fourth declarative form for annotated non-object types:

4. `class MyType(o.T, some_annotation): ...` meant: define a named typed wrapper directly in class syntax.

The important feeling was that the user did not need to think first about storage classes such as `o.One`, `o.List`, `o.Dict`, or `o.Object`.
They could start from `o.T`, and the system resolved the concrete shape.

## Core use cases

### 1. Root coercion from Python values

The base constructor `o.T(value)` was a universal entrypoint.

```python
o.T(1)         # -> o.Int
o.T(1.5)       # -> o.Float
o.T(True)      # -> o.Bool
o.T('x')       # -> o.Str
o.T(None)      # -> o.Null
o.T([1, 'a'])  # -> o.List
o.T({'a': 1})  # -> o.Dict
```

Observed contract:

- `o.T()` without a root value raised `TypeError`
- `o.T(existing_o_instance)` returned that same instance unchanged
- unsupported root values raised `TypeError`
- `kwargs` passed to base `o.T` were treated as an object-like root value

Example:

```python
x = o.Int(10)
y = o.T(x)

assert y is x
assert int(y) == 10
```

### 2. Nested embodiment was automatic

Users could pass nested Python trees and expect recursive embodiment.

```python
root = o.T([
	1,
	'v',
	{'k': [2, 3.0, None]},
	[True, {'x': 10}],
])
```

Observed contract:

- nested `list` values became `o.List`
- nested `dict` values became `o.Dict`
- atomic leaves became the matching atomic `o.*` wrappers
- reading back through indexing and attribute access yielded plain Python values at the leaf level
- nested containers still surfaced as `o.List` and `o.Dict` objects

This created a mixed interface:

- containers remained typed runtime objects
- leaf reads felt Python-native

### 3. Subclassing `o.T` created declarative user types

A user could declare a type with fields by subclassing `o.T`.

```python
class User(o.T):
	name: str
	age: int
```

Observed contract:

- constructing the subclass produced that subclass, not a generic `o.Object`
- empty construction was allowed
- partial keyword construction was allowed
- fields could be set after construction
- nested `o.T` subclasses were valid field types

Examples:

```python
class A(o.T):
	x: int
	y: int

a0 = A()
a1 = A(x=1, y=2)
a2 = A(x=1)

a0.x = 1
a0.y = 2
```

Nested type example:

```python
class Address(o.T):
	zip: int

class User(o.T):
	address: Address

u = User(address=Address(zip=12345))
assert isinstance(u.address, Address)
assert u.address.zip == 12345
```

### 4. Structured subclasses felt object-like

When a subclass declared fields, the user-facing experience was object-style access.

```python
class User(o.T):
	name: str
	age: int

u = User(name='alex', age=33)

assert u.name == 'alex'
assert u.age == 33
```

Expected behavior from adjacent old tests around `o.Object`:

- attribute read worked
- attribute write worked
- attribute delete worked
- `__cast_out__()` returned a plain Python `dict`
- invalid field names were rejected for dynamic object keys

### 5. `o.T.define(...)` exposed runtime type creation

Users could create named types at runtime instead of writing class syntax.

Atomic runtime type:

```python
Age = o.T.define('Age', int)
age = Age(10)
```

List runtime type:

```python
Names = o.T.define('Names', list[str])
names = Names(['a', 'b'])
```

Dict runtime type:

```python
Scores = o.T.define('Scores', dict[str, int])
scores = Scores({'a': 1, 'b': 2})
```

Object runtime type:

```python
User = o.T.define('User', name=str, age=int)
user = User({'name': 'alex', 'age': 10})
```

Observed contract:

- annotation-only definition produced a typed non-object wrapper
- field-based definition produced an object-like type
- field specs could be declared with bare annotations or `o.F(...)`
- exactly one style was required: annotation or fields, but not both
- the defined type was registered under `o.T.<Name>`

### 6. Typed second-base class declarations were part of the surface

This was one of the main cases I had missed in the first draft.

The old metaclass explicitly supported a second base that was a Python annotation:

```python
class Scores(o.T, dict[str, int]):
	pass

class Names(o.T, list[str]):
	pass

class Age(o.T, int):
	pass
```

In spirit, this was the class-syntax twin of `o.T.define(...)`.

These forms were meant to feel equivalent:

```python
class Scores(o.T, dict[str, int]):
	pass
```

```python
Scores = o.T.define('Scores', dict[str, int])
```

Observed contract from old metaclass code:

- when `o.T` received a second typed base, that annotation became `__annotation__`
- the metaclass normalized the real runtime base from that annotation
- the resulting type was still registered under `o.T.<Name>`
- this worked for atomic, list, and dict-like types

There is also an explicit old comment showing intended usage:

```python
class Users(o.T, list[o.User]):
	pass
```

So this form should be treated as part of the historical interface, not a side effect.

### 7. Runtime-defined and declaratively defined types stayed visible inside containers

One important old affordance was that custom runtime types did not disappear when placed into containers.

```python
Age = o.T.define('Age', int)
x = o.List([Age(10), Age(20)])

assert isinstance(x.__refs__[0], Age)
assert isinstance(x.__refs__[1], Age)
```

The same applied for:

- runtime atomic types inside `o.List`
- runtime atomic types inside `o.Dict`
- runtime atomic types inside object fields
- runtime object types inside `o.List`
- runtime typed `list[...]` and `dict[...]` wrappers after reload

This matters because preserving values alone is not enough.
The interface also preserved the specific runtime class identity of user-defined types.

### 8. Types were discoverable from `o.T` by name

The old metaclass also exposed class lookup directly from `o.T`.

Supported shapes in old code:

```python
o.T['Scores']
o.T.Scores
```

Observed contract from old metaclass code:

- `o.T['Name']` resolved `o.T.Name` through the type registry
- `o.T.Name` delegated to that same lookup path
- missing names raised `AttributeError` at the dotted access surface

This matters because old `o.T` was not only a constructor.
It also acted as a namespace for dynamic types.

### 9. `o.T` objects participated in normal Python protocols

Old tests treated `o.T` objects as Pythonic values, not only as storage nodes.

Examples:

```python
x = o.Int(5)

assert (2 + x) == 7
assert (10 - x) == 5
assert (x >= 5) == True
```

For containers:

```python
l = o.List([3, 1, 2])
l.sort()

assert l.__cast_out__() == [1, 2, 3]
assert l.count(2) == 1
assert l[:2] == [1, 2]
```

For dict-like values:

```python
d = o.Dict()
d['a'] = 1
d.update({'b': 2})

assert d.get('b') == 2
assert 'a' in d.keys()
```

Observed contract:

- numeric wrappers supported arithmetic and comparisons against Python values
- container wrappers supported `len`, iteration, containment, indexing, slicing
- calling mutating Python methods on wrapped containers persisted the mutation
- calling non-mutating Python methods returned normal Python results without corrupting state

This was a major part of the old feel of `o.T`: typed persistence with low-friction Python ergonomics.

### 10. Identity and reopening were part of the experience

Users could create a value, keep its id, and reopen it later as the same typed interface.

Examples in old tests used methods such as:

- `SomeType.instantiate(id_)`
- `SomeType.__load__(id_)`

Observed contract:

- reopened values preserved their visible type
- reopened nested values rebuilt the typed graph shape
- reopening a container with runtime-defined children preserved those child classes
- multiple reopenings of the same value stayed consistent

This means persistence was not just a storage concern.
It was part of the interface contract.

### 11. Recursive embodiment happened level by level through container dispatch

The old code makes the recursion path fairly clear.

Root entry:

- `o.T(value)` selected the first wrapper class from `o.__cast_map__` based on the Python root type
- once that wrapper was chosen, embodiment moved into that concrete class

Container recursion:

- `o.Many.__cast_in_item__` was the central item-level dispatcher
- if a child was not already an `o.T` instance, it looked up the wrapper class from `o.__cast_map__`
- then it either:
  - reused the existing child object and called `reuse_item.__cast_in__(value)`
  - or created a fresh child wrapper with `cls(value)`

That means recursion happened one level at a time:

- `o.List.__cast_in__` iterated items and called `__cast_in_item__` for each child
- `o.Dict.__cast_in__` iterated keys and values and called `__cast_in_item__` for each level
- `o.Object.__cast_in__` iterated field values and called `__cast_in_item__` for each child slot

Each child could itself be a container.
When that happened, the child wrapper repeated the same process inside its own `__cast_in__`.

So a nested value like:

```python
o.T({
	'user': {
		'name': 'alex',
		'tags': ['a', 'b'],
	},
})
```

was embodied by repeated local steps, not by one giant global walker.

### 12. Validation also happened level by level, but through two different laws

The old code had two different validation channels.

Annotation validation:

- `o.Annotation` validated the annotation tree itself on construction
- `o.Annotation.cast(...)` recursively validated and normalized runtime values
- for `list[...]`, it cast each item through the nested value annotation
- for `dict[..., ...]`, it cast each key and each value through their nested annotations
- for unions, it tried options in canonical order until one matched

This was the strongest explicit recursive validation path in the old code.

Atomic and typed-wrapper validation:

- `o.One.__cast_in__` called `self.__annotation__.cast(value)`
- `o.One.__cast_out__` called that same cast on read
- so atomic and typed non-object wrappers validated through annotation recursion

Field validation for object-like types:

- `o.F.validate(...)` existed and validated field values against declared field type
- `o.TMeta.__validate__(...)` existed with the same overall law
- both paths handled:
  - `undefined`
  - optional `None`
  - existing `o.T` instances
  - non-`o.T` values by inferring their annotation and checking compatibility

Important nuance:

- in the old code I inspected, recursive embodiment for containers is definitely wired and active
- recursive annotation validation is definitely wired and active
- field validation for declared object fields clearly exists as intended law, but it is not as directly visible in the old embodiment path as the container recursion is

So the accurate reading is:

- embodiment was recursive by active container dispatch
- validation was recursive by active annotation casting
- field-level schema validation existed as explicit contract code and should be preserved, even where the old call path was less obvious

## Interface invariants worth preserving

If we want the rebuilt `o.T` to feel the same to a user, these invariants seem essential:

1. `o.T` remains the root public entrypoint for typed embodiment.
2. One Python root value maps to one obvious `o.*` wrapper class.
3. Existing `o.T` instances pass through unchanged when given to `o.T(...)`.
4. Nested Python data is embodied recursively without extra ceremony.
5. Declaring `class X(o.T): ...` remains a first-class way to define user types.
6. Declaring `class X(o.T, some_annotation): ...` remains equivalent in spirit to `o.T.define('X', some_annotation)`.
7. `o.T.define(...)` remains equivalent in spirit to class declaration for runtime cases.
8. `o.T` can act as a namespace for dynamic type lookup by name.
9. Custom runtime types survive roundtrip through containers and reloads.
10. Wrapped values still feel Pythonic for arithmetic, indexing, iteration, and common methods.
11. Object-like `o.T` types expose field access through attributes.
12. Recursive nested embodiment stays local and level-wise rather than becoming a special one-off traversal path.
13. Recursive nested validation follows the same annotation tree the user declared.

## Planned extensions

### 1. Type creation and type extension are symmetrical across API form and class form

This is a new rule we want to add on top of the legacy interface.

The structure should read as three matched pairs.

Creation pair:

```python
User = o.T.define('User', name=str)
```

```python
class User(o.T):
	name: str
```

Typed-wrapper creation pair:

```python
Scores = o.T.define('Scores', dict[str, int])
```

```python
class Scores(o.T, dict[str, int]):
	pass
```

Extension pair:

```python
o.T.User.extend(age=int)
```

```python
class User(o.T.User):
	age: int
```

Equivalent class-local extension form:

```python
User = o.T.define('User', name=str)
User.extend(age=int)
```

Desired contract:

- `define(...)` exists only on root `o.T`
- subclasses and defined types do not expose their own `.define(...)`
- once a type exists, it evolves through `.extend(**fields)` or through subclass extension syntax
- API form and class form should describe the same schema moves

The law becomes:

- `o.T.define(...)` is symmetrical with class definition
- `MyClass.extend(...)` is symmetrical with subclassing an existing class and adding fields
- root `o.T` creates named types
- existing types extend from themselves

Important nuance:

- creation creates a named root type
- extension does not redefine the root type from outside
- extension is local to the type being evolved, whether expressed through `.extend(...)` or class syntax

This keeps the old beauty intact while making the growth model much clearer.

### 2. Dynamic `@o.property` slots resolve once and then cache as ordinary stored attributes

This is another new rule we want to add on top of the legacy interface.

Desired contract:

- a method decorated with `@o.property` behaves like a dynamic semantic slot
- first access may execute code
- the resolved value is then cached internally
- the cached value is stored under the same slot name
- once stored, it behaves like an ordinary attribute in the system

Example:

```python
class User(o.T):

	prompt: str

	@o.property
	def summary(self):
		return llm(self.prompt)
```

Expected behavior:

```python
user = User(prompt='Summarize me')

first  = user.summary   # runs code, resolves value, stores it
second = user.summary   # returns stored value
```

Meaning:

- `@o.property` is not only a Python descriptor convenience
- it is a manifestation rule attached to a semantic slot
- access is allowed to trigger computation
- the result is persisted through normal `o` storage law
- there is no separate special cache format for generated values

Storage law:

- the resolved value is stored just like any other ordinary stored attribute
- the cache lives under the same semantic name, not a hidden backing name
- after resolution, the system reads the embodied value rather than recomputing

Why this matters:

- it makes expensive or generative values feel like native attributes
- it is a natural fit for LLM-backed generation
- it lets generation become part of the object interface rather than an external workflow step

## Things that were user-visible but should be treated carefully

Some old surface details were visible, but they feel more incidental than essential:

- direct inspection of `.__refs__`
- direct inspection of `.__dict__['_attributes']`
- exact internal class split between `o.One`, `o.Many`, `o.Object`, and container storage services
- exact registration internals such as `__types_by_id__`

These are useful as implementation evidence, but they should not be the main compatibility target unless a new design truly needs them.

## Recommended rebuild target

If we compress the old interface down to its cleanest promise, it is this:

> `o.T` is the single public root for creating, declaring, reopening, and working with typed persistent values that still behave like natural Python values.

That seems to be the beauty worth preserving.
