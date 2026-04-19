# wikimark-python — Sub-project Plan

Python bindings for WikiMark. The package name is `wikimark` on
PyPI; the repo is called `wikimark-python` to match the naming
pattern of other libwikimark bindings.

Parent plan: [../PLAN.md](../PLAN.md)

## Role

Give Python code a way to render WikiMark. Specifically:
- Call `wikimark.render()` from Python
- Register Python functions as `resolve_variable`,
  `resolve_template`, `resolve_embed` callbacks
- Read parsed YAML frontmatter via `wikimark.read_frontmatter()`
- Get rendered HTML back as a Python `str`

The Trellis engine is Python. It consumes this package to do
rendering. Nothing in `wikimark-python` parses WikiMark on its own —
the parser is libwikimark, full stop.

## Current state

**Working CFFI binding.** Ships today as a thin wrapper around
libwikimark's C API. Stats:

- **Version:** 0.1.0
- **Package layout:**
  - `src/wikimark/__init__.py` — public API (`render`,
    `read_frontmatter`, `Frontmatter`, `Interwiki`, `OPT_*` consts)
  - `src/wikimark/_build.py` — CFFI cdef + link configuration
  - `setup.py` — hooks `cffi_modules` into setuptools
- **Build requirements:**
  - Python 3.11+ with development headers (`python3-dev`)
  - A C11 compiler
  - libwikimark built with `-fPIC` (enabled by default as of the
    libwikimark CMake update, commit 0fe636f)
  - Path to libwikimark via the `LIBWIKIMARK_DIR` /
    `LIBWIKIMARK_BUILD_DIR` environment variables, or default
    location of `../libwikimark/` next to this repo
- **Test results:**
  - 31 feature smoke tests (`tests/test_render.py`)
  - Full WikiMark spec suite: 1,471 passed + 85 xfailed (matches
    libwikimark's documented baseline exclusions exactly)
  - Fixture engine at `tests/_engine.py` mirrors the libwikimark
    CLI's `test_engine.c` so templates and embeds in spec tests
    resolve against the same fixture data
- **Callback safety:**
  - Python exceptions raised inside resolver callbacks are caught
    at the C boundary and treated as "unresolved" rather than
    allowed to propagate
  - Per-render `_RenderArena` retains strong refs to every CFFI-
    owned bytes buffer so strings stay alive for libwikimark's
    "valid until render returns" contract
  - `Frontmatter` is a context manager; GC cleans up if not used
    with `with`

## Design decisions (locked)

| Decision | Choice | Rationale |
|---|---|---|
| Binding tech | **CFFI** (out-of-line / API mode) | Standard for Python-to-C; mature; simpler than Cython for a thin wrapper |
| Build backend | **setuptools** + `cffi_modules` via setup.py | Most widely supported CFFI integration path |
| libwikimark location | Env-var or sibling directory | Simple for local development; packaging for wheels comes later |
| Spec conformance | Fixture-engine replica of libwikimark CLI behavior | Matches exact pass/fail counts |

## Remaining tasks

### Group A — v0.1 polish (unblocked)

- [ ] **T10** Tag 0.1.0 once Trellis has consumed it end-to-end.

### Group B — Packaging (post-v0.1)

- [ ] **T11** Build and publish binary wheels for common platforms
      (Linux x86-64, macOS arm64/x86-64, Windows x86-64). Currently
      build-from-source only.
- [ ] **T12** Decide whether to vendor libwikimark as a submodule so
      `pip install wikimark` works without a separate libwikimark
      checkout. Trade-off: larger package vs. zero-setup install.
- [ ] **T13** CI workflow for this repo independently of libwikimark
      (build libwikimark as a step, then build wheel, run pytest).

### Group C — Feature expansion (as Trellis discovers needs)

- [ ] **T14** Expose more of libwikimark's public API if Trellis
      needs it: node accessors, additional render options, custom
      allocators. Keep the surface minimal; add only when needed.

## Completed

- [x] **T1** Rewrite `README.md` to reflect real state. *(Landed in
      pre-binding stub README, then expanded after CFFI wrapper
      shipped in commit 8ae60e7.)*
- [x] **T2** Delete pure-Python stub modules (`parser.py`,
      `block_parser.py`, `inline_parser.py`, `ast.py`,
      `frontmatter.py`, `normalize.py`, `renderer.py`,
      `templates.py`, `config.py`, `cli.py`, `py.typed`).
      *(Landed in commit 8ae60e7.)*
- [x] **T3** Delete stub test files. *(Landed in commit 8ae60e7.)*
- [x] **T4** Add `cffi` to `pyproject.toml`. *(Landed in commit
      8ae60e7.)*
- [x] **T5** `src/wikimark/_build.py` with `ffibuilder.cdef()` and
      `ffibuilder.set_source()`. *(Landed in commit 8ae60e7;
      frontmatter API added in commit f29e830.)*
- [x] **T6** `src/wikimark/__init__.py` public API: `render(source,
      *, options, base_url, interwiki, resolve_variable,
      resolve_template, resolve_embed) -> str`. *(Landed in commit
      8ae60e7.)*
- [x] **T7** Callback marshalling via `@ffi.def_extern()`
      trampolines + per-render arena for lifetime management.
      Python exceptions in callbacks are swallowed to avoid
      propagating through the C boundary. *(Landed in commit
      8ae60e7.)*
- [x] **T8** Feature smoke tests — 25 at launch, expanded to 31
      with the frontmatter API and the bare-bracket regression
      pin. *(Landed in commit 8ae60e7; extended in commits f29e830
      and the bare-bracket regression test.)*
- [x] **T9** Spec suite runner — parametrized pytest that runs the
      full 1,556-test WikiMark spec suite with the documented 85
      baseline exclusions as xfailed. Also includes the fixture
      engine at `tests/_engine.py` so template and embed tests
      resolve against the same data as the libwikimark CLI.
      *(Landed in commit 8ae60e7.)*
- [x] **wikimark.read_frontmatter()** — added alongside libwikimark's
      new public `wikimark_frontmatter_parse/get/free` C API.
      *(Landed in commit f29e830.)*

## Verification

- [x] `pip install -e .` works in a venv
- [x] `python -c "import wikimark; print(wikimark.render('[[Home]]'))"`
      prints `<p><a href="Home">Home</a></p>`
- [x] Full spec test suite passes (1,471 + 85 xfailed, matching
      libwikimark)
- [x] Callback exceptions raised in Python resolvers surface as
      unresolved references, not segfaults
- [ ] Trellis imports `wikimark` and renders pages end-to-end
      *(gated on Trellis T-0 / T-3)*

## Out of scope

- Pure-Python parser (permanently retired)
- Sync / async split (keep sync; Trellis can wrap with
  `asyncio.to_thread` where needed)
- Type stubs / mypy support beyond basic annotations
- CLI (the libwikimark CLI handles command-line use)
- Embedding libwikimark sources in the wheel (T12 open)
