"""
wikimark — Python bindings to libwikimark.

Basic usage::

    import wikimark
    html = wikimark.render("See [[Main Page]] for details.")

With engine callbacks for variable, template, and embed resolution::

    def resolve_variable(path: str) -> str | None:
        return {"title": "Earth"}.get(path)

    html = wikimark.render(
        "# ${title}",
        resolve_variable=resolve_variable,
    )

The parser is libwikimark (C). This package is a thin CFFI wrapper —
it does no parsing itself. Content resolution (templates, variables,
page embeds) is handled by Python callables you pass in; the library
invokes them via C function pointers.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeAlias

from ._wikimark import ffi, lib  # type: ignore[import-not-found]

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "OPT_DEFAULT",
    "OPT_SOURCEPOS",
    "OPT_HARDBREAKS",
    "OPT_NOBREAKS",
    "OPT_SMART",
    "OPT_UNSAFE",
    "render",
    "Interwiki",
]

# ---------- cmark-gfm option constants (re-exported for convenience) ----------

OPT_DEFAULT: int = lib.CMARK_OPT_DEFAULT
OPT_SOURCEPOS: int = lib.CMARK_OPT_SOURCEPOS
OPT_HARDBREAKS: int = lib.CMARK_OPT_HARDBREAKS
OPT_NOBREAKS: int = lib.CMARK_OPT_NOBREAKS
OPT_SMART: int = lib.CMARK_OPT_SMART
OPT_UNSAFE: int = lib.CMARK_OPT_UNSAFE


# ---------- Public types ----------

ResolveVariable: TypeAlias = Callable[[str], str | None]
ResolveTemplate: TypeAlias = Callable[[str, str | None], str | None]
ResolveEmbed: TypeAlias = Callable[[str], str | None]


class Interwiki:
    """An interwiki prefix mapping.

    ``prefix`` is the namespace prefix (e.g. ``"wikipedia"``);
    ``url_format`` is a URL template containing the literal ``{page}``
    placeholder (e.g. ``"https://en.wikipedia.org/wiki/{page}"``).
    """

    __slots__ = ("prefix", "url_format")

    def __init__(self, prefix: str, url_format: str) -> None:
        self.prefix = prefix
        self.url_format = url_format


# ---------- Internal: callback trampolines ----------
#
# libwikimark calls our registered C function pointers with a
# void* user_data. We stash a handle to a `_RenderArena` object
# there. The trampolines resolve the handle, call the Python
# callable, and arena-own the returned string so the pointer we
# hand back to C stays valid until the render completes.


class _RenderArena:
    """Per-render-call scratch space.

    Holds strong references to every CFFI-owned bytes buffer we hand
    to libwikimark, so they aren't GC'd mid-call. Also holds the
    user's three resolver callables and the active interwiki
    table (so it outlives the C struct we point to it from).
    """

    __slots__ = (
        "resolve_variable",
        "resolve_template",
        "resolve_embed",
        "kept",
        "interwiki_keepalives",
    )

    def __init__(
        self,
        resolve_variable: ResolveVariable | None,
        resolve_template: ResolveTemplate | None,
        resolve_embed: ResolveEmbed | None,
    ) -> None:
        self.resolve_variable = resolve_variable
        self.resolve_template = resolve_template
        self.resolve_embed = resolve_embed
        self.kept: list[object] = []
        self.interwiki_keepalives: list[object] = []

    def keep(self, obj: object) -> object:
        """Retain a reference to ``obj`` for the lifetime of the arena."""
        self.kept.append(obj)
        return obj


def _arena_from_userdata(user_data):  # type: ignore[no-untyped-def]
    return ffi.from_handle(user_data)


def _arena_new_cstring(arena: _RenderArena, value: str):  # type: ignore[no-untyped-def]
    """Allocate an arena-owned NUL-terminated C string and return its pointer.

    libwikimark's contract (from wikimark.h): "All returned strings are
    owned by the engine and must remain valid until wikimark_render()
    returns." The arena keeps the bytes alive; we return the raw pointer.
    """
    buf = ffi.new("char[]", value.encode("utf-8"))
    arena.keep(buf)
    return buf


@ffi.def_extern()  # type: ignore[misc]
def _wm_py_resolve_variable(path, user_data):  # type: ignore[no-untyped-def]
    arena = _arena_from_userdata(user_data)
    if arena.resolve_variable is None:
        return ffi.NULL
    try:
        py_path = ffi.string(path).decode("utf-8")
        result = arena.resolve_variable(py_path)
    except Exception:
        # Swallow exceptions at the C boundary — a raised Python
        # exception here would be unrecoverable (C has no concept
        # of Python exceptions). Return NULL so libwikimark treats
        # the variable as unresolved.
        return ffi.NULL
    if result is None:
        return ffi.NULL
    return _arena_new_cstring(arena, result)


@ffi.def_extern()  # type: ignore[misc]
def _wm_py_resolve_template(name, args, user_data):  # type: ignore[no-untyped-def]
    arena = _arena_from_userdata(user_data)
    if arena.resolve_template is None:
        return ffi.NULL
    try:
        py_name = ffi.string(name).decode("utf-8")
        py_args = ffi.string(args).decode("utf-8") if args != ffi.NULL else None
        result = arena.resolve_template(py_name, py_args)
    except Exception:
        return ffi.NULL
    if result is None:
        return ffi.NULL
    return _arena_new_cstring(arena, result)


@ffi.def_extern()  # type: ignore[misc]
def _wm_py_resolve_embed(target, user_data):  # type: ignore[no-untyped-def]
    arena = _arena_from_userdata(user_data)
    if arena.resolve_embed is None:
        return ffi.NULL
    try:
        py_target = ffi.string(target).decode("utf-8")
        result = arena.resolve_embed(py_target)
    except Exception:
        return ffi.NULL
    if result is None:
        return ffi.NULL
    return _arena_new_cstring(arena, result)


# ---------- Public render function ----------


def render(
    source: str,
    *,
    options: int = OPT_DEFAULT,
    base_url: str = "",
    interwiki: Sequence[Interwiki] | None = None,
    resolve_variable: ResolveVariable | None = None,
    resolve_template: ResolveTemplate | None = None,
    resolve_embed: ResolveEmbed | None = None,
) -> str:
    """Render a WikiMark source string to HTML.

    Args:
        source: WikiMark source text.
        options: Bitmask of ``OPT_*`` flags. Defaults to ``OPT_DEFAULT``.
        base_url: URL prefix for wiki links (e.g. ``"/wiki/"``).
        interwiki: Optional list of :class:`Interwiki` prefix mappings.
        resolve_variable: Callable ``(path: str) -> str | None``. Called
            when the renderer encounters ``${path}``. Return ``None`` to
            leave the variable unresolved.
        resolve_template: Callable ``(name: str, args: str | None) ->
            str | None``. Called when the renderer encounters
            ``{{name args}}``. The callable is expected to return
            rendered HTML (not WikiMark — libwikimark does not
            recursively reparse). Return ``None`` to emit an error
            indicator.
        resolve_embed: Callable ``(target: str) -> str | None``. Called
            when the renderer encounters ``![[target]]``. Return
            rendered HTML, or ``None`` for an error indicator.

    Returns:
        The rendered HTML.

    Raises:
        UnicodeError: if ``source`` cannot be encoded as UTF-8.
        MemoryError: if libwikimark returns NULL (allocation failure).
    """
    # Ensure the C library's extension registration has happened.
    # Safe to call multiple times (pthread_once under the hood).
    lib.wikimark_extensions_ensure_registered()

    encoded = source.encode("utf-8")

    arena = _RenderArena(resolve_variable, resolve_template, resolve_embed)

    # Build config struct
    config = ffi.new("wikimark_config *")
    base_url_buf = arena.keep(ffi.new("char[]", base_url.encode("utf-8")))
    config.base_url = base_url_buf

    if interwiki:
        iw_buf = ffi.new("wikimark_interwiki[]", len(interwiki))
        for i, entry in enumerate(interwiki):
            prefix_c = arena.keep(ffi.new("char[]", entry.prefix.encode("utf-8")))
            url_c = arena.keep(ffi.new("char[]", entry.url_format.encode("utf-8")))
            iw_buf[i].prefix = prefix_c
            iw_buf[i].url_format = url_c
        arena.interwiki_keepalives.append(iw_buf)
        config.interwiki = iw_buf
        config.interwiki_count = len(interwiki)
    else:
        config.interwiki = ffi.NULL
        config.interwiki_count = 0

    # Build engine context struct. We route every call through our
    # three @def_extern trampolines; they dispatch to the Python
    # callables via the arena pulled from user_data.
    context = ffi.new("wikimark_context *")
    handle = ffi.new_handle(arena)
    # Retain the handle for the duration of the call so the Python
    # side of the handle→object mapping doesn't GC.
    arena.keep(handle)

    context.resolve_variable = lib._wm_py_resolve_variable
    context.resolve_template = lib._wm_py_resolve_template
    context.resolve_embed = lib._wm_py_resolve_embed
    context.user_data = handle

    html_ptr = lib.wikimark_render(encoded, len(encoded), options, config, context)
    if html_ptr == ffi.NULL:
        raise MemoryError("wikimark_render returned NULL")

    try:
        return ffi.string(html_ptr).decode("utf-8")
    finally:
        lib.wikimark_free(html_ptr)
