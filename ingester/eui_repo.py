"""Manage the local EUI clone for the ingester.

The clone lives under .cache/eui (gitignored). We keep it on a detached HEAD
at whatever tag we're currently ingesting; never push, never check out a
branch, never disturb the user's eui-fork repo at ~/git/justinkambic/eui.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


DEFAULT_REPO_URL = "https://github.com/elastic/eui.git"
DEFAULT_LOCATION = ".cache/eui"


@dataclass
class EuiRepo:
    location: Path

    @classmethod
    def open_or_clone(cls, location: str | Path = DEFAULT_LOCATION, repo_url: str = DEFAULT_REPO_URL) -> "EuiRepo":
        loc = Path(location)
        loc.parent.mkdir(parents=True, exist_ok=True)
        if not (loc / ".git").exists():
            subprocess.run(
                ["git", "clone", "--quiet", "--no-tags", repo_url, str(loc)],
                check=True,
            )
        return cls(location=loc)

    def fetch_tags(self) -> None:
        subprocess.run(
            ["git", "-C", str(self.location), "fetch", "--quiet", "--tags", "origin"],
            check=True,
        )

    def checkout(self, ref: str) -> None:
        # Detached HEAD at the tag.
        subprocess.run(
            ["git", "-C", str(self.location), "checkout", "--quiet", ref],
            check=True,
        )

    def list_tags(self, pattern: str = "v*.*.*") -> list[str]:
        out = subprocess.check_output(
            ["git", "-C", str(self.location), "tag", "-l", pattern],
            text=True,
        )
        return [t.strip() for t in out.splitlines() if t.strip()]

    def commit_date(self, ref: str) -> str:
        """ISO-8601 commit date for the given ref."""
        out = subprocess.check_output(
            ["git", "-C", str(self.location), "log", "-1", "--format=%aI", ref],
            text=True,
        ).strip()
        return out

    def assets_dir(self) -> Path:
        """Resolve the path to the icon assets dir for the currently checked-out
        version. Detects v95+ monorepo vs pre-v95 flat layout."""
        monorepo = self.location / "packages/eui/src/components/icon/assets"
        flat = self.location / "src/components/icon/assets"
        if monorepo.exists():
            return monorepo
        if flat.exists():
            return flat
        raise FileNotFoundError(f"could not locate icon assets dir under {self.location}")
