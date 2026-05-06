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

    # Strip JSX, then normalize JSX-style attribute names to SVG kebab-case.
    cleaned = _normalize_attr_names(_strip_jsx(inner))
    return ExtractedSvg(inner=cleaned.strip(), viewbox=vb)


_JSX_NUMERIC_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
_JSX_STRING_RE = re.compile(r"""^(['"])([^'"]*)\1$""")
_JSX_GENERATE_ID_RE = re.compile(r"""^generateId\(\s*['"]([^'"]+)['"]\s*\)$""")
# Backtick-template literal containing exactly one ${generateId('x')} interpolation.
_JSX_TEMPLATE_GEN_ID_RE = re.compile(
    r"""^`([^`$]*)\$\{\s*generateId\(\s*['"]([^'"]+)['"]\s*\)\s*\}([^`$]*)`$"""
)


def _try_recover_jsx_literal(body: str) -> str | None:
    """If a JSX expression body is a literal we can preserve, return its
    string form. Otherwise return None and the caller should drop the
    whole attribute (current default behavior)."""
    s = body.strip()
    # Pure number: width={16} → width="16"
    if _JSX_NUMERIC_RE.match(s):
        return s
    # Quoted string: foo={'bar'} → foo="bar"
    m = _JSX_STRING_RE.match(s)
    if m:
        return m.group(2)
    # generateId('x') → "x"
    m = _JSX_GENERATE_ID_RE.match(s)
    if m:
        return m.group(1)
    # `prefix${generateId('x')}suffix` → "prefix" + "x" + "suffix"
    m = _JSX_TEMPLATE_GEN_ID_RE.match(s)
    if m:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}"
    return None


def _strip_jsx(body: str) -> str:
    """Brace-aware JSX stripper.

    Walks characters; outside of string literals, when we see `{`, we find
    the matching `}` (handling nesting like `style={{maskType:'alpha'}}`).

    For attributes — `name={...}` — we try to recover the value if it's a
    JSX literal we can preserve (numeric, string literal, generateId call,
    template literal that wraps a generateId). If we can, we rewrite the
    attribute as `name="<recovered>"`. Otherwise we drop the whole
    attribute (the conservative default).

    For non-attribute braces (top-level JSX expressions like
    `{title ? ... : null}`), we just remove them.

    This handles:
      - `{title ? <title id={titleId}>{title}</title> : null}`  → ""
      - `width={16}` → `width="16"` (preserved as numeric attribute)
      - `aria-labelledby={titleId}` → "" (variable, can't recover)
      - `style={{maskType: 'alpha'}}` → "" (object, can't recover)
      - `id={generateId('a')}` → `id="a"` (recoverable from EUI's pattern)
      - fill={`url(#${generateId('a')})`} → fill="url(#a)" (template literal)

    What remains is plain XML/SVG with quoted attributes only.
    """
    out: list[str] = []
    i = 0
    n = len(body)
    while i < n:
        c = body[i]
        # Skip over string literals so we don't misread `{` inside attribute values.
        if c == '"' or c == "'":
            quote = c
            out.append(c)
            i += 1
            while i < n:
                if body[i] == "\\" and i + 1 < n:
                    out.append(body[i])
                    out.append(body[i + 1])
                    i += 2
                    continue
                out.append(body[i])
                if body[i] == quote:
                    i += 1
                    break
                i += 1
            continue

        if c == "{":
            # Determine whether this brace-expression is an attribute value
            # (`name={...}`) or a free-standing JSX expression. Look back at
            # the rendered output for a pending `=` after an attribute name.
            j = len(out) - 1
            while j >= 0 and out[j] in " \t\r\n":
                j -= 1
            is_attr_value = False
            attr_cut_to: int | None = None
            if j >= 0 and out[j] == "=":
                k = j - 1
                while k >= 0 and (out[k].isalnum() or out[k] in "-_:"):
                    k -= 1
                while k >= 0 and out[k] in " \t\r\n":
                    k -= 1
                attr_cut_to = k + 1  # truncate-to-here if we end up dropping
                is_attr_value = True

            # Capture the brace contents (handling nested braces and string
            # literals inside).
            depth = 1
            start = i + 1
            i += 1
            while i < n and depth > 0:
                ch = body[i]
                if ch == '"' or ch == "'":
                    qq = ch
                    i += 1
                    while i < n and body[i] != qq:
                        if body[i] == "\\" and i + 1 < n:
                            i += 2
                            continue
                        i += 1
                    if i < n:
                        i += 1
                    continue
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                i += 1
            inner_body = body[start : i - 1] if depth == 0 else ""

            if is_attr_value:
                recovered = _try_recover_jsx_literal(inner_body)
                if recovered is not None:
                    # Rewrite as a quoted attribute value: drop the trailing
                    # whitespace/`=` we kept, then re-emit `="<recovered>"`.
                    # We keep the `=` (it's at out[j]) and just append the quoted value.
                    out.append('"')
                    out.append(recovered.replace('"', "&quot;"))
                    out.append('"')
                else:
                    # Couldn't recover — drop the whole attribute, including
                    # the leading whitespace before its name.
                    del out[attr_cut_to:]
            # Non-attribute brace expressions (free-standing JSX) are silently dropped.
            continue

        out.append(c)
        i += 1

    return "".join(out)


# JSX uses camelCase for SVG attributes; SVG itself wants kebab-case for some.
# Map the ones EUI actually uses.
_JSX_TO_SVG_ATTR = {
    "fillRule": "fill-rule",
    "clipRule": "clip-rule",
    "fillOpacity": "fill-opacity",
    "strokeWidth": "stroke-width",
    "strokeLinecap": "stroke-linecap",
    "strokeLinejoin": "stroke-linejoin",
    "strokeOpacity": "stroke-opacity",
    "strokeDasharray": "stroke-dasharray",
    "stopColor": "stop-color",
    "stopOpacity": "stop-opacity",
    "textAnchor": "text-anchor",
    "vectorEffect": "vector-effect",
    "maskUnits": "maskUnits",       # already camelCase in SVG too
    "gradientUnits": "gradientUnits",
    "patternUnits": "patternUnits",
    "preserveAspectRatio": "preserveAspectRatio",
    "xmlnsXlink": "xmlns:xlink",
    "xlinkHref": "xlink:href",
}


def _normalize_attr_names(body: str) -> str:
    for camel, kebab in _JSX_TO_SVG_ATTR.items():
        if camel == kebab:
            continue
        body = re.sub(rf"\b{re.escape(camel)}\b", kebab, body)
    return body


def to_inline_svg(extracted: ExtractedSvg) -> str:
    """Wrap the extracted inner content in a clean self-contained <svg>.

    Includes the xlink namespace declaration because some EUI logos use
    xlink:href (recovered from JSX `xlinkHref={...}`) and resvg refuses
    to render unknown-prefix attributes.
    """
    vbx, vby, vbw, vbh = extracted.viewbox
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="{vbx} {vby} {vbw} {vbh}">'
        f"{extracted.inner}"
        f"</svg>"
    )
