"""
Minimal setup.py shim. Everything metadata-related lives in
pyproject.toml; this file exists only to hook in the CFFI
out-of-line build.
"""

from setuptools import setup

setup(
    cffi_modules=["src/wikimark/_build.py:ffibuilder"],
)
