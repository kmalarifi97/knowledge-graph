#!/usr/bin/env python3
"""Validate one or more lesson JSON files against lesson_pages.schema.json.

Exit non-zero if any file fails. Prints a concise per-file report.

Usage:
  validate.py path/to/1-1.json [more.json ...]
  validate.py --all library/math/trc1-sm1-math1.1/lesson_pages
"""
import argparse
import glob
import json
import os
import sys

import jsonschema

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lesson_pages.schema.json")


def collect(args):
    files = []
    for p in args.paths:
        if os.path.isdir(p):
            files += sorted(glob.glob(os.path.join(p, "*.json")))
        else:
            files.append(p)
    if args.all:
        files += sorted(glob.glob(os.path.join(args.all, "*.json")))
    # skip schema/example artifacts
    return [f for f in files if not os.path.basename(f).startswith(("lesson_pages.schema", "_"))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--all", help="validate every *.json in this dir")
    args = ap.parse_args()

    schema = json.load(open(SCHEMA_PATH, encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    files = collect(args)
    if not files:
        sys.exit("no files to validate")

    n_ok = 0
    n_bad = 0
    for f in files:
        try:
            data = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            print(f"FAIL {f}: not valid JSON: {e}")
            n_bad += 1
            continue
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            n_bad += 1
            print(f"FAIL {f}: {len(errors)} error(s)")
            for e in errors[:8]:
                loc = "/".join(str(x) for x in e.absolute_path)
                print(f"   - at [{loc}]: {e.message[:200]}")
        else:
            n_ok += 1
            # quick stats
            npages = len(data.get("pages", []))
            nq = sum(
                1
                for pg in data.get("pages", [])
                for b in pg.get("blocks", [])
                if b.get("type") == "question"
            ) + sum(
                len(b.get("questions", []))
                for pg in data.get("pages", [])
                for b in pg.get("blocks", [])
                if b.get("type") == "question_set"
            )
            print(f"OK   {os.path.basename(f)}: {npages} pages, {nq} questions")

    print(f"\n{n_ok} ok, {n_bad} failed")
    sys.exit(1 if n_bad else 0)


if __name__ == "__main__":
    main()
