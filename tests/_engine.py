"""
Minimal filesystem-backed engine for spec-test validation.

Mirrors libwikimark's `tools/test_engine.c` — reads templates and
pages from disk, provides the three resolver callbacks, and handles
variable substitution in template bodies using merged caller args +
frontmatter defaults.

This is test-fixture code, not production. The Trellis T-0 prototype
will grow from something like this.
"""

from __future__ import annotations

import re
from pathlib import Path

import wikimark

_VAR_RE = re.compile(r"\$\{([^}]+)\}")

# Matches the libwikimark CLI's built-in interwiki mapping so spec
# tests tagged against the CLI's output render equivalently.
_DEFAULT_INTERWIKI = [
    wikimark.Interwiki("wikipedia", "https://en.wikipedia.org/wiki/{page}"),
]


def _parse_frontmatter(source: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body). Frontmatter is a simple
    two-level YAML-ish mapping; sufficient for fixture templates."""
    if not source.startswith("---\n"):
        return {}, source
    end = source.find("\n---\n", 4)
    if end == -1:
        return {}, source
    raw = source[4:end]
    body = source[end + 5 :]

    fm: dict = {}
    current_key = None
    current_sub = None
    for line in raw.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 0 and ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if not val:
                fm[key] = {}
                current_key = key
                current_sub = None
            else:
                fm[key] = _strip_quotes(val)
                current_key = None
        elif indent == 2 and current_key is not None and stripped.endswith(":"):
            sub = stripped[:-1].strip()
            fm[current_key][sub] = {}
            current_sub = sub
        elif indent >= 4 and current_key and current_sub:
            if ":" in stripped:
                k, _, v = stripped.partition(":")
                fm[current_key][current_sub][k.strip()] = _strip_quotes(v.strip())
    return fm, body


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def _parse_template_args(args: str | None) -> dict[str, str]:
    """Turn a template arg string into a dict.

    Supports: positional ("value"), named (key=value, key="value"),
    matching the test_engine.c behavior for the spec-fixture cases.
    Positional args get keys "1", "2", ...
    """
    out: dict[str, str] = {}
    if not args:
        return out

    i = 0
    pos = 1
    s = args
    while i < len(s):
        while i < len(s) and s[i] == " ":
            i += 1
        if i >= len(s):
            break

        # Detect key=... vs positional
        eq = -1
        j = i
        if s[j] != '"':
            while j < len(s) and s[j] not in "= ":
                j += 1
            if j < len(s) and s[j] == "=":
                eq = j

        if eq != -1:
            key = s[i:eq]
            i = eq + 1
        else:
            key = str(pos)
            pos += 1

        if i < len(s) and s[i] == '"':
            i += 1
            val_chars: list[str] = []
            while i < len(s) and s[i] != '"':
                if s[i] == "\\" and i + 1 < len(s):
                    i += 1
                val_chars.append(s[i])
                i += 1
            if i < len(s) and s[i] == '"':
                i += 1
            val = "".join(val_chars)
        else:
            j = i
            while j < len(s) and s[j] != " ":
                j += 1
            val = s[i:j]
            i = j

        out[key] = val
    return out


def _substitute_vars(text: str, values: dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        key = m.group(1)
        return values.get(key, m.group(0))

    return _VAR_RE.sub(repl, text)


def _map_positional_to_inputs(args: dict[str, str], inputs: dict) -> dict[str, str]:
    """Rewrite positional keys ("1", "2", ...) to the named inputs
    declared by the template's frontmatter."""
    if not inputs:
        return args
    out = dict(args)
    for i, name in enumerate(inputs.keys(), start=1):
        pos = str(i)
        if pos in out and name not in out:
            out[name] = out.pop(pos)
    return out


def _apply_defaults(args: dict[str, str], inputs: dict) -> dict[str, str]:
    out = dict(args)
    for name, meta in inputs.items():
        if name not in out and isinstance(meta, dict):
            default = meta.get("default")
            if default is not None:
                out[name] = default
    return out


class FixtureEngine:
    """Filesystem-backed resolver engine for the WikiMark spec tests.

    Parameters:
        template_dir: Directory containing `<name>.wm` template files.
        pages_dir: Directory containing page `.wm` files for embeds.
    """

    MAX_DEPTH = 40

    def __init__(self, template_dir: Path, pages_dir: Path) -> None:
        self.template_dir = Path(template_dir)
        self.pages_dir = Path(pages_dir)
        self._depth = 0
        self._page_fm: dict = {}

    def set_page_frontmatter(self, fm: dict) -> None:
        self._page_fm = fm

    def context_kwargs(self) -> dict:
        return {
            "resolve_variable": self._resolve_variable,
            "resolve_template": self._resolve_template,
            "resolve_embed": self._resolve_embed,
        }

    # --- Variable resolution ---
    def _resolve_variable(self, path: str) -> str | None:
        # Dot-notation: star.name → page_fm["star"]["name"]
        cur: object = self._page_fm
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return None
        return cur if isinstance(cur, str) else None

    # --- Template resolution ---
    def _resolve_template(self, name: str, args: str | None) -> str | None:
        if self._depth > self.MAX_DEPTH:
            return None
        path = self.template_dir / f"{name}.wm"
        if not path.exists():
            return None

        source = path.read_text(encoding="utf-8")
        fm, body = _parse_frontmatter(source)
        inputs = fm.get("inputs", {}) if isinstance(fm.get("inputs"), dict) else {}

        call_args = _parse_template_args(args)
        call_args = _map_positional_to_inputs(call_args, inputs)
        call_args = _apply_defaults(call_args, inputs)

        # Check required inputs
        for input_name, meta in inputs.items():
            if isinstance(meta, dict) and meta.get("required") == "true":
                if input_name not in call_args:
                    return (
                        f'<span class="wm-error">{{{{{name}}}}}: '
                        f'missing required input "{input_name}"</span>'
                    )

        # Pre-substitute variables in the template body, matching
        # test_engine.c's behavior (args live in a scope libwikimark
        # doesn't see natively).
        resolved_body = _substitute_vars(body, call_args)

        self._depth += 1
        try:
            # Swap out page frontmatter during template render so
            # ${...} inside the template body — if any survived
            # pre-substitution — resolves against caller args.
            prev_fm = self._page_fm
            self._page_fm = {**prev_fm, **call_args}
            html = wikimark.render(
                resolved_body,
                options=wikimark.OPT_UNSAFE,
                interwiki=_DEFAULT_INTERWIKI,
                **self.context_kwargs(),
            )
            self._page_fm = prev_fm
        finally:
            self._depth -= 1

        return html.rstrip("\n\r")

    # --- Embed resolution ---
    def _resolve_embed(self, target: str) -> str | None:
        if self._depth > self.MAX_DEPTH:
            return None

        # Support "Page#Section" form for section embeds.
        page_name, _, section = target.partition("#")
        page_file = page_name.replace(" ", "_")
        path = self.pages_dir / f"{page_file}.wm"
        if not path.exists():
            return None

        source = path.read_text(encoding="utf-8")

        self._depth += 1
        try:
            html = wikimark.render(
                source,
                options=wikimark.OPT_UNSAFE,
                **self.context_kwargs(),
            )
        finally:
            self._depth -= 1

        if section:
            html = _extract_section(html, section)
        return html

    # Utility: render a top-level page through this engine.
    def render(self, source: str) -> str:
        fm, _body = _parse_frontmatter(source)
        prev = self._page_fm
        self._page_fm = fm
        try:
            return wikimark.render(
                source,
                options=wikimark.OPT_UNSAFE,
                interwiki=_DEFAULT_INTERWIKI,
                **self.context_kwargs(),
            )
        finally:
            self._page_fm = prev


def _extract_section(html: str, section: str) -> str:
    """Extract the content under a specific `<hN>Section</hN>` heading.

    Mirrors test_engine.c's naive substring approach — good enough for
    spec fixtures.
    """
    needle = f">{section}</h"
    start = html.find(needle)
    if start == -1:
        return html
    after_heading = html.find(">", html.find("</h", start)) + 1
    if after_heading <= 0:
        return html
    if after_heading < len(html) and html[after_heading] == "\n":
        after_heading += 1
    next_h = html.find("<h", after_heading)
    end = next_h if next_h != -1 else len(html)
    while end > after_heading and html[end - 1] in "\n ":
        end -= 1
    chunk = html[after_heading:end]
    # Strip <p>…</p> wrapper when the whole section is one paragraph
    if chunk.startswith("<p>") and chunk.endswith("</p>"):
        chunk = chunk[3:-4]
    return chunk
