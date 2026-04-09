"""WikiMark HTML renderer."""

from __future__ import annotations

from .config import Config


class HtmlRenderer:
    """Render a WikiMark AST to HTML."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()

    def render(self, document: object) -> str:
        """Render an AST document node to an HTML string."""
        raise NotImplementedError("HtmlRenderer not yet implemented")
