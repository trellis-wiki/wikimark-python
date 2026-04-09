"""Pytest configuration and fixtures for WikiMark tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Path to the wikimark spec test suites
SPEC_TESTS_DIR = Path(__file__).parent.parent.parent / "wikimark" / "tests"


def load_test_suite(filename: str) -> list[dict]:
    """Load a test suite JSON file from the spec tests directory."""
    path = SPEC_TESTS_DIR / filename
    if not path.exists():
        pytest.skip(f"Test suite not found: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def commonmark_tests() -> list[dict]:
    """CommonMark 0.31.2 specification tests."""
    return load_test_suite("upstream/commonmark-spec.json")


@pytest.fixture(scope="session")
def gfm_tests() -> list[dict]:
    """GFM 0.29 specification tests."""
    return load_test_suite("upstream/gfm-spec.json")


@pytest.fixture(scope="session")
def gfm_extension_tests() -> list[dict]:
    """GFM extension tests (tables, strikethrough, autolinks, task lists)."""
    return load_test_suite("upstream/gfm-extensions.json")


@pytest.fixture(scope="session")
def wikimark_spec_tests() -> list[dict]:
    """WikiMark specification examples."""
    return load_test_suite("wikimark-spec.json")


@pytest.fixture(scope="session")
def wikimark_extra_tests() -> list[dict]:
    """WikiMark additional edge case tests."""
    return load_test_suite("wikimark-extra.json")
