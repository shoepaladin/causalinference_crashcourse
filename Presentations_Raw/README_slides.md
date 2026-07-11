# Building the pretty slide decks

This folder has a pipeline that turns the course notebooks into **polished,
self-contained reveal.js slides**, then exports each one to a **PDF** — that's
the artifact actually committed to `Updated_v2/`. It does *not* change any
slide content — only how the slides look and how they're packaged.

(GitHub can't render the multi-MB self-contained HTML deck inline in the repo
browser, but it does render PDFs inline and paginated, which is why PDF is
the shipped format. The HTML is still generated as a build step — see below —
but it's a local, gitignored intermediate, not committed.)

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

# JS side: reveal.js + MathJax (vendored, inlined) + playwright (PDF export)
npm install
npx playwright install chromium
```

Requires Python 3.9+ and Node.js.

## Build

```bash
# Rebuild every deck's PDF from its notebook (this is the standard process)
python build_pdfs.py

# Just one deck
python build_pdfs.py "1 Foundations 20230528 update.ipynb"

# List the source decks
python build_slides.py --list
```

Each run produces `Updated_v2/<name>.pdf` — commit that. It also leaves a
`Updated_v2/<name>.slides.html` behind (self-contained, opens in any browser
offline, supports speaker notes) — that file is gitignored, so it's fine to
keep locally for presenting but don't commit it. See `Updated_v2/README.md`
for the full three-step breakdown (`build_slides.py` → `export_pdfs.js` →
`check_overflow.js`) and how to run them individually.

## Customizing the look

Edit **`theme/custom.css`** — the variables at the top (`--ci-accent`,
`--ci-bg`, fonts, …) re-skin every deck at once. Re-run `build_pdfs.py` to
regenerate. The nbconvert template lives in `theme/index.html.j2`.

## How it works

`build_pdfs.py` runs three scripts in sequence:
1. **`build_slides.py`** normalizes malformed Markdown table separators in
   memory (the notebooks are never modified) so newer mistune renders the
   tables correctly, runs `nbconvert --to slides` with the custom `theme/`
   template and `--embed-images`, inlines the vendored reveal.js core, the
   notes plugin and MathJax, and base64-embeds every figure, writing the
   finished, self-contained deck to `Updated_v2/*.slides.html`.
2. **`export_pdfs.js`** prints that HTML to `Updated_v2/*.pdf` via
   Chromium/reveal.js's `?print-pdf` mode, one physical page per slide.
3. **`check_overflow.js`** flags any slide whose content is taller than one
   page, so it can be fixed (in the notebook, ideally) before committing.

## Notes

- `node_modules/`, `package-lock.json`, and `Updated_v2/*.slides.html` are
  git-ignored; they're build artifacts, not source.
- The source notebooks (`*.ipynb`) and the `Figures/` folder are untouched.
