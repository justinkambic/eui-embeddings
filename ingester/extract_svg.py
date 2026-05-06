"""Extract raw SVG from EUI's auto-generated .tsx icon assets.

EUI compiles every SVG asset into a React component .tsx file that wraps
the original SVG in `({title, titleId, ...props}) => (<svg ...>...</svg>)`.
We need the raw SVG (no JSX, no React variables) to feed to resvg.

The .tsx files are mechanical (header says "THIS IS A GENERATED FILE"),
so a careful regex pass is enough — we don't need a JSX parser.

Strategy:
1. Find the outermost <svg> ... </svg> block.
2. Extract the viewBox (always present — EUI's compile-icons script sets it).
3. Inside the block, drop:
   - any pure JSX-expression line `{ ... }` (e.g. `{title ? ... : null}`),
   - any attribute whose value is a JSX expression `attr={someVar}`,
   - the `{...props}` spread, and the title/titleId React props.
4. Return a clean SVG string with our own deterministic wrapper that the
   raster module will compose into.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


_SVG_BLOCK_RE = re.compile(r"<svg\b([^>]*?)>(.*?)</svg>", re.DOTALL | re.IGNORECASE)
_VIEWBOX_RE = re.compile(r'viewBox\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)
# Attribute whose value is a JSX expression: name={...} or name={... ? ... : ...}
_JSX_ATTR_RE = re.compile(r"\s+[a-zA-Z][\w:-]*=\{[^{}]*\}")
# Inline JSX expressions inside element bodies: {something}
# We strip whole lines that are JSX-only.
_JSX_LINE_RE = re.compile(r"^\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}\s*$", re.MULTILINE)
# Spread: {...props}
_JSX_SPREAD_RE = re.compile(r"\s+\{\.\.\.[^{}]*\}")
# `title ? <title id={titleId}>{title}</title> : null` style multi-line conditionals
# can span multiple lines — handle by stripping anything between {? : null}
_JSX_INLINE_TITLE_RE = re.compile(
    r"\{title\?\s*<title[^>]*>\{title\}</title>\s*:\s*null\}",
    re.DOTALL,
)
# JSX attribute on tags inside the body: name={...} (e.g. id={titleId})
_INNER_JSX_ATTR_RE = re.compile(r"\s+[a-zA-Z][\w:-]*=\{[^{}]*\}")


@dataclass(frozen=True)
class ExtractedSvg:
    """A normalized SVG ready to feed to resvg."""
    inner: str                         # contents between <svg> and </svg>, JSX stripped
    viewbox: tuple[float, float, float, float]


def extract_from_tsx(tsx_text: str) -> ExtractedSvg:
    """Pull the SVG content out of an EUI .tsx asset file.

    Raises ValueError if the file doesn't contain a <svg> block we can read.
    """
    block = _SVG_BLOCK_RE.search(tsx_text)
    if not block:
        raise ValueError("no <svg>..</svg> block found")
    open_attrs = block.group(1)
    inner = block.group(2)

    # viewBox
    vb_m = _VIEWBOX_RE.search(open_attrs)
    if vb_m:
        parts = vb_m.group(1).replace(",", " ").split()
        try:
            vb = tuple(float(p) for p in parts)  # type: ignore[assignment]
            if len(vb) != 4:
                raise ValueError
        except (ValueError, TypeError):
            vb = (0.0, 0.0, 16.0, 16.0)
    else:
        vb = (0.0, 0.0, 16.0, 16.0)

    # Strip JSX
    cleaned = _strip_jsx(inner)
    return ExtractedSvg(inner=cleaned.strip(), viewbox=vb)


def _strip_jsx(body: str) -> str:
    # Multi-line title conditional first (most fragile pattern).
    body = re.sub(
        r"\{title\s*\?\s*<title[^>]*>\{title\}</title>\s*:\s*null\}",
        "",
        body,
        flags=re.DOTALL,
    )
    # Pure JSX expression lines: `  {something}`
    body = _JSX_LINE_RE.sub("", body)
    # JSX attributes inside child element opening tags: `id={titleId}`,
    # `aria-labelledby={titleId}`, etc.
    body = _INNER_JSX_ATTR_RE.sub("", body)
    return body


def to_inline_svg(extracted: ExtractedSvg) -> str:
    """Wrap the extracted inner content in a clean self-contained <svg>."""
    vbx, vby, vbw, vbh = extracted.viewbox
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vbx} {vby} {vbw} {vbh}">'
        f"{extracted.inner}"
        f"</svg>"
    )
