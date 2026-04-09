"""WikiMark parser — four-phase document processing."""

from __future__ import annotations

from .config import Config


class Parser:
    """Parse WikiMark source into an AST.

    Implements the four-phase processing model from the WikiMark specification:

    1. Frontmatter extraction
    2. Block structure (GFM + WikiMark block extensions)
    3. Inline structure (GFM + WikiMark inline extensions)
    4. Expansion (variables and templates)
    """

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()

    def parse(self, source: str) -> object:
        """Parse WikiMark source text into an AST."""
        raise NotImplementedError("Parser not yet implemented")
