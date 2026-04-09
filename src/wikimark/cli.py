"""WikiMark command-line interface."""

from __future__ import annotations

import argparse
import sys

from . import __version__


def main(argv: list[str] | None = None) -> None:
    """Entry point for the ``wikimark`` CLI command."""
    parser = argparse.ArgumentParser(
        prog="wikimark",
        description="Convert WikiMark to HTML.",
    )
    parser.add_argument(
        "file",
        nargs="?",
        metavar="FILE",
        help="Input file (default: stdin)",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="OUTPUT",
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "--ast",
        action="store_true",
        help="Dump AST as JSON instead of rendering HTML",
    )
    parser.add_argument(
        "--base-url",
        metavar="URL",
        default="",
        help="Base URL for wiki links (default: none)",
    )
    parser.add_argument(
        "--template-dir",
        metavar="DIR",
        default="_templates/",
        help="Template directory (default: _templates/)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args(argv)

    # Read input
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            source = f.read()
    else:
        source = sys.stdin.read()

    # Convert
    from .config import Config

    config = Config(
        base_url=args.base_url,
        template_dir=args.template_dir,
    )

    from .parser import Parser
    from .renderer import HtmlRenderer

    doc_parser = Parser(config)
    renderer = HtmlRenderer(config)

    doc = doc_parser.parse(source)

    if args.ast:
        import json

        # TODO: Implement AST JSON serialization
        json.dump({"error": "AST serialization not yet implemented"}, sys.stdout, indent=2)
        print()
    else:
        output = renderer.render(doc)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
        else:
            sys.stdout.write(output)


if __name__ == "__main__":
    main()
