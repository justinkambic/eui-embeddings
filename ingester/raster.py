"""SVG -> PNG rasterization and synthetic chrome composition.

Two callers:
- `rasterize_glyph(svg_text)`     — returns PNG bytes for a bare EUI icon.
- `rasterize_token(svg_text, ...)` — wraps the icon in synthetic chrome
                                     matching EuiToken's shape + color, then
                                     rasterizes.

No Playwright. No headless browser. Everything is pure SVG manipulation
plus resvg.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import resvg_py

from .palette import DEFAULT_CHROME_HEX, resolve as resolve_color


# --- types ------------------------------------------------------------------


@dataclass(frozen=True)
class ResolvedChrome:
    shape: str        # "square" or "circle"
    color_token: str  # e.g. "euiColorVis0"
    color_hex: str    # e.g. "#54B399"


# --- SVG plumbing -----------------------------------------------------------


_SVG_OPEN_RE = re.compile(r"<svg\b[^>]*>", re.IGNORECASE)
_SVG_CLOSE_RE = re.compile(r"</svg>", re.IGNORECASE)
_VIEWBOX_RE = re.compile(r'viewBox\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)


def _extract_inner(svg_text: str) -> tuple[str, tuple[float, float, float, float]]:
    """Return (inner-content, (vb_x, vb_y, vb_w, vb_h)).

    Strips the outermost <svg ...>...</svg> wrapper and returns the inner
    body plus the viewBox parsed from the wrapper. Falls back to "0 0 16 16"
    if no viewBox is set (matches EUI's default).
    """
    open_m = _SVG_OPEN_RE.search(svg_text)
    close_m = _SVG_CLOSE_RE.search(svg_text)
    if not (open_m and close_m):
        raise ValueError("not a valid SVG (missing <svg> or </svg>)")
    inner = svg_text[open_m.end():close_m.start()].strip()

    vb = (0.0, 0.0, 16.0, 16.0)
    vb_m = _VIEWBOX_RE.search(open_m.group(0))
    if vb_m:
        parts = vb_m.group(1).replace(",", " ").split()
        if len(parts) == 4:
            try:
                vb = tuple(float(p) for p in parts)  # type: ignore[assignment]
            except ValueError:
                pass
    return inner, vb


# --- public API -------------------------------------------------------------


# Standard pixel dimensions for the rasterized PNG. 256x256 gives jina-clip-v2
# plenty of detail without making each call expensive.
DEFAULT_PNG_SIZE = 256


def rasterize_glyph(svg_text: str, *, size: int = DEFAULT_PNG_SIZE) -> bytes:
    """Render a bare EUI icon SVG to a square PNG with a white background.

    EUI icons use `fill="currentColor"`, which resvg renders as black with
    no CSS in scope. That gives us a deterministic black-on-white render
    matching the legacy `image_processor.normalize_search_image` output.
    """
    inner, (vbx, vby, vbw, vbh) = _extract_inner(svg_text)
    # Compose: white background + inner content.
    # We force the inner fill to a default black (in case currentColor isn't
    # honored by resvg in some edge cases) by wrapping in a <g fill="black">.
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="{vbx} {vby} {vbw} {vbh}" '
        f'width="{size}" height="{size}">'
        f'<rect x="{vbx}" y="{vby}" width="{vbw}" height="{vbh}" fill="white"/>'
        f'<g fill="black">{inner}</g>'
        f'</svg>'
    )
    return bytes(resvg_py.svg_to_bytes(svg_string=svg))


def rasterize_token(
    svg_text: str,
    chrome: ResolvedChrome,
    *,
    size: int = DEFAULT_PNG_SIZE,
) -> bytes:
    """Render a chromed EuiToken-style PNG.

    Composition (in a 32x32 outer viewBox):
      - Background shape (rect rx=8 for square, circle for circle) filling 0..32.
      - Inner glyph content placed in the centered 16x16 region in white.

    The outer canvas is rasterized to `size`x`size` PNG with no extra padding.
    """
    inner, (vbx, vby, vbw, vbh) = _extract_inner(svg_text)

    # Inner glyph maps onto a 16x16 area centered at (16, 16) in a 32-unit canvas.
    # Compute the transform from the source viewBox into that 16x16 area.
    inner_size = 16.0
    pad = (32.0 - inner_size) / 2.0  # 8
    sx = inner_size / vbw if vbw else 1.0
    sy = inner_size / vbh if vbh else 1.0
    tx = pad - vbx * sx
    ty = pad - vby * sy

    if chrome.shape == "circle":
        bg = '<circle cx="16" cy="16" r="16" fill="' + chrome.color_hex + '"/>'
    elif chrome.shape == "square":
        bg = (
            '<rect x="0" y="0" width="32" height="32" rx="8" ry="8" fill="'
            + chrome.color_hex + '"/>'
        )
    else:
        # Defensive: fall back to a square with neutral color if shape is unrecognized.
        bg = (
            '<rect x="0" y="0" width="32" height="32" rx="8" ry="8" fill="'
            + DEFAULT_CHROME_HEX + '"/>'
        )

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" '
        f'width="{size}" height="{size}">'
        f'{bg}'
        f'<g transform="translate({tx:.4f} {ty:.4f}) scale({sx:.4f} {sy:.4f})" fill="white">'
        f'{inner}'
        f'</g>'
        '</svg>'
    )
    return bytes(resvg_py.svg_to_bytes(svg_string=svg))


def resolve_chrome(color_token: str, shape: str, theme: str = "amsterdam") -> ResolvedChrome:
    """Build a ResolvedChrome from a TOKEN_MAP entry's raw string fields.

    `theme` selects which EUI palette to resolve `euiColorVis*` against.
    Defaults to Amsterdam for backward compatibility; pass `"borealis"`
    for v110+ where EUI rebranded the same color names to different
    hexes.
    """
    return ResolvedChrome(
        shape=shape,
        color_token=color_token,
        color_hex=resolve_color(color_token, theme=theme),
    )
