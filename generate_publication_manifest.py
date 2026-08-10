#!/usr/bin/env python3
"""Canonical stdlib-only generator for the checked-in public-candidate manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "egoh-demo" / "public-pack" / "PUBLICATION_MANIFEST.json"
OPERATING_CORE = ROOT / "operating-core-demo"
MANIFEST_EXCLUSIONS = [
    ".git/**",
    ".pytest_cache/**",
    "**/.pytest_cache/**",
    "**/__pycache__/**",
    "**/*.pyc",
    "**/*.pyo",
    "egoh-demo/public-pack/PUBLICATION_MANIFEST.json",
]


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tracked_paths(root: Path) -> set[Path]:
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"], check=True, capture_output=True
    )
    return {root / item for item in completed.stdout.decode("utf-8").split("\0") if item}


def is_excluded(root: Path, path: Path) -> bool:
    """Apply the declared candidate exclusions to one path beneath ``root``."""
    relative = path.relative_to(root).as_posix()
    parts = Path(relative).parts
    return (
        relative == "egoh-demo/public-pack/PUBLICATION_MANIFEST.json"
        or ".git" in parts
        or ".pytest_cache" in parts
        or "__pycache__" in parts
        or path.suffix in {".pyc", ".pyo"}
    )


def content_paths(root: Path = ROOT) -> list[Path]:
    """Return every candidate file, including local composed-demo additions.

    The explicit directories make local regeneration bind new demo files before
    they are committed; a clean checkout also reaches them through git.
    """
    paths = _tracked_paths(root)
    paths.add(root / Path(__file__).name)
    for directory in (root / "egoh-demo", root / "operating-core-demo"):
        if directory.is_dir():
            paths.update(path for path in directory.rglob("*") if path.is_file())
    return sorted(
        path for path in paths if not is_excluded(root, path)
    )


def manifest_payload(root: Path = ROOT) -> dict[str, object]:
    files = [
        {"path": str(path.relative_to(root)), "sha256": sha256_file(path)}
        for path in content_paths(root)
    ]
    return {
        "schema": "evidence-gated-public-candidate-manifest-v1",
        "algorithm": "sha256",
        "exclusions": MANIFEST_EXCLUSIONS,
        "files": files,
        "tree_sha256": hashlib.sha256(canonical_json(files).encode("utf-8")).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate the public-candidate manifest.")
    parser.add_argument("--check", action="store_true", help="Fail unless the checked-in manifest is canonical.")
    args = parser.parse_args()
    payload = manifest_payload()
    if args.check:
        try:
            current = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return 2
        return 0 if current == payload else 1
    MANIFEST.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
