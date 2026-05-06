"""Hardcoded EUI Amsterdam-theme vis-color palette.

We use one canonical palette across all versions and tokens. The goal is
consistent vector embeddings across the index, not pixel-perfect theme
reproduction. If EUI ever ships a token with a `color` value not in this
table, the chrome composer falls back to a neutral gray and logs a warning.

These hexes are taken from the EUI Amsterdam theme as of v115. Borealis
(introduced in 2025) has slightly different values; we deliberately stick
with Amsterdam for stability across the v91..v115 range.
"""

EUI_COLOR_VIS = {
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
    # Some EUI versions use a 10-color palette under different names; we map them defensively.
    "euiColorVis00": "#54B399",
    "euiColorVis10": "#6092C0",
    "euiColorVis20": "#D36086",
}

DEFAULT_CHROME_HEX = "#888888"


def resolve(color_token: str) -> str:
    """Map a euiColorVis token to a hex string. Returns DEFAULT_CHROME_HEX if unknown."""
    return EUI_COLOR_VIS.get(color_token, DEFAULT_CHROME_HEX)
