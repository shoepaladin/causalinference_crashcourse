#!/usr/bin/env python3
"""Export the self-contained reveal.js decks in Updated_v2/ to PDF.

Renders each ``Updated_v2/<name>.slides.html`` with headless Chromium in
reveal.js's built-in ``?print-pdf`` mode (one slide per page, including
overflow continuation pages for text-heavy slides) and writes
``Updated_v2/<name>.pdf`` alongside it. Requires ``build_slides.py`` to have
been run first, and Playwright with the Chromium browser installed:

    pip install playwright
    playwright install chromium

Usage:
    python build_pdf.py                # export every deck in Updated_v2/
    python build_pdf.py "8 Surrogate Models 20260707 update.ipynb"
    python build_pdf.py --list
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "Updated_v2"

sys.path.insert(0, str(HERE))
from build_slides import SOURCE_DECKS  # noqa: E402

# The width/height reveal.js is initialized with in theme/index.html.j2;
# print-pdf mode lays out each slide at exactly this pixel size.
SLIDE_WIDTH, SLIDE_HEIGHT = 1150, 740


def _chromium_launch_kwargs() -> dict:
    """Point at a pre-vendored Chromium if one is available (e.g. the
    Claude Code sandbox's /opt/pw-browsers/chromium) so this doesn't require
    a `playwright install` download; otherwise let Playwright pick its own."""
    import os
    candidate = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")) / "chromium"
    return {"executable_path": str(candidate)} if candidate.exists() else {}


async def export_pdf(html_path: Path, pdf_path: Path) -> None:
    from playwright.async_api import async_playwright

    url = html_path.as_uri() + "?print-pdf"
    async with async_playwright() as p:
        browser = await p.chromium.launch(**_chromium_launch_kwargs())
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(4000)  # let MathJax typeset + reveal.js apply print layout
        await page.pdf(
            path=str(pdf_path),
            width=f"{SLIDE_WIDTH}px",
            height=f"{SLIDE_HEIGHT}px",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        await browser.close()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("decks", nargs="*", help="specific notebook(s) to export (default: all)")
    ap.add_argument("--list", action="store_true", help="list source decks and exit")
    args = ap.parse_args()

    if args.list:
        for d in SOURCE_DECKS:
            print(d)
        return 0

    decks = args.decks or SOURCE_DECKS
    for stem_nb in decks:
        html_path = OUT_DIR / f"{Path(stem_nb).stem}.slides.html"
        if not html_path.exists():
            print(f"Missing {html_path.relative_to(HERE)} — run build_slides.py first.",
                  file=sys.stderr)
            return 1
        pdf_path = OUT_DIR / f"{Path(stem_nb).stem}.pdf"
        print(f"▸ Exporting: {html_path.name}")
        asyncio.run(export_pdf(html_path, pdf_path))
        print(f"  → {pdf_path.relative_to(HERE)}  ({pdf_path.stat().st_size / 1e6:.1f} MB)")

    print(f"\nDone. PDFs written to {OUT_DIR.relative_to(HERE.parent)}/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
