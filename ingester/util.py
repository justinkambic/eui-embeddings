"""Small helpers used across the ingester."""

from __future__ import annotations

import re


def humanize_prop(prop: str) -> str:
    """Turn a camelCase prop name into a space-separated lower phrase.

    Examples:
        humanize_prop("search")           -> "search"
        humanize_prop("addDataApp")       -> "add data app"
        humanize_prop("tokenString")      -> "token string"
        humanize_prop("logoElasticsearch")-> "logo elasticsearch"
        humanize_prop("arrowDownLeft")    -> "arrow down left"
        humanize_prop("XMLHttp")          -> "xml http"
    """
    # Split before any uppercase preceded by lowercase/digit.
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", prop)
    # Split between consecutive uppercase letters when followed by lowercase
    # (so "XMLHttp" -> "XML Http", which then lowercases cleanly).
    spaced = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", spaced)
    return spaced.lower()


def major_from_tag(tag: str) -> int:
    """Return the major-version integer from a tag like 'v115.0.0'."""
    m = re.match(r"v(\d+)\.", tag)
    if not m:
        raise ValueError(f"not a vN.M.P tag: {tag!r}")
    return int(m.group(1))


def doc_id(prop_name: str, release_tag: str) -> str:
    """Canonical doc id used in eui_icons. One doc per (prop_name, release_tag)."""
    return f"{prop_name}@{release_tag}"
