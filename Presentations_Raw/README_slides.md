# Building the pretty slide decks

This folder now has a redesigned pipeline that turns the course notebooks into
**polished, self-contained reveal.js slides**. It does *not* change any slide
content — only how the slides look and how the HTML is packaged.

The original `*.slides.html` exports are left in place so you can compare them
against the new ones. The redesigned decks are written to **`Updated_v2/`**.

## What changed vs. the old `jupyter nbconvert --to slides`

| | Old one-liner | New `build_slides.py` |
|---|---|---|
| Theme | default `simple` reveal theme | custom design system (`theme/custom.css`) |
| Typography | small, cramped | larger, readable sans; clean spacing |
| Headings | plain black, ALL-CAPS-ish | teal with an accent underline |
| Tables | unstyled | styled header, zebra rows, rounded |
| Figures | raw | framed, centered, drop shadow |
| Title slide | a plain slide | centered hero slide |
| Assets | CDN-linked (needs internet) | **inlined / base64 — one offline file** |
| Math | MathJax 2 (CDN) | MathJax 3 (inlined, SVG) |

## One-time setup

```bash
# Python side (nbconvert / jupyter)
pip install -r requirements-slides.txt

# JS assets (reveal.js + MathJax) are fetched automatically by the build,
# but you can pre-fetch them with:
npm install
```

Requires Python 3.9+ and Node.js (for `npm`, used only to vendor the reveal.js
and MathJax files that get inlined into each deck).

## Build

```bash
# Build every deck into Updated_v2/
python build_slides.py

# Build a single deck
python build_slides.py "1 Foundations 20230528 update.ipynb"

# List the source decks
python build_slides.py --list
```

Each run produces a single `Updated_v2/<name>.slides.html` that opens in any
browser with no internet connection and is small enough to email or drop on a
static host.

## Exporting to PDF

```bash
pip install playwright
playwright install chromium   # skip if Chromium is already vendored/available

# Export every deck in Updated_v2/ to a matching Updated_v2/<name>.pdf
python build_pdf.py

# Export a single deck
python build_pdf.py "8 Surrogate Models 20260707 update.ipynb"
```

`build_pdf.py` renders each `Updated_v2/<name>.slides.html` with headless
Chromium in reveal.js's built-in `?print-pdf` mode — one slide per page,
including continuation pages where a slide's content overflows the fixed
1150×740 canvas. Run `build_slides.py` first; the PDF export reads its output.

## Customizing the look

Edit **`theme/custom.css`** — the variables at the top (`--ci-accent`,
`--ci-bg`, fonts, …) re-skin every deck at once. Re-run `build_slides.py` to
regenerate. The nbconvert template lives in `theme/index.html.j2`.

## How it works

`build_slides.py`:
1. normalizes malformed Markdown table separators in memory (the notebooks are
   never modified) so newer mistune renders the tables correctly,
2. runs `nbconvert --to slides` with the custom `theme/` template and
   `--embed-images`,
3. inlines the vendored reveal.js core, the notes plugin and MathJax, and
   base64-embeds every figure, then
4. writes the finished, self-contained deck to `Updated_v2/`.

## Notes

- `node_modules/` and `package-lock.json` are git-ignored; they are only build
  inputs.
- The source notebooks (`*.ipynb`), the `Figures/` folder, and the legacy
  `*.slides.html` files are untouched.
