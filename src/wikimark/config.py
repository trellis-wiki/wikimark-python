"""WikiMark configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    """Configuration for WikiMark parsing and rendering.

    Attributes:
        base_url: Base URL prepended to wiki link hrefs (e.g., "/wiki/").
        template_dir: Directory for file-based template resolution.
        interwiki: Mapping of interwiki prefix to URL template.
            Use ``{page}`` as the placeholder (e.g.,
            ``{"wikipedia": "https://en.wikipedia.org/wiki/{page}"}``).
        max_expansion_depth: Maximum recursion depth for template/embed expansion.
        max_expansions: Maximum total template expansions per page.
        max_output_size: Maximum expanded output size in bytes.
        case_sensitive: If True, disable first-letter capitalization in wiki link URLs.
    """

    base_url: str = ""
    template_dir: Path | str = "_templates/"
    interwiki: dict[str, str] = field(default_factory=dict)
    max_expansion_depth: int = 40
    max_expansions: int = 500
    max_output_size: int = 2 * 1024 * 1024  # 2 MB
    case_sensitive: bool = False
