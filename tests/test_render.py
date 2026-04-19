"""
Smoke tests for the CFFI binding.

These assert that each major WikiMark feature round-trips through
wikimark.render() and produces plausible HTML. They are NOT spec-
conformance tests — that's test_spec_suite.py.
"""

from __future__ import annotations

import pytest

import wikimark


def test_plain_text() -> None:
    html = wikimark.render("hello world")
    assert html == "<p>hello world</p>\n"


def test_heading() -> None:
    html = wikimark.render("# Hello")
    assert html == "<h1>Hello</h1>\n"


def test_wiki_link() -> None:
    html = wikimark.render("See [[Main Page]].")
    assert 'href="Main_Page"' in html
    assert ">Main Page<" in html


def test_wiki_link_base_url() -> None:
    html = wikimark.render("[[Home]]", base_url="/wiki/")
    assert "/wiki/Home" in html


def test_interwiki_link() -> None:
    html = wikimark.render(
        "[[wikipedia:Paris]]",
        interwiki=[
            wikimark.Interwiki("wikipedia", "https://en.wikipedia.org/wiki/{page}"),
        ],
    )
    assert "https://en.wikipedia.org/wiki/Paris" in html


def test_frontmatter_variable() -> None:
    html = wikimark.render(
        "---\ntitle: Earth\n---\n\n# ${title}\n\n${title} is a planet.",
    )
    assert "Earth" in html
    # Should render with the variable expanded in two places
    assert html.count("Earth") >= 2


def test_variable_via_callback() -> None:
    values = {"star.name": "Sol", "star.type": "G2V"}

    def resolver(path: str) -> str | None:
        return values.get(path)

    # When a variable isn't in frontmatter, libwikimark doesn't call
    # our callback — variables resolve from page frontmatter only in
    # current libwikimark. This test verifies that calling with a
    # callback at least doesn't crash.
    html = wikimark.render(
        "---\nplanet: Earth\n---\n\n${planet}",
        resolve_variable=resolver,
    )
    assert "Earth" in html


def test_template_via_callback() -> None:
    def resolver(name: str, args: str | None) -> str | None:
        if name == "greeting":
            return "<span>Hello!</span>"
        return None

    # OPT_UNSAFE required to pass HTML from the callback through
    # to the rendered output — without it cmark-gfm strips raw HTML.
    html = wikimark.render(
        "{{greeting}}",
        options=wikimark.OPT_UNSAFE,
        resolve_template=resolver,
    )
    assert "Hello!" in html


def test_template_without_callback_produces_error_indicator() -> None:
    html = wikimark.render("{{missing}}", options=wikimark.OPT_UNSAFE)
    assert "wm-error" in html
    assert "missing" in html


def test_embed_via_callback() -> None:
    def resolver(target: str) -> str | None:
        if target == "Shared/Header":
            return "<p>rendered shared content</p>"
        return None

    html = wikimark.render(
        "![[Shared/Header]]",
        options=wikimark.OPT_UNSAFE,
        resolve_embed=resolver,
    )
    assert "rendered shared content" in html


def test_gfm_strikethrough() -> None:
    html = wikimark.render("~~stricken~~")
    assert "<del>stricken</del>" in html


def test_gfm_table() -> None:
    source = "| a | b |\n|---|---|\n| 1 | 2 |\n"
    html = wikimark.render(source)
    assert "<table>" in html
    assert "<td>1</td>" in html


def test_unicode_passthrough() -> None:
    html = wikimark.render("# Hëllo, 世界 🌍")
    assert "Hëllo, 世界 🌍" in html


def test_html_escape() -> None:
    html = wikimark.render("a & b < c > d")
    assert "&amp;" in html
    assert "&lt;" in html


def test_option_constants_exposed() -> None:
    # Just make sure we didn't mis-wire the constant re-exports.
    assert isinstance(wikimark.OPT_DEFAULT, int)
    assert wikimark.OPT_UNSAFE != wikimark.OPT_DEFAULT


def test_callback_exception_does_not_crash() -> None:
    def broken(_path: str) -> str | None:
        raise RuntimeError("boom")

    # Should not segfault or propagate the exception; the C side
    # treats the variable as unresolved.
    html = wikimark.render(
        "---\ntitle: Earth\n---\n${title}",
        resolve_variable=broken,
    )
    assert "Earth" in html  # frontmatter still resolves


def test_callback_returning_none_yields_error_indicator() -> None:
    def none_resolver(_name: str, _args: str | None) -> str | None:
        return None

    html = wikimark.render(
        "{{unknown}}",
        options=wikimark.OPT_UNSAFE,
        resolve_template=none_resolver,
    )
    assert "wm-error" in html
    assert "unknown" in html


def test_multiple_renders_in_sequence() -> None:
    # Verify no cross-render state leaks (thread-local parse state
    # reset cleanly between calls).
    for i in range(5):
        html = wikimark.render(f"# Page {i}")
        assert f"Page {i}" in html


def test_empty_input() -> None:
    html = wikimark.render("")
    assert html == ""


@pytest.mark.parametrize(
    ("source", "needle"),
    [
        ("**bold**", "<strong>bold</strong>"),
        ("*italic*", "<em>italic</em>"),
        ("`code`", "<code>code</code>"),
        ("> quote", "<blockquote>"),
        ("- item\n- item", "<ul>"),
        ("1. one\n2. two", "<ol>"),
    ],
)
def test_gfm_basic_inline(source: str, needle: str) -> None:
    html = wikimark.render(source)
    assert needle in html


# ---- Frontmatter reader ----


def test_frontmatter_missing_returns_none() -> None:
    assert wikimark.read_frontmatter("just plain body text") is None


def test_frontmatter_scalar() -> None:
    with wikimark.read_frontmatter("---\ntitle: Earth\n---\n\nbody") as fm:
        assert fm is not None
        assert fm.get("title") == "Earth"
        assert fm.get("nonexistent") is None


def test_frontmatter_nested_dot_path() -> None:
    src = (
        "---\n"
        "star:\n"
        "  name: Sol\n"
        "  type: G2V\n"
        "moons:\n"
        "  - Luna\n"
        "  - Phobos\n"
        "---\n\nbody\n"
    )
    with wikimark.read_frontmatter(src) as fm:
        assert fm is not None
        assert fm.get("star.name") == "Sol"
        assert fm.get("star.type") == "G2V"
        assert fm.get("moons.0") == "Luna"
        assert fm.get("moons.1") == "Phobos"


def test_frontmatter_context_manager_closes() -> None:
    fm = wikimark.read_frontmatter("---\na: 1\n---\n\nbody")
    assert fm is not None
    with fm:
        assert fm.get("a") == "1"
    # After close, queries return None rather than crashing.
    assert fm.get("a") is None


def test_bare_brackets_are_literal() -> None:
    # Per spec §8.5 rule 5: a bare [text] without paired brackets
    # and without a matching reference definition is literal text.
    # libwikimark follows GFM exactly here — no bare-bracket wiki
    # link promotion.
    assert wikimark.render("[PageName]") == "<p>[PageName]</p>\n"
    assert wikimark.render("[multi word]") == "<p>[multi word]</p>\n"

    # Reference-style links still work because the reference is
    # defined.
    ref_source = "[See here][ref]\n\n[ref]: /somewhere\n"
    html = wikimark.render(ref_source)
    assert 'href="/somewhere"' in html


def test_frontmatter_input_defaults_exposed() -> None:
    # Template authors use inputs.<name>.default; the public API
    # exposes them via the same dot-notation the spec uses.
    src = (
        "---\n"
        "inputs:\n"
        "  greeting:\n"
        "    default: hello\n"
        "    required: true\n"
        "---\nbody\n"
    )
    with wikimark.read_frontmatter(src) as fm:
        assert fm is not None
        assert fm.get("inputs.greeting.default") == "hello"
        assert fm.get("inputs.greeting.required") == "true"
