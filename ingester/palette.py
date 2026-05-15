"""EUI vis-color palette resolution, theme-aware.

EUI shipped two themes during the v91..v115 range we target:
  - Amsterdam (v91 onward) — original palette
  - Borealis (introduced in 2025, default in v110+) — repalette where the
    same `euiColorVis*` names map to different hexes

A token like tokenParameter (color: euiColorVis6) renders as tan
(#B9A888) in Amsterdam but coral (#F6726A) in Borealis. To match the
docs page rendering at index time we have to pick the right palette per
version.

The simple heuristic that matches every version we've ingested: a repo
that contains the `eui-theme-amsterdam` package is Amsterdam-era; a repo
with only `eui-theme-borealis` is Borealis-era. Detected once per
ingestion via `theme_for_repo()`.
"""

from __future__ import annotations

from pathlib import Path

# Amsterdam palette — the original. Hexes captured from
# packages/eui/src/themes/eui-amsterdam/global_styling/variables/_colors.ts
# (or the resolved theme JSON) at the v95 baseline.
_AMSTERDAM = {
    "euiColorVis0":  "#54B399",
    "euiColorVis1":  "#6092C0",
    "euiColorVis2":  "#D36086",
    "euiColorVis3":  "#9170B8",
    "euiColorVis4":  "#CA8EAE",
    "euiColorVis5":  "#D6BF57",
    "euiColorVis6":  "#B9A888",
    "euiColorVis7":  "#DA8B45",
    "euiColorVis8":  "#AA6556",
    "euiColorVis9":  "#E7664C",
    "euiColorVis00": "#54B399",
    "euiColorVis10": "#6092C0",
    "euiColorVis20": "#D36086",
}

# Borealis palette — taken from
# packages/eui-theme-borealis/src/eui_theme_borealis_light.json (the
# resolved values, since the source uses indirection via SEMANTIC_COLORS).
# Each `euiColorVis*` name maps to a different hex than Amsterdam.
_BOREALIS = {
    "euiColorVis0":  "#16C5C0",
    "euiColorVis1":  "#A6EDEA",
    "euiColorVis2":  "#61A2FF",
    "euiColorVis3":  "#BFDBFF",
    "euiColorVis4":  "#EE72A6",
    "euiColorVis5":  "#FFC7DB",
    "euiColorVis6":  "#F6726A",
    "euiColorVis7":  "#FFC9C2",
    "euiColorVis8":  "#EAAE01",
    "euiColorVis9":  "#FCD883",
    "euiColorVis00": "#16C5C0",
    "euiColorVis10": "#A6EDEA",
    "euiColorVis20": "#61A2FF",
}

PALETTES: dict[str, dict[str, str]] = {
    "amsterdam": _AMSTERDAM,
    "borealis":  _BOREALIS,
}

DEFAULT_THEME = "amsterdam"
DEFAULT_CHROME_HEX = "#888888"

# Backward-compat: existing call sites still import EUI_COLOR_VIS. Default
# to the Amsterdam palette so older versions keep rendering correctly.
EUI_COLOR_VIS = _AMSTERDAM


def theme_for_repo(repo_dir: Path) -> str:
    """Detect which palette to use given a checked-out EUI repo.

    Heuristic: presence of the eui-theme-amsterdam package implies
    Amsterdam-era (v91..v109). Repos with only eui-theme-borealis are
    Borealis-era (v110+). Older repos (v91..v95) have neither package
    at packages/eui-theme-* but live as an in-tree theme directory; we
    treat those as Amsterdam by default.
    """
    repo_dir = Path(repo_dir)
    has_amsterdam_pkg = (repo_dir / "packages/eui-theme-amsterdam").exists()
    has_borealis_pkg = (repo_dir / "packages/eui-theme-borealis").exists()
    if has_borealis_pkg and not has_amsterdam_pkg:
        return "borealis"
    return "amsterdam"


def resolve(color_token: str, theme: str = DEFAULT_THEME) -> str:
    """Map a euiColorVis token to a hex string for the given theme."""
    return PALETTES.get(theme, _AMSTERDAM).get(color_token, DEFAULT_CHROME_HEX)
