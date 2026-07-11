#!/usr/bin/env python3
"""Rebuild deck PDFs straight from the source notebooks.

This is the standard way to refresh Presentations_Raw/Updated_v2/*.pdf from
now on. For each notebook it:

  1. renders it to a self-contained reveal.js HTML deck (build_slides.py),
  2. exports that HTML to a PDF, one physical page per slide, via Chromium's
     print pipeline (export_pdfs.js), and
  3. flags any slide whose content is still taller than one page
     (check_overflow.js) so it can be fixed before committing.

The HTML from step 1 is a local build intermediate, gitignored, not
committed — only the resulting PDF is. If a deck has a slide that doesn't
fit on one page, fix it in the notebook (preferred) or the built HTML, then
re-run this script until check_overflow.js reports clean.

One-time setup:
    pip install -r requirements-slides.txt
    npm install
    npx playwright install chromium

Usage:
    python build_pdfs.py                # rebuild every deck's PDF
    python build_pdfs.py "1 Foundations 20230528 update.ipynb"   # one deck
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "Updated_v2"


def main() -> int:
    decks = sys.argv[1:]

    # 1. notebook(s) -> self-contained HTML
    subprocess.run([sys.executable, "build_slides.py", *decks], cwd=HERE, check=True)

    html_files = (
        sorted(str(p) for p in OUT_DIR.glob("*.slides.html"))
        if not decks
        else [str(OUT_DIR / f"{Path(d).stem}.slides.html") for d in decks]
    )

    # 2. HTML -> PDF
    subprocess.run(["node", "export_pdfs.js", *html_files], cwd=HERE, check=True)

    # 3. flag any slide that still overflows a page (non-fatal, just a warning)
    overflow = subprocess.run(["node", "check_overflow.js", *html_files], cwd=HERE)
    if overflow.returncode != 0:
        print(
            "\n⚠ Some slides above overflow a page. Split or shrink them "
            "(preferably in the notebook) and re-run before committing.",
            file=sys.stderr,
        )

    print(
        "\nDone. Commit Updated_v2/*.pdf — the .slides.html files are a "
        "local build artifact (gitignored, not committed)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
