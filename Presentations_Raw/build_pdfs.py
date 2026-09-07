#!/usr/bin/env python3
"""Rebuild deck PDFs straight from the source notebooks.

This is the standard way to refresh Presentations_Raw/Updated_v2/*.pdf. For
each notebook it:

  1. renders it to a self-contained reveal.js HTML deck (build_slides.py), and
  2. exports that HTML to a PDF, one physical page per slide, via Chromium's
     print pipeline, flagging any slide whose content is cut by a page
     boundary (export_pdfs.js).

The HTML from step 1 is a local build intermediate, gitignored, not
committed - only the resulting PDF is. A PDF whose content is unchanged is
left untouched on disk, so rebuilding everything doesn't dirty decks you
didn't edit.

If a slide is reported as CUT, fix it in the notebook (split the slide, or
trim a bullet) and re-run until the report is clean.

One-time setup:
    pip install -r requirements-slides.txt
    npm install
    npx playwright install chromium

Usage:
    python build_pdfs.py                # rebuild every deck's PDF
    python build_pdfs.py "1 Foundations 20230528 update.ipynb"   # one deck
    python build_pdfs.py --force        # ignore the up-to-date check
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Status lines use arrow/check glyphs; a cp1252 Windows console can't encode
# them. Fix it here for this process and for the child build_slides.py run.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - non-TTY / old Python
        pass
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "Updated_v2"

# A deck is rebuilt when its notebook or anything that shapes the output is
# newer than the PDF it produced.
BUILD_INPUTS = [HERE / "build_slides.py", HERE / "theme"]


def _newest(paths: list[Path]) -> float:
    stamps = [0.0]
    for p in paths:
        if p.is_dir():
            stamps += [f.stat().st_mtime for f in p.rglob("*") if f.is_file()]
        elif p.exists():
            stamps.append(p.stat().st_mtime)
    return max(stamps)


def is_stale(deck: str, tooling_mtime: float) -> bool:
    pdf = OUT_DIR / f"{Path(deck).stem}.pdf"
    if not pdf.exists():
        return True
    nb = HERE / deck
    return max(nb.stat().st_mtime, tooling_mtime) > pdf.stat().st_mtime


def main() -> int:
    args = sys.argv[1:]
    force = "--force" in args
    decks = [a for a in args if a != "--force"]

    if not decks:
        listed = subprocess.run(
            [sys.executable, "build_slides.py", "--list"],
            cwd=HERE, check=True, capture_output=True, text=True)
        decks = [d for d in listed.stdout.splitlines() if d.strip()]

    if not force:
        tooling = _newest(BUILD_INPUTS)
        fresh = [d for d in decks if not is_stale(d, tooling)]
        decks = [d for d in decks if is_stale(d, tooling)]
        for d in fresh:
            print(f"· Up to date, skipping: {d}")
        if not decks:
            print("\nEverything is up to date. Use --force to rebuild anyway.")
            return 0

    # 1. notebook(s) -> self-contained HTML
    subprocess.run([sys.executable, "build_slides.py", *decks], cwd=HERE, check=True)

    html_files = [str(OUT_DIR / f"{Path(d).stem}.slides.html") for d in decks]

    # 2. HTML -> PDF, with the page-boundary report
    export = subprocess.run(["node", "export_pdfs.js", *html_files], cwd=HERE)
    if export.returncode != 0:
        print(
            "\n⚠ Some slides above are cut by a page boundary. Split or shrink "
            "them (preferably in the notebook) and re-run before committing.",
            file=sys.stderr,
        )

    print(
        "\nDone. Commit Updated_v2/*.pdf — the .slides.html files are a "
        "local build artifact (gitignored, not committed)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
