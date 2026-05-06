"""Parse EUI's typeToPathMap (icons) and TOKEN_MAP (tokens) from a repo checkout.

Handles two layouts:
- v91 .. v94: src/components/{icon,token}/{icon,token}_map.ts
- v95+:       packages/eui/src/components/{icon,token}/{icon,token}_map.ts

Handles two icon-map shapes:
- v91-ish: `accessibility: 'accessibility',`
- v115-ish: `accessibility: () => import('./assets/accessibility'),`

TOKEN_MAP shape is stable across the v91..v115 range we care about:
    tokenAlias: {
      shape: 'square',
      color: 'euiColorVis0',
    },

We deliberately use regex rather than a TS AST parser. The maps are mechanical,
EUI-controlled, and have been stable for years; regex is faster, dep-free, and
the snapshot tests in tests/test_parse_maps.py keep us honest if EUI ever
restructures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


# --- types ------------------------------------------------------------------


@dataclass(frozen=True)
class IconEntry:
    prop_name: str        # the value passed to <EuiIcon type=...>
    asset_filename: str   # the filename (no extension) under assets/


@dataclass(frozen=True)
class TokenEntry:
    prop_name: str        # one of EuiTokenMapType, e.g. "tokenString"
    shape: str            # "square" | "circle"
    color: str            # "euiColorVis<N>" e.g. "euiColorVis0"


@dataclass(frozen=True)
class RepoPaths:
    icon_map: Path
    token_map: Path | None  # None pre-v95 if it doesn't exist
    layout: str             # "monorepo" (v95+) or "flat" (pre-v95)


# --- regexes ----------------------------------------------------------------


# Matches both shapes of typeToPathMap entries.
# v91-ish: `propName: 'asset_filename',`
# v115-ish: `propName: () => import('./assets/asset_filename'),`
# We strip block comments first, then run this against the body of the map.
_ICON_ENTRY_RE = re.compile(
    r"""
    ^\s*                                # leading whitespace
    (?P<prop>[A-Za-z_][\w]*)            # prop name (JS identifier)
    \s*:\s*
    (?:
        ['"](?P<lit>[^'"]+)['"]                          # v91 string literal
      | \(\s*\)\s*=>\s*import\s*\(\s*['"]\./assets/(?P<imp>[^'"]+)['"]\s*\)  # v115 dynamic import
    )
    """,
    re.MULTILINE | re.VERBOSE,
)

# Matches a single TOKEN_MAP entry. Multi-line.
_TOKEN_ENTRY_RE = re.compile(
    r"""
    ^\s*
    (?P<prop>[A-Za-z_][\w]*)            # prop name
    \s*:\s*\{                           # opening brace of the inner object
    (?P<body>[^{}]*)                    # inner properties (no nested braces in TOKEN_MAP)
    \}                                  # closing brace
    """,
    re.MULTILINE | re.VERBOSE | re.DOTALL,
)

_TOKEN_SHAPE_RE = re.compile(r"shape\s*:\s*['\"](\w+)['\"]")
_TOKEN_COLOR_RE = re.compile(r"color\s*:\s*['\"]([\w]+)['\"]")

# Strip /* ... */ block comments so they don't interfere with body extraction.
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
# Strip // line comments.
_LINE_COMMENT_RE = re.compile(r"//[^\n]*")

# The icon map value is `export const typeToPathMap = { ... };`
# Capture the body between the matching outer braces.
_ICON_MAP_BODY_RE = re.compile(
    r"export\s+const\s+typeToPathMap\b[^=]*=\s*\{(?P<body>.*?)\}\s*;",
    re.DOTALL,
)

_TOKEN_MAP_BODY_RE = re.compile(
    r"export\s+const\s+TOKEN_MAP\b[^=]*=\s*\{(?P<body>.*?)\}\s*;",
    re.DOTALL,
)


# --- public API -------------------------------------------------------------


def find_repo_paths(repo_dir: Path) -> RepoPaths:
    """Locate icon_map.ts and token_map.ts in a checked-out EUI repo.

    Detects v95+ monorepo layout vs pre-v95 flat layout by file existence.
    """
    repo_dir = Path(repo_dir)
    monorepo_icon = repo_dir / "packages/eui/src/components/icon/icon_map.ts"
    monorepo_token = repo_dir / "packages/eui/src/components/token/token_map.ts"
    flat_icon = repo_dir / "src/components/icon/icon_map.ts"
    flat_token = repo_dir / "src/components/token/token_map.ts"

    if monorepo_icon.exists():
        return RepoPaths(
            icon_map=monorepo_icon,
            token_map=monorepo_token if monorepo_token.exists() else None,
            layout="monorepo",
        )
    if flat_icon.exists():
        return RepoPaths(
            icon_map=flat_icon,
            token_map=flat_token if flat_token.exists() else None,
            layout="flat",
        )
    raise FileNotFoundError(
        f"could not locate icon_map.ts in either layout under {repo_dir}"
    )


def _strip_comments(text: str) -> str:
    text = _BLOCK_COMMENT_RE.sub("", text)
    text = _LINE_COMMENT_RE.sub("", text)
    return text


def parse_icon_map(text: str) -> list[IconEntry]:
    """Extract IconEntry list from the contents of icon_map.ts.

    Raises ValueError if the typeToPathMap export can't be located.
    """
    cleaned = _strip_comments(text)
    body_match = _ICON_MAP_BODY_RE.search(cleaned)
    if not body_match:
        raise ValueError("could not locate `export const typeToPathMap = { ... };`")
    body = body_match.group("body")

    entries: list[IconEntry] = []
    for m in _ICON_ENTRY_RE.finditer(body):
        prop = m.group("prop")
        asset = m.group("lit") or m.group("imp")
        if not asset:
            continue
        entries.append(IconEntry(prop_name=prop, asset_filename=asset))
    return entries


def parse_token_map(text: str) -> list[TokenEntry]:
    """Extract TokenEntry list from the contents of token_map.ts.

    Returns [] if TOKEN_MAP isn't present (older versions may differ).
    """
    cleaned = _strip_comments(text)
    body_match = _TOKEN_MAP_BODY_RE.search(cleaned)
    if not body_match:
        return []
    body = body_match.group("body")

    entries: list[TokenEntry] = []
    for m in _TOKEN_ENTRY_RE.finditer(body):
        prop = m.group("prop")
        inner = m.group("body")
        shape_m = _TOKEN_SHAPE_RE.search(inner)
        color_m = _TOKEN_COLOR_RE.search(inner)
        if not (shape_m and color_m):
            # Skip entries that don't conform; the snapshot tests will
            # surface unexpected shapes early.
            continue
        entries.append(
            TokenEntry(
                prop_name=prop,
                shape=shape_m.group(1),
                color=color_m.group(1),
            )
        )
    return entries


def parse_repo(repo_dir: Path) -> tuple[list[IconEntry], list[TokenEntry], RepoPaths]:
    """Read and parse both maps from a checked-out EUI repo."""
    paths = find_repo_paths(repo_dir)
    icon_text = paths.icon_map.read_text(encoding="utf-8")
    icons = parse_icon_map(icon_text)
    tokens: list[TokenEntry] = []
    if paths.token_map is not None:
        tokens = parse_token_map(paths.token_map.read_text(encoding="utf-8"))
    return icons, tokens, paths
