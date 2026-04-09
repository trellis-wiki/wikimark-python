"""WikiMark — a Python implementation of the WikiMark markup language.

WikiMark is a strict superset of GitHub Flavored Markdown with wiki links,
templates, semantic annotations, and structured page metadata.

Basic usage::

    import wikimark

    html = wikimark.convert("See [[Main Page]] for details.")

For more control::

    from wikimark import Parser, HtmlRenderer, Config

    parser = Parser()
    renderer = HtmlRenderer()
    doc = parser.parse(source)
    html = renderer.render(doc)
"""

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "convert",
    "Config",
    "HtmlRenderer",
    "Parser",
]


def convert(source: str, **kwargs: object) -> str:
    """Convert a WikiMark string to HTML.

    This is the simplest entry point. For more control, use Parser and
    HtmlRenderer directly.

    Args:
        source: WikiMark source text.
        **kwargs: Passed to Config().

    Returns:
        Rendered HTML string.
    """
    # Lazy imports to avoid circular dependencies during package init
    from .config import Config
    from .parser import Parser
    from .renderer import HtmlRenderer

    config = Config(**kwargs)  # type: ignore[arg-type]
    parser = Parser(config)
    renderer = HtmlRenderer(config)
    doc = parser.parse(source)
    return renderer.render(doc)


def __getattr__(name: str) -> object:
    """Lazy import public classes to keep top-level import fast."""
    if name == "Config":
        from .config import Config

        return Config
    if name == "Parser":
        from .parser import Parser

        return Parser
    if name == "HtmlRenderer":
        from .renderer import HtmlRenderer

        return HtmlRenderer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
