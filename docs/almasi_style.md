# Almasi Architecture & Code Style

**Normative guidance for Codex and contributors to Almasi-based repositories.**

This document combines Almasi's established architectural invariants with the project owner's mandatory coding style. **Read this document, the repository's `/docs`, and nearby implementations before writing code.** Where historical Almasi invariant documents differ, prefer the newest applicable invariant and verify against the current implementation. Explicit project-owner instructions override generic Python conventions.

## 1. Core architecture

1. **Filesystem is API.** The directory tree under `root/` is the public namespace. For example, `root/agents/scenario_agent.py` resolves to `repo101.agents.ScenarioAgent`. Never introduce a redundant registry, export facade, discovery mechanism, import router, or resource loader.
2. **Library is a class.** An Almasi library or application is declared through `a.A` (or the appropriate library ancestor). Its lowercase published face is derived, not manually instantiated or aliased. Use native `initialize()` where initialization is required.
3. **Behavior belongs to classes.** Files in a library's resolved component tree are not bags of standalone functions. Put behavior on the component responsible for it. An application entry point such as `main.py` is an orchestration boundary, not an excuse for a procedural subsystem.
4. **One Python carrier, one corresponding class.** Every `.py` component loaded by Almasi's Python carrier mechanism defines exactly one loadable class, named to match its snake-case file (`scenario_agent.py` → `ScenarioAgent`). It must inherit `a.Module` or an appropriate Almasi-derived class such as `do.base.Agent` or `a.Service`. This rule applies to resolved carriers, not arbitrary infrastructure scripts.
5. **Names carry meaning.** Capitalized symbols denote classes/types; lower-case names ordinarily denote filesystem-resolved namespace children. Do not confuse storage paths, `__route__`, Python module identity, and class identity.
6. **Local-first namespace inheritance.** Rely on Almasi's native class lineage and namespace resolution. Do not recreate inherited lookups through manual imports, copies, registries, or fallback scanners.
7. **Direct access realizes; iteration discovers.** `edu.expertise.scenario` retrieves the usable resource. Iterating a namespace discovers file/directory carriers. Do not introduce custom Markdown/JSON loaders where Almasi already resolves the content.
8. **Single owner of identity and state.** Python modules are authoritative through `sys.modules`, class identity through the loaded Python module, namespace-child carriers through their directory/library face, realized file content through `File`, and singleton identity through the service class. Avoid parallel caches and registries.
9. **Service lifecycle is canonical.** Shared services use `Service` and its existing canonical instance/lifecycle. Do not inspect `__dict__`, `_is_initialized`, or other private internal flags from client code. Use the supported initialization and execution API, or improve that public API in the owning library.
10. **Plugins interpret sources; directories describe topology.** The library resolver and its plugins perform resource discovery and loading. `Directory` represents a namespace directory, not a second content cache. Respect ownership boundaries.
11. **Explicit paths and OS mutations.** For an existing Almasi directory, use its `.path` when filesystem I/O is actually needed. Current Almasi `Directory` does **not** have a `mkdir()`/`create()` method; use `os.makedirs(...)` for creating physical directories unless a native method is explicitly added. Do not invent methods in examples or silently mutate paths via namespace lookup.
12. **No escape hatches around Almasi.** Avoid `edu_internal`, manual `root` path reconstruction, custom component registries, reflective lifecycle probes, or package-level hacks to bypass the intended API. Improve the owning public component instead.

## 2. Responsibility and composition

13. **Ownership determines placement.** Scenario validation and playback belong to `edu.Player`; DOM geometry to `edu.Browser`; video assembly to `edu.Renderer` when that component exists; reusable LLM infrastructure to `do`; application intent and orchestration to `repo101`. Do not force a consumer to know a dependency's Docker setup, private file structure, or other implementation details.
14. **Native agent contract.** Implement agents with `schema`, `template`, `invoke`. Invoking an agent uses the inherited class-call semantics; inside `invoke`, call `await self()` to perform an LLM request. Do not override `__call__` simply to choose a model for one agent; solve model selection using the framework's established extension points, updating the framework when necessary.
15. **Use Almasi/O schemas.** Express structured agent output through `o.T` and `o.F`, not hand-written JSON Schema dictionaries as a replacement for that type system. An output schema is not the scenario instance: after conversion/validation, an Edu scenario remains a plain Python `dict`.
16. **No redundant models.** Do not wrap dict/list/string data in classes without an independently justified identity, lifecycle, or behavior. Do not create `Manager`, `Factory`, `Context`, `Adapter`, `Controller`, etc. just to rename existing responsibilities.
17. **One source of truth.** Do not copy Edu's operation catalog or constraints into Repo101 when they can be derived from Edu. Do not maintain competing declarations for the same schema, state, or lifecycle.
18. **Application entry point expresses intent.** `main.py` should read as a small sequence of domain operations, not container preparation, IDE settings patching, rendering plumbing, and private-state tests. Move mechanisms into the library that owns them.
19. **Applications need not be installed as libraries.** For the present Repo101 application, do not add `pyproject.toml`, editable registration, or an application installer merely to reuse it locally. This is a project-specific decision, not a ban on packaging reusable Almasi libraries.
20. **Structural simplicity beats cosmetic refactoring.** Splitting a monolith into many tiny functions is not enough if dependencies and ownership stay wrong. Eliminate redundant concepts and move responsibility to the correct owner.
21. **Prefer declarative intent.** APIs should describe *what* to do; their owning components encapsulate *how*. Expose the smallest usable public surface; allow complexity inside its rightful owner.
22. **No speculative architecture.** Do not introduce timeline frameworks, agents, abstractions, migrations, or compatibility layers before the task needs them. Extend existing mechanisms only after studying them.

## 3. Mandatory Python formatting

23. **Indent using tabs**, not spaces. Preserve the repository's existing indentation convention throughout any touched code.
24. **Use single quotes** for ordinary Python strings. Use triple-single-quoted strings for multiline literals unless a technical need dictates otherwise.
25. **At most one `return` statement per method/function.** Prefer a final return of a named result where a result is required. Do not contort simple control flow into unnecessary flags; reconsider the method boundary when one-return structure becomes awkward.
26. **No `continue` statements.** Express iteration with clear conditionals and unambiguous progression.
27. **No `pathlib`.** Use the existing Almasi path facilities and `os.path`/`os` where raw filesystem operations are necessary.
28. **Do not use `helper` or `util` in identifiers.** Choose a name that describes real domain responsibility. Avoid vague nouns such as `manager` or `processor` unless they truly express an established concept.
29. **Vertically align adjacent operators** in cohesive groups of assignments, class attributes, mappings, and keyword arguments when the repository's style uses alignment. Alignment is local to one logical block, not across unrelated code.
30. **Exactly one empty line between operator-aligned blocks.** When two separately aligned logical blocks are adjacent, separate them with **one and only one blank line**; do not merge their alignment columns across blocks and do not insert multiple blank lines. Apply the same single-blank-line discipline to adjacent logical sections in a method where appropriate.
31. **Preserve compact, deliberate whitespace.** Group related operations visually. Avoid sprawling vertically padded code and long run-on expressions. Use a line break when it reveals structure, not automatically whenever a formatter might wrap a line.
32. **Comments explain purpose or non-obvious reasoning.** Follow the established comment format:

    ```python
    # Prepare the recording before playback begins.
    # ----------------------------------------------------------------------
    ```

    Comment blocks should sit immediately before the relevant logical unit. Do not narrate obvious Python syntax or add ornamental separators without a meaningful section.
33. **Prefer meaningful domain names.** Use `snake_case` for methods/variables/files, `PascalCase` for classes, and stable existing Almasi names for intrinsic framework concepts. Do not introduce synonyms that fracture the vocabulary.
34. **Minimize intermediate variables.** Retain variables that clarify domain meaning, represent a real intermediate state, or prevent duplication; remove one-use aliases and ceremonial indirection. This is not a mandate to write unreadable nested expressions.
35. **Keep methods focused.** An operation should have one coherent responsibility and a comprehensible state transition. Prefer the owning class's method over creating a loose function or a new class to avoid editing an existing abstraction.
36. **Avoid gratuitous overrides.** If an inherited method already provides the desired semantics, use it. An override must express an actual extension of the contract, not a convenient bypass.
37. **Do not mask broken invariants.** Avoid blanket catches, silently chosen fallbacks, broad retries, and checks duplicating what the framework guarantees. Validate at genuine trust/side-effect boundaries and let actionable failures surface.
38. **Keep imports plain and purposeful.** Use the library's published Almasi interface (`import edu`, `import do`, etc.). Avoid importing private implementation modules merely to reach public functionality.
39. **Respect local style over generic autoformatting.** Do not run a formatter that destroys tabs, single quotes, intentional alignment, or comment formatting. PEP 8 is not authority over these explicit rules.

### Example of correctly separated alignment blocks

```python
name   = 'demo'
source = 'demo.py'

width  = 1600
height = 900

result = await edu.Player.play(scenario)
```

Each aligned group has its own width and is separated from the next group by **exactly one** blank line.

### Example of a native agent outline

```python
import do, o


class ScenarioAgent(do.base.Agent):

	persona = 'Developer video author'
	intent  = 'Creating executable Edu scenarios'

	schema = o.T.extend(
		title  = o.F(str, 'Video title.'),
		scenes = o.F(list, 'Sequential Edu scenes.')
	)

	template = '''
		REQUEST:
		{{ctx.input.prompt}}

		EXPERTISE:
		{{ctx.input.expertise}}
	'''

	# Generate through the inherited agent request mechanism.
	# ----------------------------------------------------------------------
	async def invoke(self, prompt, expertise):
		result = await self()
		return result
```

*The snippet is an outline of the intended framework contract, not a complete scenario validator or a substitute for examining current `do` examples.*

## 4. Workflow for Codex

40. **Read before changing anything.** Inspect the relevant `/docs` and current source of `a`, `o`, `do`, `edu`, and the consuming application. Do not infer API behavior from names or earlier code examples.
41. **Identify authority and owner.** For every added method, schema, lifecycle hook, and file, explain which component owns it and whether the framework already offers it.
42. **Use real contracts.** Verify inheritance, route resolution, available methods, `Service` lifecycle, and agent invocation semantics in source before coding. Historical docs are interpreted using newer superseding decisions and runtime reality.
43. **Make the smallest native change.** Prefer one correct modification in the owning class to a workaround in a consumer. Avoid new entities unless absolutely required.
44. **Review style manually.** Check tabs, quote style, single-return count, no `continue`, no `pathlib`, forbidden naming, aligned blocks, exactly-one-blank-line separation, and house comment conventions.
45. **Test actual behavior.** Verify native namespace resolution, real resource loading, agent execution, and output behavior with integration testing where relevant. Do not report mocked tests as proof of live execution.
46. **Report deviations.** If a task genuinely requires breaking one of these rules, stop and explain the exact reason before implementing the exception. Do not silently introduce an alternative convention.

## 5. Review checklist

- [ ] Relevant `/docs` and neighboring implementations read first
- [ ] Almasi filesystem namespace preserved
- [ ] Exactly one corresponding Almasi-derived class in each resolved `.py` carrier
- [ ] Class/library/service/agent lifecycle semantics respected
- [ ] No parallel registries, loaders, schema catalogs, or state owners
- [ ] Ownership boundaries respected; no private cross-library shortcuts
- [ ] Structured schema uses `o.T` / `o.F`; ordinary data remains ordinary data
- [ ] `main.py` describes intent, not infrastructure plumbing
- [ ] Tabs and single-quoted strings
- [ ] No more than one `return` per function/method
- [ ] No `continue`, `pathlib`, `helper`, or `util` naming
- [ ] Operators aligned in logical groups
- [ ] Exactly one blank line between separately aligned blocks
- [ ] Purposeful comments in repository convention
- [ ] No unnecessary entities, aliases, wrappers, or defensive branches
- [ ] Actual tests and integration behavior verified

**Guiding principle:** *Almasi should remove architecture, not add architecture.*
