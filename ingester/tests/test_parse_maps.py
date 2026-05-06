"""Snapshot-style tests for ingester.parse_maps.

We pin minimum expected counts for v91 and v115 against the EUI checkout in
.cache/eui. If the ingester loses entries due to an upstream refactor, these
tests fail loudly.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ingester.parse_maps import (
    IconEntry,
    TokenEntry,
    parse_icon_map,
    parse_repo,
    parse_token_map,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
EUI_CHECKOUT = REPO_ROOT / ".cache/eui"


def _checkout(tag: str) -> None:
    if not (EUI_CHECKOUT / ".git").exists():
        pytest.skip(f"no EUI checkout at {EUI_CHECKOUT}; run `git clone elastic/eui` there to enable")
    subprocess.run(
        ["git", "-C", str(EUI_CHECKOUT), "checkout", "--quiet", tag],
        check=True,
    )


# --- icon-map shape coverage ------------------------------------------------


def test_parse_icon_map_v91_string_literal_shape():
    text = """
    /* header */
    export const typeToPathMap = {
      accessibility: 'accessibility',
      addDataApp: 'app_add_data',
      // a comment
      arrowDown: "arrow_down",
    };
    """
    entries = parse_icon_map(text)
    assert IconEntry("accessibility", "accessibility") in entries
    assert IconEntry("addDataApp", "app_add_data") in entries
    assert IconEntry("arrowDown", "arrow_down") in entries
    assert len(entries) == 3


def test_parse_icon_map_v115_dynamic_import_shape():
    text = """
    export const typeToPathMap = {
      accessibility: () => import('./assets/accessibility'),
      addDataApp: () => import('./assets/app_add_data'),
      arrowDown: () => import("./assets/arrow_down"),
    };
    """
    entries = parse_icon_map(text)
    assert IconEntry("accessibility", "accessibility") in entries
    assert IconEntry("addDataApp", "app_add_data") in entries
    assert IconEntry("arrowDown", "arrow_down") in entries
    assert len(entries) == 3


def test_parse_icon_map_missing_export_raises():
    with pytest.raises(ValueError):
        parse_icon_map("export const somethingElse = {};")


# --- token-map shape coverage -----------------------------------------------


def test_parse_token_map_basic():
    text = """
    export const TOKEN_MAP: {
      [mapType in EuiTokenMapType]: Omit<TokenProps, 'iconType'>;
    } = {
      tokenAlias: {
        shape: 'square',
        color: 'euiColorVis0',
      },
      tokenAnnotation: {
        shape: 'circle',
        color: 'euiColorVis8',
      },
    };
    """
    entries = parse_token_map(text)
    assert TokenEntry("tokenAlias", "square", "euiColorVis0") in entries
    assert TokenEntry("tokenAnnotation", "circle", "euiColorVis8") in entries
    assert len(entries) == 2


def test_parse_token_map_returns_empty_when_absent():
    assert parse_token_map("// no map here") == []


# --- live snapshot tests against the checkout ------------------------------


@pytest.mark.parametrize(
    "tag, layout, min_icons, min_tokens",
    [
        ("v91.0.0", "flat", 480, 50),
        ("v115.0.0", "monorepo", 670, 50),
    ],
)
def test_parse_repo_real_versions(tag, layout, min_icons, min_tokens):
    _checkout(tag)
    icons, tokens, paths = parse_repo(EUI_CHECKOUT)
    assert paths.layout == layout
    assert len(icons) >= min_icons, f"{tag}: only {len(icons)} icons parsed"
    assert len(tokens) >= min_tokens, f"{tag}: only {len(tokens)} tokens parsed"
    # Every prop_name should be a unique JS identifier
    assert len({i.prop_name for i in icons}) == len(icons)
    assert len({t.prop_name for t in tokens}) == len(tokens)
    # Token shapes/colors are constrained
    for t in tokens:
        assert t.shape in {"square", "circle"}, f"{tag} {t.prop_name}: unexpected shape {t.shape!r}"
        assert t.color.startswith("euiColorVis"), f"{tag} {t.prop_name}: unexpected color {t.color!r}"
