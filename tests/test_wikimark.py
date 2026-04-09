"""WikiMark specification and edge case tests."""

from __future__ import annotations

import pytest

from wikimark import convert


def test_wikimark_spec(wikimark_spec_tests: list[dict]) -> None:
    """Every WikiMark spec example must produce the expected output."""
    failures = []
    for test in wikimark_spec_tests:
        try:
            actual = convert(test["markdown"])
        except NotImplementedError:
            pytest.skip("Parser not yet implemented")
        if actual != test["html"]:
            failures.append(
                f"Example {test['example']} [{test['section']}]:\n"
                f"  Input:    {test['markdown']!r}\n"
                f"  Expected: {test['html']!r}\n"
                f"  Actual:   {actual!r}"
            )
    if failures:
        pytest.fail(
            f"{len(failures)} WikiMark spec tests failed:\n\n" + "\n\n".join(failures[:10])
        )


def test_wikimark_extra(wikimark_extra_tests: list[dict]) -> None:
    """Every WikiMark edge case test must produce the expected output."""
    failures = []
    for test in wikimark_extra_tests:
        try:
            actual = convert(test["markdown"])
        except NotImplementedError:
            pytest.skip("Parser not yet implemented")
        if actual != test["html"]:
            desc = test.get("description", "")
            failures.append(
                f"Example {test['example']} [{test['section']}] {desc}:\n"
                f"  Input:    {test['markdown']!r}\n"
                f"  Expected: {test['html']!r}\n"
                f"  Actual:   {actual!r}"
            )
    if failures:
        pytest.fail(
            f"{len(failures)} WikiMark extra tests failed:\n\n" + "\n\n".join(failures[:10])
        )
