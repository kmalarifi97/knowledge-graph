#!/usr/bin/env python3
"""Rasterize a lesson's PDF pages to PNGs for vision extraction.

The library structure.json holds, per lesson, a (source_file, start_page,
end_page) in PDF page numbers. PDFs are gitignored and live in a sibling
worktree; this script resolves the real PDF and renders only the pages a
lesson claims, into a per-book cache.

Usage:
  rasterize.py --book library/math/trc1-sm1-math1.1 --lesson 1-1
  rasterize.py --book library/math/trc1-sm1-math1.1 --lesson 1-1 --dpi 150

Prints, one per line, the absolute path of each rendered PNG in page order.
"""
import argparse
import json
import os
import sys

import fitz  # PyMuPDF

# PDFs are gitignored in this worktree; they exist in this sibling worktree.
PDF_ROOTS = [
    ".",  # if PDFs are ever present locally, prefer them
    "/Users/khalid-dev/knowledge-graph/.claude/worktrees/quizzical-newton-a13040",
]

REPO = "/Users/khalid-dev/knowledge-graph/.claude/worktrees/condescending-wilbur-71d863"


def find_lesson(structure, lesson_id):
    for ch in structure.get("chapters", []):
        for ls in ch.get("lessons", []):
            if ls["id"] == lesson_id:
                # default source_file to chapter's, then book single-file
                src = ls.get("source_file") or ch.get("source_file")
                return ls, ch, src
    # earth-science style: units -> chapters -> lessons
    for unit in structure.get("units", []):
        for ch in unit.get("chapters", []):
            for ls in ch.get("lessons", []):
                if ls["id"] == lesson_id:
                    src = ls.get("source_file") or ch.get("source_file")
                    return ls, ch, src
    return None, None, None


def resolve_pdf(book_rel, src_file):
    """book_rel like 'library/math/trc1-sm1-math1.1'."""
    if not src_file:
        # single-file book: textbook.pdf
        src_file = "textbook.pdf"
    for root in PDF_ROOTS:
        cand = os.path.join(root, book_rel, src_file)
        if os.path.isfile(cand):
            return os.path.abspath(cand)
    raise FileNotFoundError(
        f"PDF not found for {book_rel}/{src_file} in roots {PDF_ROOTS}"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True, help="repo-relative book dir")
    ap.add_argument("--lesson", required=True)
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--out", default=os.path.join(REPO, "extraction/_pagecache"))
    args = ap.parse_args()

    book_rel = args.book.rstrip("/")
    book_id = os.path.basename(book_rel)
    structure_path = os.path.join(REPO, book_rel, "structure.json")
    structure = json.load(open(structure_path, encoding="utf-8"))

    ls, ch, src = find_lesson(structure, args.lesson)
    if ls is None:
        sys.exit(f"lesson {args.lesson} not found in {structure_path}")

    pdf_path = resolve_pdf(book_rel, src)
    start, end = ls["start_page"], ls["end_page"]

    out_dir = os.path.join(args.out, book_id)
    os.makedirs(out_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    zoom = args.dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    paths = []
    for pno in range(start, end + 1):
        idx = pno - 1  # PDF page numbers are 1-indexed; fitz is 0-indexed
        if idx < 0 or idx >= doc.page_count:
            sys.stderr.write(f"WARN page {pno} out of range (doc has {doc.page_count})\n")
            continue
        page = doc.load_page(idx)
        pix = page.get_pixmap(matrix=mat)
        vol_tag = os.path.splitext(os.path.basename(pdf_path))[0]
        fp = os.path.join(out_dir, f"{args.lesson}_{vol_tag}_p{pno:03d}.png")
        pix.save(fp)
        paths.append(os.path.abspath(fp))
    doc.close()

    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
