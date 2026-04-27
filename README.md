# wikimark-python

Python bindings for [WikiMark](https://github.com/trellis-wiki/wikimark).
A thin [CFFI](https://cffi.readthedocs.io/) wrapper around
[libwikimark](https://github.com/trellis-wiki/libwikimark) — the C
reference implementation.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)

## Status

**Pre-alpha.** Bindings in place, unverified against a live build. The
CFFI wrapper is written but hasn't been compiled in the development
environment because `python3-dev` isn't installed here. See
[PLAN.md](PLAN.md) for remaining work.

## Building

1. Build libwikimark first (see its repo). The build must produce
   static libraries under `libwikimark/build/`:
   - `libwikimark.a`
   - `third_party/cmark-gfm/src/libcmark-gfm.a`
   - `third_party/cmark-gfm/extensions/libcmark-gfm-extensions.a`
   - `third_party/libyaml/libyaml.a`

2. Install system build requirements:
   - Python 3.11+ with development headers (`python3-dev` on
     Debian/Ubuntu)
   - A C11-capable C compiler
   - `pip` and `venv`

3. From this directory:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

   If your libwikimark checkout isn't at `../libwikimark`, set:
   ```bash
   export LIBWIKIMARK_DIR=/path/to/libwikimark
   export LIBWIKIMARK_BUILD_DIR=/path/to/libwikimark/build
   ```

## Usage

```python
import wikimark

html = wikimark.render("See [[Main Page]] for details.")
# '<p>See <a href="Main_Page">Main Page</a> for details.</p>\n'
```

### With base URL

```python
html = wikimark.render("[[Home]]", base_url="/wiki/")
# '<p><a href="/wiki/Home">Home</a></p>\n'
```

### With interwiki prefixes

```python
html = wikimark.render(
    "[[wikipedia:Paris]]",
    interwiki=[
        wikimark.Interwiki("wikipedia", "https://en.wikipedia.org/wiki/{page}"),
    ],
)
```

### With engine callbacks

Templates, variables, and page embeds resolve through engine-provided
callbacks. Without them, `{{...}}` and `![[...]]` produce error
indicators.

```python
def resolve_template(name: str, args: str | None) -> str | None:
    if name == "greeting":
        return "<span>Hello!</span>"
    return None

def resolve_embed(target: str) -> str | None:
    if target == "Shared/Header":
        return "<p>rendered shared content</p>"
    return None

html = wikimark.render(
    "{{greeting}} ![[Shared/Header]]",
    resolve_template=resolve_template,
    resolve_embed=resolve_embed,
)
```

Callbacks return rendered HTML (not WikiMark source — libwikimark
does not recursively reparse the result). Returning ``None`` makes
libwikimark emit an error placeholder.

## Options

```python
import wikimark

html = wikimark.render(
    source,
    options=wikimark.OPT_UNSAFE,  # allow raw HTML
)
```

Available options (re-exported from cmark-gfm):
`OPT_DEFAULT`, `OPT_SOURCEPOS`, `OPT_HARDBREAKS`, `OPT_NOBREAKS`,
`OPT_SMART`, `OPT_UNSAFE`.

## Testing

```bash
pip install -e ".[dev]"
pytest
```

The test suite includes:
- `tests/test_render.py` — feature smoke tests
- `tests/test_spec_suite.py` — the full 1,556-test WikiMark spec
  suite, with 85 documented baseline exclusions

## License

[MIT](LICENSE)

## Related

- [WikiMark spec](https://github.com/trellis-wiki/wikimark)
- [libwikimark](https://github.com/trellis-wiki/libwikimark) — C
  reference parser this wraps
- [Trellis](https://github.com/trellis-wiki/trellis) — the wiki
  engine that consumes this binding
