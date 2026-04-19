"""
CFFI out-of-line build script.

Invoked by setup.py (via cffi_modules) during `pip install` or
`python setup.py build`. Produces a compiled extension module
named `wikimark._wikimark` that wraps libwikimark.

Location of the libwikimark sources and build output is resolved in
this order:
  1. Environment variables LIBWIKIMARK_DIR, LIBWIKIMARK_BUILD_DIR
  2. Default: ../libwikimark next to this repo, with build output
     at ../libwikimark/build
"""

from __future__ import annotations

import os
from pathlib import Path

from cffi import FFI

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

LIBWIKIMARK_DIR = Path(
    os.environ.get("LIBWIKIMARK_DIR", REPO_ROOT.parent / "libwikimark")
).resolve()
LIBWIKIMARK_BUILD_DIR = Path(
    os.environ.get("LIBWIKIMARK_BUILD_DIR", LIBWIKIMARK_DIR / "build")
).resolve()

CMARK_GFM_SRC = LIBWIKIMARK_DIR / "third_party" / "cmark-gfm" / "src"
CMARK_GFM_BUILD = LIBWIKIMARK_BUILD_DIR / "third_party" / "cmark-gfm" / "src"
CMARK_GFM_EXT_BUILD = LIBWIKIMARK_BUILD_DIR / "third_party" / "cmark-gfm" / "extensions"
LIBYAML_BUILD = LIBWIKIMARK_BUILD_DIR / "third_party" / "libyaml"

# Fail loudly during build if libwikimark isn't built — better than
# a cryptic linker error later.
_required_libs = [
    LIBWIKIMARK_BUILD_DIR / "libwikimark.a",
    CMARK_GFM_BUILD / "libcmark-gfm.a",
    CMARK_GFM_EXT_BUILD / "libcmark-gfm-extensions.a",
    LIBYAML_BUILD / "libyaml.a",
]
for _lib in _required_libs:
    if not _lib.exists():
        raise RuntimeError(
            f"libwikimark artifact not found: {_lib}\n"
            f"Build libwikimark first:\n"
            f"  cd {LIBWIKIMARK_DIR} && mkdir -p build && cd build "
            f"&& cmake .. && make\n"
            f"Or set LIBWIKIMARK_DIR / LIBWIKIMARK_BUILD_DIR env vars."
        )

ffibuilder = FFI()

# ------------------------------------------------------------------
# cdef: minimal subset of the public API Python callers need.
# We only declare what we call — cffi does not need the whole header.
# ------------------------------------------------------------------
ffibuilder.cdef(
    r"""
    /* Opaque — we never dereference from Python. */
    typedef struct cmark_node cmark_node;

    /* cmark-gfm rendering options we expose to callers. */
    #define CMARK_OPT_DEFAULT     ...
    #define CMARK_OPT_SOURCEPOS   ...
    #define CMARK_OPT_HARDBREAKS  ...
    #define CMARK_OPT_NOBREAKS    ...
    #define CMARK_OPT_SMART       ...
    #define CMARK_OPT_UNSAFE      ...

    /* --- Registration --- */
    void wikimark_extensions_ensure_registered(void);

    /* --- Configuration --- */
    typedef struct wikimark_interwiki {
        const char *prefix;
        const char *url_format;
    } wikimark_interwiki;

    typedef struct wikimark_config {
        const char *base_url;
        const wikimark_interwiki *interwiki;
        int interwiki_count;
    } wikimark_config;

    wikimark_config wikimark_config_default(void);

    /* --- Engine context (callbacks) --- */
    typedef struct wikimark_context {
        const char *(*resolve_variable)(const char *path, void *user_data);
        const char *(*resolve_template)(const char *name, const char *args,
                                         void *user_data);
        const char *(*resolve_embed)(const char *target, void *user_data);
        void *user_data;
    } wikimark_context;

    wikimark_context wikimark_context_default(void);

    /* --- Rendering API --- */
    char *wikimark_markdown_to_html(const char *text, size_t len, int options);

    char *wikimark_markdown_to_html_with_config(
        const char *text, size_t len, int options,
        const wikimark_config *config);

    char *wikimark_render(const char *text, size_t len, int options,
                          const wikimark_config *config,
                          const wikimark_context *context);

    void wikimark_free(void *ptr);

    /* --- Node accessors --- */
    int wikimark_node_is_wikilink(cmark_node *node);
    const char *wikimark_node_get_wiki_target(cmark_node *node);

    /* --- Python-side callback trampolines ---
     * The `extern "Python"` declarations below let us implement
     * these functions in Python (via @ffi.def_extern) and still
     * hand their addresses to libwikimark through the normal
     * function-pointer fields of wikimark_context. See the
     * cffi "extern Python" docs for details.
     */
    extern "Python" const char *_wm_py_resolve_variable(
        const char *path, void *user_data);
    extern "Python" const char *_wm_py_resolve_template(
        const char *name, const char *args, void *user_data);
    extern "Python" const char *_wm_py_resolve_embed(
        const char *target, void *user_data);
    """
)

# ------------------------------------------------------------------
# set_source: the C compile. Includes the wikimark header and links
# against libwikimark + its dependencies (static libs).
# ------------------------------------------------------------------
ffibuilder.set_source(
    "wikimark._wikimark",
    r"""
    #include <wikimark.h>
    """,
    include_dirs=[
        str(LIBWIKIMARK_DIR / "include"),
        str(CMARK_GFM_SRC),
        str(CMARK_GFM_BUILD),
    ],
    extra_objects=[
        str(LIBWIKIMARK_BUILD_DIR / "libwikimark.a"),
        str(CMARK_GFM_EXT_BUILD / "libcmark-gfm-extensions.a"),
        str(CMARK_GFM_BUILD / "libcmark-gfm.a"),
        str(LIBYAML_BUILD / "libyaml.a"),
    ],
    libraries=["pthread"],
    extra_compile_args=["-std=c11"],
)


if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
