#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Julian Hsu <hsu.julian.econ@gmail.com>
# Source: https://github.com/shoepaladin/causalinference_crashcourse
# attribution-id: attr-45fd9566

"""Rebuild deck PDFs straight from the source notebooks.

This is the standard way to refresh Presentations_Raw/Updated_v2/*.pdf from
now on. For each notebook it:

  1. renders it to a self-contained reveal.js HTML deck (build_slides.py),
  2. exports that HTML to a PDF, one physical page per slide, via Chromium's
     print pipeline (export_pdfs.js),
  3. stamps authorship onto the fresh PDF — per-page footer, XMP and DocInfo
     (tools/stamp_attribution.py), and
  4. flags any slide whose content is still taller than one page
     (check_overflow.js) so it can be fixed before committing.

This is the only path that produces a PDF in this repo, which is what keeps
every shipped deck attributed. Step 3 writes in place: the file was created
seconds earlier by step 2, so there is no original to protect. It is
idempotent and refuses to stamp a PDF that already carries the marker, so
re-running is safe. Pass --no-stamp to skip it.

The per-slide footer visible on screen comes from theme/custom.css; step 3
adds the page numbering and the document metadata that CSS cannot reach.

The HTML from step 1 is a local build intermediate, gitignored, not
committed — only the resulting PDF is. If a deck has a slide that doesn't
fit on one page, fix it in the notebook (preferred) or the built HTML, then
re-run this script until check_overflow.js reports clean.

One-time setup:
    pip install -r requirements-slides.txt
    pip install -r ../tools/requirements-attribution.txt
    npm install
    npx playwright install chromium

Usage:
    python build_pdfs.py                # rebuild every deck's PDF
    python build_pdfs.py "1 Foundations 20230528 update.ipynb"   # one deck
    python build_pdfs.py --no-stamp     # rebuild without stamping
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "Updated_v2"


STAMPER = HERE.parent / "tools" / "stamp_attribution.py"


def stamp(pdfs: list[Path]) -> None:
    """Stamp authorship onto freshly built PDFs, in place.

    In place is deliberate here and nowhere else: these files were created by
    step 2 moments ago, so there is no original at risk. Run by hand, the
    stamper always writes to stamped/ instead.
    """
    for pdf in pdfs:
        if not pdf.exists():
            print(f"⚠ expected {pdf.name} but it was not built; not stamped",
                  file=sys.stderr)
            continue
        subprocess.run(
            [sys.executable, str(STAMPER), "--only", "pdf", "--in-place",
             "--allow-dirty", "--no-diff", "--path", str(pdf)],
            cwd=HERE.parent, check=True,
        )


def main() -> int:
    argv = sys.argv[1:]
    do_stamp = "--no-stamp" not in argv
    decks = [a for a in argv if a != "--no-stamp"]

    # 1. notebook(s) -> self-contained HTML
    subprocess.run([sys.executable, "build_slides.py", *decks], cwd=HERE, check=True)

    html_files = (
        sorted(str(p) for p in OUT_DIR.glob("*.slides.html"))
        if not decks
        else [str(OUT_DIR / f"{Path(d).stem}.slides.html") for d in decks]
    )

    # 2. HTML -> PDF
    subprocess.run(["node", "export_pdfs.js", *html_files], cwd=HERE, check=True)

    # 3. stamp authorship onto what step 2 just produced
    pdfs = [Path(h[: -len(".slides.html")] + ".pdf") for h in html_files]
    if do_stamp:
        stamp(pdfs)
    else:
        print("· Skipping attribution stamping (--no-stamp).", file=sys.stderr)

    # 4. flag any slide that still overflows a page (non-fatal, just a warning)
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
