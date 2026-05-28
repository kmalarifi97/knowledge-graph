"""Run the whole pipeline end-to-end inside the container.

Stages, in order:
  1. registry summary (smoke check)
  2. sources.logical    -> candidates/logical.jsonl
  3. sources.llm_extract -> candidates/llm.jsonl
  4. arbitration.arbitrate -> arbitration/arbitrated.jsonl, review.jsonl

Each stage is a real Python module run as a subprocess so its stdout is
preserved verbatim. If any stage exits non-zero, the pipeline halts and
returns that code.
"""
from __future__ import annotations

import subprocess
import sys


STAGES = [
    ("registry summary",    [sys.executable, "-m", "registry.registry"]),
    ("logical source",      [sys.executable, "-m", "sources.logical"]),
    ("llm source",          [sys.executable, "-m", "sources.llm_extract"]),
    ("arbitration",         [sys.executable, "-m", "arbitration.arbitrate"]),
]


def main() -> int:
    for label, cmd in STAGES:
        print(f"\n=== {label} ===")
        rc = subprocess.call(cmd)
        if rc != 0:
            print(f"\n!! {label} exited {rc}, halting pipeline", file=sys.stderr)
            return rc
    print("\n=== pipeline complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
