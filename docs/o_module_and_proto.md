# `__o_module__` and `__proto__`

## Short law

`__o_module__` and `__proto__` do not serve the same role.

- `__o_module__` answers: which lawful source-backed class should be re-entered
- `__proto__` answers: which canonical class / instance lineage this entity belongs to
- `id` answers: which persisted entity this is

Those are different axes:

- source resolution
- lineage identity
- technical lookup

## Current code line

For classes, `__o_module__` is persisted only on the class room.

- disk file: `__o_module__`
- owner: `o.disk.Class`
- value: evalable world address such as `o.T` or `o.services.Registry`

This means:

- source-backed classes persist `__o_module__`
- runtime-defined classes do not

So class resolution now splits in two lawful ways:

- if class room has `__o_module__`, `TMeta.__new__` re-enters that class through `eval(o_module)`
- otherwise class birth follows structural runtime path

## `__proto__` remains canonical identity

`__proto__` is still the canonical identity string.

Examples:

- `o.T`
- `o.T.User`
- `o.T.User._0`

It is not loaded from a special file.
It is reconstructed from class / instance position in folder geometry.

So:

- `__proto__` is canonical identity
- `__o_module__` is lawful source origin if one exists

These must not be merged.

## Clean interpretation

The clean reading now is:

- `__o_module__` re-enters a source-backed body
- `__proto__` places that body or instance into ontology lineage

This is a good separation because:

- a runtime-defined class may have `__proto__` without `__o_module__`
- a source-backed class may re-enter through `__o_module__` while still keeping the same `__proto__`
- `id` remains the technical stable ref derived from canonical proto

## Important consequence

Source-backed class declaration is not just arbitrary Python class birth anymore.

The lawful split is:

- source-backed named class
  - born from file-backed `o.Module`
  - re-entered by persisted `__o_module__`

- runtime-defined class
  - born through `extend()`
  - re-entered structurally from disk lineage

So `__o_module__` is not decoration.
It is the witness that a class should come back through source instead of being structurally re-born.
