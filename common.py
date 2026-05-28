"""Shared paths and tiny JSONL helpers. Everything else stays in its module."""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

# Resolves to /app inside the container, to the repo root on host.
ROOT = Path(__file__).resolve().parent

REGISTRY_PATH = ROOT / "registry" / "nodes.jsonl"
CANDIDATES_DIR = ROOT / "candidates"
ARBITRATION_DIR = ROOT / "arbitration"
SOURCES_DIR = ROOT / "sources"


def read_jsonl(path: Path) -> Iterator[dict]:
    """Yield one dict per line; skip blanks and comments. Missing file = empty."""
    if not path.exists():
        return
    with path.open() as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{i}: invalid JSON ({e})") from e


def write_jsonl(path: Path, records: Iterable[Any]) -> int:
    """Write records as JSONL. Returns count written. Overwrites existing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w") as f:
        for rec in records:
            if is_dataclass(rec):
                rec = asdict(rec)
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")
            n += 1
    return n
