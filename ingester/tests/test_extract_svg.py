"""Tests for ingester.extract_svg.

Focus on JSX-stripping edge cases discovered while ingesting EUI icons.
"""

from __future__ import annotations

import pytest

from ingester.extract_svg import extract_from_tsx, to_inline_svg


def _wrap(svg_block: str) -> str:
    """Minimal .tsx scaffold matching EUI's compile-icons output."""
    return (
        "import * as React from 'react';\n"
        "const Icon = ({title, titleId, ...props}) => (\n"
        "  <svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'>\n"
        "    {title ? <title id={titleId}>{title}</title> : null}\n"
        f"    {svg_block}\n"
        "  </svg>\n"
        ");\n"
        "export const icon = Icon;\n"
    )


def test_jsx_numeric_attrs_are_preserved_as_strings():
    """Regression: stop_fill, swatch_input rasterized blank because <rect>
    had width={12} height={12} x={2} y={2} dropped, leaving an empty tag."""
    tsx = _wrap('<rect width={12} height={12} x={2} y={2} rx={2} />')
    ext = extract_from_tsx(tsx)
    inner = ext.inner
    assert 'width="12"' in inner
    assert 'height="12"' in inner
    assert 'x="2"' in inner
    assert 'y="2"' in inner
    assert 'rx="2"' in inner


def test_jsx_decimal_numerics_preserved():
    tsx = _wrap('<circle cx={2.5} cy={2.5} r={0.75} />')
    ext = extract_from_tsx(tsx)
    assert 'cx="2.5"' in ext.inner
    assert 'cy="2.5"' in ext.inner
    assert 'r="0.75"' in ext.inner


def test_jsx_negative_numerics_preserved():
    tsx = _wrap('<rect x={-2} y={-2} width={20} height={20} />')
    ext = extract_from_tsx(tsx)
    assert 'x="-2"' in ext.inner
    assert 'y="-2"' in ext.inner


def test_jsx_string_literals_preserved():
    tsx = _wrap('<rect fill={"black"} stroke={\'red\'} />')
    ext = extract_from_tsx(tsx)
    assert 'fill="black"' in ext.inner
    assert 'stroke="red"' in ext.inner


def test_generate_id_pattern_preserved():
    """Regression: logo_apache used id={generateId('a')} and
    fill={`url(#${generateId('a')})`}; both got dropped, leaving gradients
    unreachable. Recover them by extracting the literal argument."""
    tsx = _wrap(
        '<defs><linearGradient id={generateId("a")}><stop /></linearGradient></defs>'
        '<path fill={`url(#${generateId("a")})`} d="M0 0h10v10H0z" />'
    )
    ext = extract_from_tsx(tsx)
    inner = ext.inner
    assert 'id="a"' in inner
    assert 'fill="url(#a)"' in inner


def test_unrecoverable_jsx_attribute_dropped():
    """Variables, function calls, objects → still dropped (existing behavior)."""
    tsx = _wrap('<rect aria-labelledby={titleId} style={{maskType:"alpha"}} />')
    ext = extract_from_tsx(tsx)
    inner = ext.inner
    # The attributes should be stripped entirely.
    assert 'aria-labelledby' not in inner
    assert 'style=' not in inner
    # Tag itself should still be there.
    assert '<rect' in inner


def test_title_conditional_still_stripped():
    """{title ? <title>...</title> : null} body element is removed."""
    tsx = _wrap('<rect width={10} height={10} />')
    ext = extract_from_tsx(tsx)
    assert '<title' not in ext.inner


def test_to_inline_svg_round_trip():
    tsx = _wrap('<rect width={16} height={16} fill="black" />')
    inline = to_inline_svg(extract_from_tsx(tsx))
    assert inline.startswith('<svg')
    assert 'viewBox="0.0 0.0 16.0 16.0"' in inline
    assert 'width="16"' in inline
    assert 'fill="black"' in inline
    assert inline.endswith('</svg>')
