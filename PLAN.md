# wikimark-python — Sub-project Plan

Python bindings for WikiMark. The package name is `wikimark` on
PyPI; the repo is called `wikimark-python` to match the naming
pattern of other libwikimark bindings.

Parent plan: [../PLAN.md](../PLAN.md)

## Role

Give Python code a way to render WikiMark. Specifically:
- Call `wikimark_render()` from Python
- Register Python functions as `resolve_variable`,
  `resolve_template`, `resolve_embed` callbacks
- Get the resulting HTML back as a Python `str`

The Trellis engine is (assumed) a Python application. It consumes
this package to do rendering. Nothing in `wikimark-python` parses
WikiMark on its own — the parser is libwikimark, full stop.

## Current state

**Dead code.** The repo is scaffolded but abandoned:

- `pyproject.toml` exists, package name `wikimark`, version 0.1.0
- `src/wikimark/parser.py` raises `NotImplementedError`
- `src/wikimark/ast.py`, `block_parser.py`, `inline_parser.py`,
  `frontmatter.py`, `normalize.py`, `templates.py`, `renderer.py`,
  `config.py` — all empty or stub
- `src/wikimark/cli.py` — skeleton, non-functional
- `src/wikimark/__init__.py` — imports stubs, provides an API
  surface that raises when called
- `tests/` — imports stubs; no test actually exercises rendering
- **README claims "Full GFM 0.29 support" and lists every WikiMark
  feature as working.** It is all a lie. The README also documents
  removed syntax (`[[Page|display]]`, inline `#REDIRECT`) — so
  whatever version the README describes, it isn't even the current
  spec.

## Decision (for Nick's confirmation)

**Kill the pure-Python implementation. Rebuild as a thin CFFI
wrapper around libwikimark.**

Rationale:
- libwikimark is the *reference* implementation. A second pure-Python
  reparse would violate "one parser, many bindings" and guarantee
  drift.
- Trellis will be Python (assumed), so it needs *some* libwikimark
  binding. CFFI is the lowest-friction option.
- The existing stub modules are 100% dead code; nothing is lost by
  deleting them.
- CFFI bindings to a small C API (~4 functions, 2 structs) are a
  couple hundred lines tops.

If Nick wants a different binding tech (Cython, pybind11, direct
`ctypes`), say so — but CFFI is the default unless a reason comes
up.

## Gaps from "working binding"

1. No build hook that locates or vendors libwikimark
2. No CFFI definitions
3. No Python wrapper classes around the C structs
4. No callback marshalling (C function pointers ↔ Python callables)
5. No test coverage
6. README is a hallucination

## Task list

### Group A — Demolition (Phase 0)
- [ ] **T1** Rewrite `README.md`. Describe real state ("pre-binding
      stub — CFFI wrapper coming"). Delete references to piped
      wiki links and inline redirects.
- [ ] **T2** Delete stub modules: `parser.py`, `block_parser.py`,
      `inline_parser.py`, `ast.py`, `frontmatter.py`, `normalize.py`,
      `renderer.py`, `templates.py`, `config.py`, `cli.py`. Keep
      `__init__.py` as an empty placeholder.
- [ ] **T3** Delete the test files that exercise the stubs.

### Group B — CFFI binding (Phase 2)
- [ ] **T4** Add `cffi` to `pyproject.toml` build and runtime deps.
- [ ] **T5** Create `src/wikimark/_build.py` that invokes CFFI's
      `ffi.cdef()` with the libwikimark public API and
      `ffi.set_source()` to compile against the installed
      libwikimark. Decide: require libwikimark to be pre-installed,
      or vendor it as a submodule and build in-tree? Pre-installed
      is simpler but adds packaging friction; vendoring is heavier
      but makes `pip install wikimark` self-contained.
- [ ] **T6** Create `src/wikimark/__init__.py` with a minimal Python
      API:
      ```python
      def render(text: str, *, base_url: str = "",
                 resolve_variable=None, resolve_template=None,
                 resolve_embed=None) -> str: ...
      ```
      Handle encoding (Python str ↔ C `const char*`), lifetime of
      returned strings, and exception safety.
- [ ] **T7** Implement callback marshalling: when a Python resolver
      is passed in, wrap it in a C-compatible function pointer via
      `ffi.callback()`. Handle exceptions raised from Python (don't
      let them propagate through the C layer).
- [ ] **T8** Add tests that render a document with each feature (wiki
      links, frontmatter, variables via resolver, templates via
      resolver, embeds via resolver). Run them under pytest in CI.

### Group C — Spec conformance
- [ ] **T9** Port the `run_tests.py` harness from the spec repo so
      `pytest` can run the full 1,556-pair suite against
      `wikimark.render()`. Expect the same 85 baseline exclusions as
      libwikimark. Add exclusions file if needed.

### Group D — Release
- [ ] **T10** Tag 0.1.0 once the test suite passes and Trellis has
      successfully imported the package.

## Verification

- [ ] `pip install -e .` works in a clean venv
- [ ] `python -c "import wikimark; print(wikimark.render('[[Home]]'))"`
      prints `<p><a href="Home" class="wm-wikilink">Home</a></p>` (or
      whatever the current normalized form is)
- [ ] Spec test suite passes against the Python binding
- [ ] Callback exceptions raised in Python resolvers surface as
      Python exceptions, not segfaults
- [ ] Trellis imports `wikimark` and renders its pages end-to-end

## Out of scope

- Pure-Python parser (killed)
- Sync / async split (keep sync; Trellis can wrap with `asyncio.to_thread`)
- Type stubs / mypy support beyond basic annotations
- Packaging wheels for every platform — build-from-source is fine for
  v0.1
- CLI (the libwikimark CLI handles command-line use)
