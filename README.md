# almasi.o

**A Python-native persistent ontology — a computational world for applications and AI.**

Technical overview video: https://youtu.be/M8GxATOocD0

`almasi.o` makes Python entities persistent by nature.

Classes, objects, relationships, identity, schema, validation, serialization, and runtime state become parts of one persistent object system instead of separate representations connected by glue code.

```text
Python object
    │
    ├── structure
    ├── validation
    ├── identity
    ├── relationships
    ├── serialization
    ├── schema
    └── persistence
```

No separate persistence model.  
No explicit `save()`.  
No database migrations for ordinary runtime schema extension.

The object is the source of truth.

[Watch the almasi.o technical overview](https://youtu.be/M8GxATOocD0)

---

## Why o?

Modern applications often represent the same domain concept many times:

```text
Business Object
    ↓
Validation Model
    ↓
API Model
    ↓
Serialization Model
    ↓
Persistence Model
    ↓
Database Schema
```

Every boundary creates mapping code.

Every mapping creates another representation of the same thing.

Every representation creates another opportunity for state, schema, and meaning to diverge.

`almasi.o` takes a different approach:

> **Make the Python entity itself persistent.**

```text
                    ┌── database
                    │
                    ├── API
Python Entity ──────┼── validation
                    │
                    ├── serialization
                    │
                    └── AI
```

One object model spans the Python runtime, persistence, serialization, schema, and AI-facing structure.

---

# Installation

Requires Python 3.11+.

Clone the repository and run the installer:

```bash
git clone https://github.com/apodgorny/o
cd o
./install.sh
```

Then:

```python
import o
```

That's it.

Your Python world can now persist.

---

# Quick start

Define a persistent type:

```python
import o


Person = o.T.extend(
	'Person',
	name = str,
	age  = int,
)
```

Create an entity:

```python
alexander = Person(
	name = 'Alexander',
	age  = 42,
)
```

Use it like an ordinary Python object:

```python
print(alexander.name)

alexander.age = 43
```

There is no:

```python
alexander.save()
```

The mutation itself is persistent.

---

# Give an entity a persistent root

An object becomes part of the persistent world when it is referenced by the persistent graph.

`o.V` is the root value namespace:

```python
o.V.alexander = alexander
```

Later:

```python
alexander = o.V.alexander
```

And after another process starts:

```python
import o

alexander = o.V.alexander
```

The process ended.

The entity didn't.

---

# Stable entity identity

Every persistent entity has a stable identity.

```python
alexander.id
```

The same entity resolved later retains that identity:

```python
first_id = o.V.alexander.id
```

Restart the process:

```python
import o

second_id = o.V.alexander.id

assert first_id == second_id
```

Identity is not tied to a Python memory address or the lifetime of a process.

Internally, entities have canonical ontology paths (`__proto__`) which map to stable IDs.

Conceptually:

```text
proto → id → entity
```

This allows objects to remain the same logical entities across references, processes, and restarts.

---

# Deep persistence

Persistence does not stop at the top-level object.

Lists, dictionaries, atoms, and domain entities participate in the same persistent object world.

```python
alexander.tags.append('AI')
alexander.settings['dark'] = True
alexander.projects[0].status = 'active'
```

Changes persist where they happen.

There is no need to reassign the parent:

```python
# not required

alexander.tags = alexander.tags
alexander.settings = alexander.settings
```

And there is no explicit dirty tracking:

```python
# not required

mark_dirty(alexander)
```

The nested object being changed is itself persistent.

> **Persistence works at any depth of the object graph.**

---

# Python-native data modeling

`o` uses Python types as the basis of its persistent type system.

```python
Person = o.T.extend(
	'Person',
	name   = str,
	age    = int,
	active = bool,
)
```

Values are validated and cast according to their declared fields.

```python
alexander.name = 42

print(alexander.name)
# '42'
```

The same model can produce Python data:

```python
alexander.to_data()
```

JSON:

```python
print(alexander.to_json())
```

JSON Schema:

```python
Person.to_json_schema()
```

And an AI-oriented structural prompt:

```python
print(Person.to_prompt())
```

The same persistent type therefore participates in:

```text
Python runtime
      │
      ├── validation
      ├── casting
      ├── persistence
      ├── serialization
      ├── JSON Schema
      └── AI representation
```

---

# Fields

Fields can be declared directly from Python types:

```python
Person = o.T.extend(
	'Person',
	name = str,
	age  = int,
)
```

Or explicitly with `o.F`:

```python
Person = o.T.extend(
	'Person',
	name = o.F(
		str,
		description = 'Human-readable name of the person',
	),
	age = o.F(
		int,
		description = 'Age in years',
		default     = None,
	),
)
```

`o.F` carries the structural and semantic information of a field.

A field can have:

- a type
- a default
- optionality/nullability semantics
- a description
- additional atomic metadata

---

# Semantic metadata

The `._` surface exposes metadata about the structure of an entity.

```python
Person._.name.type
Person._.name.description
Person._.name.default
Person._.name.is_optional
```

Metadata can also describe what a field means:

```python
Skill = o.T.extend(
	'Skill',
	effect = o.F(
		str,
		description = 'What this skill enables an agent to do',
	),
)
```

Then:

```python
Skill._.effect.description
```

returns the semantic description associated with the field.

This distinction is important:

```text
Skill.effect
```

is part of the world.

```text
Skill._.effect
```

describes that part of the world.

This gives `o` a natural surface for reflection, tooling, AI interpretation, and future semantic indexing.

---

# Persistent type system

In most Python systems, data may survive while the class that interpreted it exists only in source code and process memory.

In `o`, types themselves participate in the persistent ontology.

```python
Employee = Person.extend(
	'Employee',
	role = str,
)
```

The relationship between the types is persistent:

```text
o.T
└── Person
    └── Employee
```

The ontology therefore contains both:

```text
types
│
├── fields
├── inheritance
└── metadata

instances
│
├── values
├── relationships
└── identity
```

Data remembers not only its values.

It remembers what it is.

---

# Runtime extensible schema

The persistent model can evolve while the application is running.

Add a field:

```python
Person.age = o.F(int)
```

Use it immediately:

```python
alexander.age = 42
```

Remove the field:

```python
del Person.age
```

Create entirely new types:

```python
Project = o.T.extend(
	'Project',
	name   = str,
	status = str,
)
```

Extend them:

```python
ResearchProject = Project.extend(
	'ResearchProject',
	topic = str,
)
```

There is no separate SQL migration operation required to express these changes.

```text
change ontology
      ↓
persistent type system changes
      ↓
application uses it immediately
```

> **No database migrations. No restart. Just Python.**

---

# Persistent relationships

References between objects are persistent relationships.

```python
Person.project = o.F(Project, default=None)

alexander.project = project
```

`alexander.project` is not a copied DTO or foreign-key value exposed to the application.

It is another entity:

```python
alexander.project.name
alexander.project.status
alexander.project.id
```

The Python object graph is also the persistent graph.

```text
Alexander
    │
    └── project ──→ Almasi
                       │
                       └── status ──→ active
```

This means ordinary object composition becomes persistent structure.

---

# Automatic persistent lifecycle

Relationships participate directly in object lifecycle.

```python
alexander.project = project
o.V.project       = project
```

There are now persistent references to `project`.

Remove one:

```python
del o.V.project
```

The project is still referenced by Alexander.

Remove the remaining reference:

```python
del alexander.project
```

The object becomes collectible when it is no longer retained by the persistent graph.

Conceptually:

```text
reference object
      ↓
object lives

remove references
      ↓
reference count reaches zero
      ↓
object becomes collectible
```

The persistent graph — not the lifetime of the Python process — determines what lives.

---

# Persistent collections

`o` embodies Python collections as persistent entities.

Lists:

```python
items = o.List([
	'AI',
	'Python',
	'ontology',
])

items.append('agents')
items[0] = 'AGI'
```

Dictionaries:

```python
settings = o.Dict({
	'dark'  : True,
	'model' : 'default',
})

settings['dark'] = False
```

Their elements are represented through the same entity system used by the rest of the ontology.

This is what makes deep persistence possible: the nested collection is not merely serialized inside its parent. It participates in persistence itself.

---

# Python values are embodied

Primitive Python values can participate in the ontology as persistent atomic entities.

`o` provides persistent representations for values such as:

```text
int
float
bool
str
None
list
dict
```

The system maps ordinary Python annotations into persistent `o` types.

Application code can still work with normal Python-visible values while the underlying object graph retains persistent identity and structure.

This creates one value world instead of a hard boundary between:

```text
Python values  |  database values
```

---

# Native Python behavior

Persistent values are designed to remain natural to use from Python.

Atomic and collection entities expose Python-facing behavior, including supported operators and built-in-style operations.

The goal is simple:

> persistence should change the lifetime of an object, not make it stop feeling like Python.

---

# JSON serialization

Any persistent object tree can be converted into ordinary Python data:

```python
data = alexander.to_data()
```

or JSON:

```python
json_text = alexander.to_json()
```

Nested persistent entities are recursively represented as ordinary visible data.

---

# Schema-carrying serialization

`o` also supports structural serialization:

```python
spec = alexander.serialize()
```

Unlike plain JSON data, the serialized specification includes the type definitions needed to understand the object.

Conceptually:

```text
serialized entity
│
├── class definitions
│   ├── field types
│   ├── defaults
│   └── descriptions
│
└── instance
    ├── class
    └── values
```

Deserialize it:

```python
restored = o.T.deserialize(spec)
```

If a required runtime-defined class does not exist, the deserializer can reconstruct it from the serialized ontology description.

The data can therefore carry the structure required to interpret itself.

---

# Self-reconstructing types

Persistent runtime types are not limited to the process that originally created them.

```python
Employee = Person.extend(
	'Employee',
	role = str,
)
```

The type becomes part of the ontology.

A later process can resolve the persistent type hierarchy again rather than requiring the original runtime definition to remain alive.

Serialization goes further: serialized objects include the class definitions needed by the deserializer to reconstruct missing runtime types.

> **The type definition can outlive the code path that created it.**

---

# JSON Schema

Persistent types can generate strict JSON Schema:

```python
schema = Person.to_json_schema()
```

For example, an object type is represented structurally as:

```json
{
	"type": "object",
	"properties": {
		"name": {
			"type": "string"
		},
		"age": {
			"type": "integer"
		}
	},
	"required": [
		"name",
		"age"
	],
	"additionalProperties": false
}
```

Nested `o` classes, lists, dictionaries, unions, nullable fields, and recursive references are represented by the schema builder where supported.

This makes the ontology directly useful at API and model boundaries without maintaining another manually synchronized schema.

---

# AI-readable structure

Types can also render an AI-oriented representation:

```python
print(Person.to_prompt())
```

Field descriptions are included as semantic context.

For a type such as:

```python
Skill = o.T.extend(
	'Skill',
	name = o.F(
		str,
		description = 'Human-readable skill name',
	),
	effect = o.F(
		str,
		description = 'What this skill enables an agent to do',
	),
)
```

the prompt representation carries both structure and meaning.

This gives AI systems a representation derived from the same ontology the application itself uses.

There is no separate AI schema that must be manually kept synchronized with the application model.

---

# o as an AI world model

Agentic systems need more than text.

They need a world with continuity.

A useful agent environment needs entities that:

- continue to exist after a prompt ends
- retain identity across processes
- have explicit structure
- carry semantic meaning
- form relationships
- can be discovered
- can be changed
- remember those changes
- can evolve as new concepts appear

That is exactly the kind of world `o` is designed to represent.

```text
              persistent ontology
                      │
        ┌─────────────┼─────────────┐
        │             │             │
      types        entities     relationships
        │             │             │
        └─────────────┼─────────────┘
                      │
                   meaning
                      │
                      ▼
                     AI
```

An agent can inspect the same structure the application uses.

It can create entities.

It can modify them.

It can create new runtime types.

It can extend the ontology.

And those changes remain part of the persistent world.

---

# Semantic search and vector databases

The ontology also provides a natural foundation for semantic retrieval.

Every meaningful node in the graph can be represented by an embedding and indexed in an external vector database.

Conceptually:

```text
persistent object graph
        │
        ├── structural relationships
        │
        └── semantic representation
                    │
                    ▼
               embedding
                    │
                    ▼
              vector index
                    │
                    ▼
             semantic search
                    │
                    ▼
             persistent entity
```

This creates two complementary ways to navigate the world:

```text
structure  → explicit relationships
meaning    → vector similarity
```

An agent can therefore navigate:

```text
relationship
    ↓
relationship
    ↓
semantic jump
    ↓
related entity
    ↓
relationship
```

The ontology provides structure.

Embeddings provide meaning-based navigation.

---

# Metadata as a semantic surface

The `._` metadata surface makes this particularly interesting for AI systems.

A node or field can carry information explaining what it means in the ontology.

Conceptually, applications can build semantic extensions such as:

```python
entity._.description
entity._.context
entity._.vector
```

where semantic metadata or vector representations can be associated with ontology nodes and indexed externally.

`o` itself provides the persistent structural and metadata foundation; vector database integration can be layered on top.

This separation is intentional:

```text
o     = persistent truth and structure
._    = metadata about that structure
vecdb = semantic retrieval over selected representations
```

Together, these can form a world that is navigable both structurally and semantically.

---

# Multi-agent systems

Because persistent state belongs to the world rather than to an individual Python process, `o` naturally fits systems where multiple processes or agents need to operate over the same conceptual environment.

Instead of every agent maintaining an independent representation:

```text
Agent A → memory A
Agent B → memory B
Agent C → memory C
```

the architecture can be centered around a shared persistent ontology:

```text
             Agent A
                │
                ▼
Agent B ──→ persistent world ←── Agent C
                ▲
                │
            application
```

Each participant can reason about the same entities, types, and relationships.

This makes `o` interesting as a substrate for:

- persistent agent memory
- world models
- knowledge graphs
- semantic memory
- tool state
- multi-agent environments
- long-running autonomous systems
- adaptive ontologies
- AI-native applications

---

# Web applications

Although `o` was designed around a persistent object world, the same architecture is naturally useful for Web applications.

A conventional Web stack may maintain:

```text
domain model
validation model
ORM model
database schema
DTO
serialization schema
API schema
```

With `o`, much of that information can originate from one persistent Python model:

```text
                Python entity
                     │
        ┌────────────┼────────────┐
        │            │            │
   validation    persistence   serialization
        │            │            │
        └────────────┼────────────┘
                     │
                JSON Schema
                     │
                     ▼
                    API
```

This can reduce mapping layers and make divergence between runtime state and persistence harder to introduce.

> **Built for AI. Remarkably natural for the Web.**

---

# Performance

`o` is built on LMDB.

The architecture is optimized around fast persistent reads and batched transactions for write-heavy workloads.

A benchmark snapshot used during current development:

| Operation | Single transaction | Batched transaction | Speedup |
|---|---:|---:|---:|
| List read | **1.39M/s** | **1.43M/s** | **1.03×** |
| List write | **341/s** | **14.21k/s** | **41.7×** |
| Dict read | **436k/s** | **509k/s** | **1.17×** |
| Dict write | **339/s** | **8.83k/s** | **26.1×** |
| Object attribute read | **7.69M/s** | **8.20M/s** | **1.07×** |
| Object attribute write | **195/s** | **15.51k/s** | **79.5×** |
| Object creation | **55.4/s** | **6.84k/s** | **123.6×** |
| Class definition | **54.2/s** | **6.31k/s** | **116.6×** |

The important distinction is transaction shape.

Reads reach hundreds of thousands to millions of operations per second in these benchmarks, while batched writes reach thousands per second.

Single-operation writes are substantially more expensive because transaction overhead dominates small mutations.

Performance is workload- and environment-dependent. These numbers are development benchmark results, not universal guarantees.

---

# Transactions

The storage layer supports explicit read and write transaction scopes.

For workloads containing many persistent mutations, operations can be grouped into a single transaction:

```python
with o.services.Memory.write():
	# many persistent operations
	...
```

This is particularly important for high-throughput mutation workloads.

Instead of paying transaction overhead for every operation:

```text
write → transaction
write → transaction
write → transaction
write → transaction
```

batching allows:

```text
transaction
    ├── write
    ├── write
    ├── write
    └── write
```

The performance difference can be substantial.

---

# Storage architecture

`o` uses LMDB as its persistent storage engine.

The storage layer provides:

- transactional reads and writes
- persistent namespaces/zones
- compact ID-based references
- stable proto-to-ID mapping
- persistent route metadata
- reference-counted object lifecycle

At the object layer, references are stored as entity IDs rather than serialized copies of entire child objects.

Conceptually:

```text
Person._17
│
├── name ─────→ Str._42
├── age ──────→ Int._11
└── project ──→ Project._8
```

The object graph and persistent graph are therefore the same conceptual structure.

---

# Identity model

`o` distinguishes between semantic address and compact persistent identity.

Every persistent entity has a canonical proto path:

```text
o.T.Person._17
```

That proto maps to a stable positive integer ID:

```text
proto
  │
  ▼
hash / persistent mapping
  │
  ▼
 id
```

References between entities can then be stored compactly using IDs while the ontology retains a human-readable structural address.

This gives `o` both:

```text
structural identity → proto
storage identity    → id
```

without exposing database primary-key mechanics as the application's conceptual model.

---

# Object lifecycle

`o` tracks persistent references between entities.

When an entity gains a persistent owner, its reference count is increased.

When a persistent relationship is removed, the count is decreased.

Entities with no remaining persistent references become eligible for collection.

This allows lifecycle to emerge from the graph itself:

```text
persistent structure
       │
       ▼
reference topology
       │
       ▼
object lifetime
```

This is different from Python's process-local object lifetime.

A Python process may disappear while the persistent graph remains.

---

# Type inheritance

Persistent types support inheritance:

```python
Person = o.T.extend(
	'Person',
	name = str,
)

Employee = Person.extend(
	'Employee',
	role = str,
)

Researcher = Employee.extend(
	'Researcher',
	field = str,
)
```

The resulting ontology is structural:

```text
o.T
└── Person
    └── Employee
        └── Researcher
```

Fields are inherited through the type hierarchy.

This allows domain taxonomies to be expressed using ordinary object-oriented structure while remaining part of the persistent ontology.

---

# Runtime type creation

Types do not have to originate from static source definitions.

They can be created dynamically:

```python
Concept = o.T.extend(
	'Concept',
	name        = str,
	description = str,
)
```

This matters for systems that discover new concepts while running.

An AI system, for example, can move beyond merely creating another row of an existing type.

It can extend the vocabulary of the world itself.

```text
observe something new
        ↓
identify new concept
        ↓
create persistent type
        ↓
create entities of that type
        ↓
concept becomes part of ontology
```

That is a fundamentally different capability from inserting untyped memory records into a vector store.

---

# Reflection

The ontology can inspect its own structure.

For example:

```python
Person._.name.type
Person._.name.description
Person._.name.default
Person._.name.is_optional
```

Types can also export machine-readable representations:

```python
Person.to_json_schema()
Person.to_prompt()
```

This makes the world self-describing enough for:

- developer tooling
- API generation
- model prompting
- schema inspection
- autonomous agents
- semantic indexing
- debugging
- visualization

---

# Serialization vs persistence

These are intentionally separate concepts in `o`.

### Persistence

Persistence preserves the identity and state of an entity inside the `o` world.

```python
o.V.alexander = alexander
```

### Serialization

Serialization creates a portable structural representation:

```python
spec = alexander.serialize()
```

The serialized representation can include the type definitions required to reconstruct the object.

Persistence answers:

> **Where does this entity continue to live?**

Serialization answers:

> **How can this entity and its structure be represented outside that world?**

---

# What o is not

`o` is not an ORM.

An ORM maps Python objects onto a separate relational model.

`o` makes persistence part of the object system itself.

`o` is not merely a key-value store.

LMDB provides the storage substrate, but the application works with persistent typed entities, fields, relationships, inheritance, and identity.

`o` is not a vector database.

Vector representations and semantic indexes can be layered over the ontology, while `o` remains responsible for persistent structure and entities.

`o` is not intended to hide the existence of storage.

It changes where persistence lives conceptually:

```text
traditional

object
  ↕ mapping
database model


o

persistent object
```

---

# Design principle

The central idea behind `o` is simple:

> **Code and state should not have to diverge.**

A Python program already describes:

- concepts
- types
- composition
- relationships
- behavior
- constraints

A database separately describes:

- identity
- storage
- relationships
- schema
- lifetime

`o` asks:

> Why should these be two different worlds?

Its answer is a persistent Python ontology in which program structure and persistent state inhabit the same object system.

---

# Why this matters for AI

Today's AI systems frequently operate through translation layers:

```text
model
 ↓
tool schema
 ↓
API
 ↓
DTO
 ↓
business logic
 ↓
ORM
 ↓
database
```

At every boundary, some structure and meaning must be translated.

An agent-native world can instead expose the concepts themselves.

```text
AI
 │
 ▼
persistent ontology
 │
 ├── entities
 ├── types
 ├── relationships
 ├── metadata
 ├── identity
 └── state
```

The agent can inspect the world.

Understand its structure.

Find things by relationships or meaning.

Create new things.

Change existing things.

Extend the ontology.

And leave those changes behind for the next process, application, human, or agent.

---

# A world, not just storage

The long-term idea behind `almasi.o` is larger than object persistence.

An intelligent system needs continuity.

It needs things that remain things.

It needs relationships that survive the process that observed them.

It needs concepts whose meaning can be inspected.

It needs memory that is more structured than a transcript.

It needs a world it can act upon.

`o` provides the persistent object substrate for such a world.

```text
a persistent world
    +
an understandable world
    +
an operable world
```

> **AI needs a world it can understand, remember, and change.**

> **almasi.o is that world.**

---

# Project status

`almasi.o` is under active development.

Its architecture and public API are evolving as the persistent ontology model is refined.

Current implemented areas include:

- persistent typed entities
- stable entity IDs
- LMDB-backed storage
- persistent lists and dictionaries
- Python atomic value embodiment
- deep mutation persistence
- persistent references
- reference-counted lifecycle
- runtime type creation
- persistent inheritance
- runtime field extension
- field metadata
- JSON conversion
- structural serialization/deserialization
- JSON Schema generation
- AI-oriented prompt schema generation
- reconstruction of serialized runtime types

Future layers can build semantic search, vector indexing, richer graph navigation, agent memory, and AI-native tooling on top of this persistent substrate.

---

# Repository

The source code is available on GitHub:

https://github.com/apodgorny/o

Technical overview:

https://youtu.be/M8GxATOocD0

---

# Author

**Alexander Podgorny**

AI architect and systems researcher.

[LinkedIn](https://www.linkedin.com/in/podgorny/)