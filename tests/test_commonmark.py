"""CommonMark 0.31.2 compliance tests."""

from __future__ import annotations

import pytest

from wikimark import convert


def test_commonmark_compliance(commonmark_tests: list[dict]) -> None:
    """Every CommonMark test must produce identical output."""
    failures = []
    for test in commonmark_tests:
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
        pytest.fail(f"{len(failures)} CommonMark tests failed:\n\n" + "\n\n".join(failures[:10]))
