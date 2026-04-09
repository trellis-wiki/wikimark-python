# wikimark-python

A Python implementation of [WikiMark](https://github.com/trellis-wiki/wikimark), a strict superset of [GitHub Flavored Markdown](https://github.github.com/gfm/) with wiki links, templates, semantic annotations, and structured page metadata.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)

## Features

- Full [GFM 0.29](https://github.github.com/gfm/) support (strict superset — every valid GFM document renders identically)
- **Wiki links**: `[[Page]]`, `[[Page|display text]]`, namespaces, interwiki prefixes
- **YAML frontmatter**: Page metadata, categories, TOC control, template inputs
- **Page variables**: `${title}`, `${star.name}`, `${moons.0}` — dot notation into frontmatter
- **Templates**: `{{name args}}` — transclusion and module-backed templates with `${...}` variable substitution
- **Semantic annotations**: `[text]|property|` — structured, machine-readable metadata on inline elements
- **Presentation attributes**: `![alt](url){.thumb width=300}` — Pandoc-style attributes on images, links, and spans
- **Callouts**: `> [!NOTE]` — GitHub/Obsidian-style admonitions
- **Page embeds**: `![[page]]` — transclude another page's rendered content
- **Redirects**: Frontmatter `redirect:` or `#REDIRECT [[Page]]`

## Installation

```bash
pip install wikimark
```

For development:

```bash
git clone https://github.com/trellis-wiki/wikimark-python.git
cd wikimark-python
pip install -e ".[dev]"
```

## Quick start

### Python API

```python
import wikimark

# One-liner: WikiMark string → HTML string
html = wikimark.convert("See [[Main Page]] for details.")
# '<p>See <a href="Main_Page">Main Page</a> for details.</p>\n'

# With frontmatter context
html = wikimark.convert("""---
title: Earth
radius_km: 6371
---

# ${title}

${title} has a radius of ${radius_km} km.
""")
# '<h1>Earth</h1>\n<p>Earth has a radius of 6371 km.</p>\n'
```

### Parser and renderer

For more control, use the parser and renderer directly:

```python
from wikimark import Parser, HtmlRenderer

parser = Parser()
renderer = HtmlRenderer()

# Parse to AST
doc = parser.parse("[[Main Page]] and **bold**")

# Render AST to HTML
html = renderer.render(doc)

# Inspect the AST
print(doc.pretty())
```

### Configuration

```python
from wikimark import Parser, HtmlRenderer, Config

config = Config(
    # Wiki link URL generation
    base_url="/wiki/",
    
    # Template resolution
    template_dir="templates/",
    
    # Interwiki prefixes
    interwiki={
        "wikipedia": "https://en.wikipedia.org/wiki/{page}",
    },
    
    # Security limits
    max_expansion_depth=40,
    max_expansions=500,
)

parser = Parser(config)
renderer = HtmlRenderer(config)
html = renderer.render(parser.parse(source))
```

### Working with frontmatter

```python
from wikimark import Parser

parser = Parser()
doc = parser.parse("""---
title: Earth
categories:
  - Planets
  - Solar System
---

Content here.
""")

# Access parsed frontmatter
print(doc.frontmatter["title"])        # "Earth"
print(doc.frontmatter["categories"])   # ["Planets", "Solar System"]
```

## Command-line usage

`wikimark` installs a CLI tool for converting WikiMark files:

```bash
# Convert a file to HTML
wikimark README.wm

# Read from stdin
echo '[[Main Page]]' | wikimark

# Output to file
wikimark input.wm -o output.html

# Dump the AST as JSON
wikimark input.wm --ast

# Specify config
wikimark input.wm --base-url /wiki/ --template-dir templates/
```

Full usage:

```
usage: wikimark [-h] [-o OUTPUT] [--ast] [--base-url URL]
                [--template-dir DIR] [--version]
                [FILE]

Convert WikiMark to HTML.

positional arguments:
  FILE                  Input file (default: stdin)

options:
  -h, --help            show this help message and exit
  -o, --output OUTPUT   Output file (default: stdout)
  --ast                 Dump AST as JSON instead of rendering HTML
  --base-url URL        Base URL for wiki links (default: none)
  --template-dir DIR    Template directory (default: _templates/)
  --version             show version and exit
```

## Testing

The test suite includes **1,546 input/output test cases** from the [WikiMark specification](https://github.com/trellis-wiki/wikimark):

| Suite | Tests | Description |
| --- | --- | --- |
| CommonMark 0.31.2 | 652 | Baseline Markdown compliance |
| GFM 0.29 | 672 | Full GFM spec (superset of CommonMark) |
| GFM extensions | 30 | Tables, strikethrough, autolinks, task lists |
| WikiMark spec | 92 | Normative examples from the spec |
| WikiMark extra | 100 | Edge cases and regression tests |

```bash
# Run all tests
pytest

# Run only WikiMark-specific tests
pytest -k wikimark

# Run with coverage
pytest --cov=wikimark --cov-report=term-missing

# Run the spec test runner directly (for CI or cross-implementation testing)
python -m wikimark.test_runner
```

## Project structure

```
wikimark-python/
├── src/
│   └── wikimark/
│       ├── __init__.py          # Public API: convert(), Parser, HtmlRenderer, Config
│       ├── parser.py            # Four-phase WikiMark parser
│       ├── inline_parser.py     # Inline parsing (wiki links, variables, templates, etc.)
│       ├── block_parser.py      # Block structure (inherits GFM + callouts, redirects)
│       ├── renderer.py          # HTML renderer
│       ├── ast.py               # AST node types
│       ├── frontmatter.py       # YAML frontmatter extraction and variable resolution
│       ├── templates.py         # Template resolution and expansion
│       ├── normalize.py         # Page title normalization (section 13)
│       ├── config.py            # Configuration dataclass
│       └── cli.py               # Command-line interface
├── tests/
│   ├── conftest.py              # Pytest fixtures and test suite loading
│   ├── test_commonmark.py       # CommonMark 0.31.2 compliance
│   ├── test_gfm.py             # GFM compliance
│   ├── test_wikimark.py        # WikiMark spec + extra tests
│   └── upstream/               # Symlink or copy of wikimark spec test suites
├── pyproject.toml
├── LICENSE
└── README.md
```

## Specification compliance

This implementation targets [WikiMark v0.4](https://github.com/trellis-wiki/wikimark/blob/main/spec.md) (draft). WikiMark is a strict superset of GFM, which is a strict superset of CommonMark:

```
CommonMark 0.31.2  ⊂  GFM 0.29  ⊂  WikiMark 0.4
```

A conforming WikiMark processor must pass all CommonMark and GFM tests in addition to WikiMark-specific tests.

## Dependencies

- **[cmark-gfm](https://github.com/theacodes/cmark-gfm)** or equivalent — GFM block and inline parsing (used as the foundation layer)
- **[PyYAML](https://pyyaml.org/)** — Frontmatter parsing
- **Standard library only** for everything else

## Contributing

Contributions are welcome. Please ensure:

1. All existing tests pass (`pytest`)
2. New features include tests (add to `tests/` following the spec.json format)
3. Code is formatted with [Ruff](https://docs.astral.sh/ruff/)
4. Type annotations are included for public APIs

## License

[MIT](LICENSE)

## Acknowledgments

- [WikiMark specification](https://github.com/trellis-wiki/wikimark) — the language this implements
- [CommonMark](https://commonmark.org/) — the foundation specification by John MacFarlane
- [GitHub Flavored Markdown](https://github.github.com/gfm/) — the GFM superset WikiMark extends
- [commonmark.py](https://github.com/commonmark/commonmark.py) — architectural inspiration
- [markdown-it-py](https://github.com/executablebooks/markdown-it-py) — API design inspiration
