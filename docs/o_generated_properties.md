# o generated properties

## New concepts and invariants

### `@o.property`
`@o.property` is an `o`-native wrapper around Python `property`.
It keeps the Python surface syntax of a property, but its storage and cache behavior follow `o` laws.

### Generated property law
A generated property is read as a semantic slot like any other field.
If the slot already has an embodied value, that value is returned.
If the slot has no embodied value, the getter is called, the returned value is stored into the same slot, and then returned.

So the law is:

- class attribute = manifestation rule
- instance field = embodied value

### Storage invariant
Generated properties do **not** require a special storage format on disk.
On disk, once embodied, they are stored exactly like ordinary fields.
There is no disk-level distinction between:

- a value written directly
- a value first produced by a generated getter and then stored

This means disk already supports generated properties as long as ordinary fields are already supported.

### Cache invariant
The cache slot uses the same semantic field name.
For example, property `name` is cached and stored under slot `name`, not `_name`.

This keeps the external semantic slot and the embodied stored value identical.

### Read behavior invariant
Reading a generated property may cause embodiment.
So reading is allowed to become a write if the value was absent.

That write must follow normal `o` storage laws, not bypass them.

### No extra entities invariant
Generated properties do not require new service entities or new disk entities just because they are generated.
A new entity appears only if the generated value itself is object-shaped and would normally require one.

So:

- atom value -> store as ordinary field value
- object/list/dict value -> store as ordinary field value with whatever normal `o` representation it already uses

## Implementation stage

### Decorator shape
Implementation should expose:

```python
@o.property
```

rather than patching Python built-in `property` globally.

### Descriptor behavior
`o.property` should wrap Python `property`, but use `o` access laws internally.
Conceptually:

1. Resolve field name from getter name
2. Check whether the object already has an embodied value for that field
3. If yes, return it
4. If no, call getter
5. Store returned value into the same field
6. Return stored value

### Storage access
The descriptor should use the object's own storage interface rather than raw `__dict__` as the architectural contract.
So behavior should be expressed through:

- `self.has(name)`
- `self.get(name)`
- `self.set(name, value)`

or the equivalent final minimal API chosen for `o`.

### Disk behavior
No new disk branch is needed for generated properties.
No generated-property metadata is needed on disk for embodied values.
The getter is a class-side rule.
The embodied value is an instance-side ordinary stored field.

So on disk the value simply looks like:

- ordinary attribute
- ordinary list item
- ordinary dict item
- ordinary object reference

according to the already existing field representation.

### Python-side distinction
There are two layers with the same semantic name:

- class-side descriptor named `name`
- instance-side embodied stored value for slot `name`

This is valid as long as the descriptor itself reads and writes through `o` storage law and does not recurse through `self.name`.

### Getter rule
The getter must not read the same property through normal attribute access.
It must resolve through storage access.
Otherwise recursion appears.

### Setter rule
If assignment through the same semantic name is needed, setter support should write into the same slot name.
That preserves the invariant that the generated property and the embodied field share one semantic slot.

### Architectural consequence
Generated properties are not a separate ontology on disk.
They are a class-side manifestation rule for ordinary stored fields.

That is why disk support is already present.
