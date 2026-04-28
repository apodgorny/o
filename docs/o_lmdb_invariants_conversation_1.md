# o LMDB Invariants — Conversation Extract

## Core Storage Law

```text
key   = concrete fact address
value = msgpack value
```

Memory stores facts, not fat object nodes.

Do not store:

```text
o.T.User -> {...}
```

Store concrete facts only.

Examples:

```text
o.T.User = True
o.T.User.__version__ = 0
o.T.User.__items__ = []
o.T.User._.age.type = <type_id>
o.T.User._.age.default = 0
o.T.User._0.name = <child_id>
```

## Reflection Law

```text
_ is reserved for class field metadata only
```

Canonical field reflection:

```text
Class._.<slot>.<prop>
```

Examples:

```text
o.T.User._.age.type
o.T.User._.age.default
o.T.User._.age.is_source
```

Do not use:

```text
o.T.User._.fields.age.type
```

## Instance Value Law

Instance values are actual slots, not reflection.

```text
o.T.User._0.name = <child_id>
```

Attribute slots store child ids.
Atom entities store raw values.

## Identity / Access Law

```text
_0  = stable birth/version identity
[0] = current positional access / view
```

Canonical:

```text
o.T.User._0
```

Runtime positional access:

```text
o.T.User[0]
```

Position is not birth.

## Sequence Law

```text
__version__ increments only
```

Current ordering / membership:

```text
__items__
```

Examples:

```text
o.T.User.__items__ = [0, 2, 5]
o.T.List._0.__items__ = [child_id, child_id]
o.T.Dict._0.__items__ = {key_id: value_id}
```

## Class Existence Law

Class existence fact:

```text
o.T.User = True
```

Missing class means resolution failure, not stored `__exists__` flag.

## TMeta Responsibilities

TMeta should:

- parse declarations into field facts
- write class existence fact
- write id registry: `str(id) -> proto`
- write route metadata for source-backed classes
- write field reflection keys directly into Memory
- avoid `disk/*`

## Source-backed Route Law

Plugin owns filesystem facts.

Plugin should compute file mtime and pass it into class creation.
TMeta consumes those facts and writes metadata.

```text
<route> -> { id, proto, mtime }
```

## Accessor Law

Accessor is the new surface.

Field / Fields wrappers are obsolete.
Disk managers are legacy.

## Serializer Law

Memory uses:

```text
keys   = strings
values = msgpack
```

## Summary Formula

```text
Memory is not node storage.
Memory is fact storage.
```

