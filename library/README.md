# library/

Catalog of Saudi MoE **"Pathways System" (نظام المسارات)** secondary-education textbooks downloaded from [`iencontent.ien.edu.sa/books/`](https://iencontent.ien.edu.sa/books/). Each book is a folder containing the PDF(s) plus a JSON page-map of its chapters and lessons.

## Layout

```
library/
├── registry.json             ← master index over every book in this library
├── README.md                 ← this file
│
├── chemistry/                ← 5 books
├── math/                     ← 5 books
├── physics/                  ← 4 books (incl. one already hand-indexed)
├── earth-science/            ← 1 book
├── reference/                ← non-textbook references (periodic table)
└── _duplicates/              ← byte-identical extra files, kept for audit (see _duplicates/README.md)
```

## Folder naming

```
{subject}/{trc}-{sm}-{code}[-{track}]
```

| Token | Meaning |
|---|---|
| `subject` | `chemistry`, `math`, `physics`, `earth-science` |
| `trc1`/`trc2`/`trc3` | Track / year: 1st year (shared), 2nd year, 3rd year |
| `sm1`/`sm2`/`sm3` | Semester within the year |
| `code` | Original IEN book code: `chmi2.1`, `math1.3`, `phys1`, `ess`, … |
| `track` (optional) | `cse` or `gnrl` — present **only** when the CSE and GNRL editions diverge in content. When they're byte-identical, the folder is unsuffixed. |

Examples:
- `chemistry/trc1-sm1-chmi1/` — year 1, single track (no CSE/GNRL split at year 1)
- `chemistry/trc2-sm1-chmi2.1/` — year 2 sem 1, CSE+GNRL share the same PDF
- `chemistry/trc3-sm1-chmi3-cse/` and `chemistry/trc3-sm1-chmi3-gnrl/` — year 3 chemistry: the two tracks have different textbook content, so they live in separate folders

## Per-book artifacts

Every book folder contains:

| File | What it is |
|---|---|
| `textbook.pdf` _or_ `volume-1.pdf` + `volume-2.pdf` | The actual book. Multi-volume books split chapters across two PDFs. |
| `workbook.pdf` _(optional)_ | The "A" supplement / activity book where one exists |
| `meta.json` | Registry-level info: original IEN filenames, md5s, source URLs, file sizes, PDF metadata, page count |
| `structure.json` | **The page-map.** Chapter & lesson titles (Arabic), start/end pages, appendices. See [Schema](#structurejson-schema) below. |
| `toc-pages.txt` | `pdftotext -layout` output of pages 1–12 (Arabic often mangled — kept as fallback) |
| `toc-pages-fitz.txt` | PyMuPDF text extraction of pages 1–12 |
| `toc-render-p*.png` | Rendered images of likely TOC pages (Arabic renders correctly here) |

## `structure.json` schema

```jsonc
{
  "book": {
    "title_ar": "الكيمياء 1",
    "title_en": "Chemistry 1",                            // optional
    "edition": "1447H / 2025M (نظام المسارات)",
    "publisher": "وزارة التعليم - المملكة العربية السعودية",
    "total_pdf_pages": 198,
    "page_offset": 0,                                     // PDF page == printed page in this series
    "notes": "...",                                       // pagination quirks, multi-volume notes
    "volumes": [                                          // only for multi-volume books
      { "file": "volume-1.pdf", "page_count": 249 },
      { "file": "volume-2.pdf", "page_count": 325 }
    ]
  },
  "chapters": [
    {
      "id": 1,
      "title_ar": "...",
      "title_en": "...",                                  // optional
      "start_page": 12,
      "end_page": 41,
      "source_file": "volume-1.pdf",                      // only for multi-volume; page numbers are per-volume
      "lessons": [
        { "id": "1-1", "title_ar": "...", "start_page": 13, "end_page": 21 }
      ]
    }
  ],
  "appendices": [
    { "id": "glossary", "title_ar": "المصطلحات", "start_page": 240, "end_page": 247 }
  ],
  "confidence_notes": [                                   // present only when the agent flagged uncertainties
    "Lesson 5-3 title may be 'دوال المقلوب' rather than 'دوال الطلوب' (OCR-ambiguous diacritic)"
  ]
}
```

**Key invariants:**

- `start_page` / `end_page` are **PDF page numbers** (1-indexed), which equal printed page numbers for this series (`page_offset: 0`).
- For multi-volume books, page numbers **reset per volume**. Each chapter carries a `source_file` and its page range is scoped to that file.
- For lesson IDs, math books may extend with suffixes like `1-2-explore`, `1-2-extend`, `-0` (intro) to mark non-numbered sections.
- Earth-science books may have `units[]` above `chapters[]` (Unit → Chapter → Lesson) — only present when the book is structured that way.
- `structure.json` is a **map over** the PDF — it gives you where things are and what's there, but does not replace the PDF for actual content.

## `registry.json` (root)

The top-level `registry.json` is one row per book with:

- folder path
- subject / trc / sm / code / track
- list of `files` (md5, source IEN filename, source URL, size)
- `page_count`, `pdf_metadata`
- `chapter_count`, `lesson_count`, `appendix_count` (summary from `structure.json`)
- `title_ar`, `title_en`
- `confidence_note_count` (≥ 1 means the structure has flagged uncertainties)

And aggregates under `totals`.

## Provenance

- Source: `https://iencontent.ien.edu.sa/books/{filename}.pdf`
- All books are the **1447H / 2025M** edition of the Saudi MoE pathways system.
- Bookkeeping: 41 PDFs downloaded → 30 unique by md5 → 14 conceptual books (some books bundle two volumes + a workbook). The 11 byte-identical duplicate downloads (same content served under different track URLs or UUID prefixes) are in `_duplicates/`.

## What this catalog does *not* (yet) contain

- Lesson summaries, learning objectives, or key-term lists — that needs a per-lesson reading pass. See `physics/trc2-sm3-phys2/structure.json` for the format such enrichment would take (hand-crafted, reused from `/Users/khalid-dev/physics-E2-library`).
- Concept slugs / video links — only the PHYS2 enriched version (from physics-E2-library) has those.

## Quick stats

| | Count |
|---|---|
| Unique books | **14** |
| Total chapters | **120** |
| Total lessons | **563** |
| Total appendices | **52** |
| Quarantined byte-duplicate PDFs | 11 |
