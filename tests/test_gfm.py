"""GFM 0.29 compliance tests."""

from __future__ import annotations

import pytest

from wikimark import convert


def test_gfm_spec_compliance(gfm_tests: list[dict]) -> None:
    """Every GFM spec test must produce identical output."""
    failures = []
    for test in gfm_tests:
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
        pytest.fail(f"{len(failures)} GFM tests failed:\n\n" + "\n\n".join(failures[:10]))


def test_gfm_extension_compliance(gfm_extension_tests: list[dict]) -> None:
    """Every GFM extension test must produce identical output."""
    failures = []
    for test in gfm_extension_tests:
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
            f"{len(failures)} GFM extension tests failed:\n\n" + "\n\n".join(failures[:10])
        )
