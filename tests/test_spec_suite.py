"""
Run the full WikiMark spec test suite against the Python binding.

We expect the same 85 baseline exclusions as libwikimark (documented
cmark-gfm baseline divergences plus intentional WikiMark deviations
for relative links and standalone images). Any failure outside the
exclusion set is a regression.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import wikimark

from ._engine import FixtureEngine

TESTS_DIR = Path(__file__).parent.parent.parent / "wikimark" / "tests"
EXCLUSIONS_FILE = TESTS_DIR / "cmark-gfm-baseline-exclusions.json"

# Fixture template / page directories — same as the libwikimark CLI uses.
FIXTURE_ROOT = Path(__file__).parent.parent.parent / "libwikimark" / "test_data"
TEMPLATE_DIR = FIXTURE_ROOT / "templates"
PAGES_DIR = FIXTURE_ROOT / "pages"


def _load_exclusions() -> dict[str, set[int]]:
    if not EXCLUSIONS_FILE.exists():
        return {}
    with open(EXCLUSIONS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return {
        suite: set(examples)
        for suite, examples in data.items()
        if suite not in ("description",)
    }


def _load_suite(relpath: str) -> list[dict]:
    path = TESTS_DIR / relpath
    if not path.exists():
        pytest.skip(f"spec test suite missing: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


_EXCLUSIONS = _load_exclusions()


def _normalize(html: str) -> str:
    """Normalize whitespace for comparison — matches run_tests.py in wikimark/."""
    s = re.sub(r"\s+", " ", html.strip())
    s = re.sub(r"\s*/>", " />", s)
    return s


def _ids_for(suite: list[dict]) -> list[str]:
    return [f"ex{t['example']}" for t in suite]


def _make_test(suite_name: str, relpath: str):
    suite = _load_suite(relpath)
    excluded = _EXCLUSIONS.get(suite_name, set())

    @pytest.mark.parametrize("test", suite, ids=_ids_for(suite))
    def _run(test: dict) -> None:
        if test["example"] in excluded:
            pytest.xfail(
                f"excluded as baseline divergence "
                f"(example {test['example']} in {suite_name})"
            )
        # Fresh engine per test — avoids state leaking across cases.
        engine = FixtureEngine(TEMPLATE_DIR, PAGES_DIR)
        actual = engine.render(test["markdown"])
        assert _normalize(actual) == _normalize(test["html"]), (
            f"spec mismatch at example {test['example']} "
            f"({test.get('section', '?')})\n"
            f"input:\n{test['markdown']!r}\n"
            f"expected:\n{test['html']!r}\n"
            f"actual:\n{actual!r}"
        )

    _run.__name__ = f"test_{suite_name.replace('-', '_')}"
    return _run


# Generate one parametrized test function per suite. Keeping them
# separate lets pytest report per-suite failure counts cleanly.

test_commonmark = _make_test("commonmark", "upstream/commonmark-spec.json")
test_gfm_spec = _make_test("gfm-spec", "upstream/gfm-spec.json")
test_gfm_extensions = _make_test("gfm-extensions", "upstream/gfm-extensions.json")
test_wikimark_spec = _make_test("wikimark-spec", "wikimark-spec.json")
test_wikimark_extra = _make_test("wikimark-extra", "wikimark-extra.json")
