# Building the pretty slide decks

Julian Hsu <hsu.julian.econ@gmail.com> · Causal Inference Crash Course · https://github.com/shoepaladin/causalinference_crashcourse  
attribution-id: `attr-3ea5ec9b`

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

## Exporting to PDF

`build_pdfs.py` is the only way a PDF gets made in this repo. There used to be
a second, parallel exporter (`build_pdf.py`, Python + Playwright) that did the
same job as `export_pdfs.js`; it has been removed so there is one path to keep
working and one place where attribution is applied.

```bash
pip install playwright
playwright install chromium   # skip if Chromium is already vendored/available

# Rebuild every deck's PDF, stamped
python build_pdfs.py

# Rebuild a single deck
python build_pdfs.py "8 Surrogate Models 20260707 update.ipynb"

# Rebuild without stamping (rarely what you want)
python build_pdfs.py --no-stamp
```

Every PDF it produces is stamped by `../tools/stamp_attribution.py`: a per-page
footer carrying name, project, source URL and page number, plus XMP and DocInfo
metadata (`/Author`, `/Title`, `/Subject`, `/Keywords`). That step writes in
place — the file was created seconds earlier by the export — and is idempotent,
so re-running is safe.

The on-screen footer in `theme/custom.css` is deliberately suppressed during
PDF export; the stamper owns the footer in every PDF so that built and
hand-stamped PDFs match, and so continuation pages of a tall slide get one too.

## Customizing the look

Edit **`theme/custom.css`** — the variables at the top (`--ci-accent`,
`--ci-bg`, fonts, …) re-skin every deck at once. Re-run `build_pdfs.py` to
regenerate. The nbconvert template lives in `theme/index.html.j2`.

## How it works

`build_pdfs.py` runs four steps in sequence:
1. **`build_slides.py`** normalizes malformed Markdown table separators in
   memory (the notebooks are never modified) so newer mistune renders the
   tables correctly, runs `nbconvert --to slides` with the custom `theme/`
   template and `--embed-images`, inlines the vendored reveal.js core, the
   notes plugin and MathJax, and base64-embeds every figure, writing the
   finished, self-contained deck to `Updated_v2/*.slides.html`.
2. **`export_pdfs.js`** prints that HTML to `Updated_v2/*.pdf` via
   Chromium/reveal.js's `?print-pdf` mode, one physical page per slide.
3. **`../tools/stamp_attribution.py`** stamps the fresh PDF in place: per-page
   footer plus XMP/DocInfo metadata. Skip with `--no-stamp`.
4. **`check_overflow.js`** flags any slide whose content is taller than one
   page, so it can be fixed (in the notebook, ideally) before committing.

## Notes

- `node_modules/`, `package-lock.json`, and `Updated_v2/*.slides.html` are
  git-ignored; they're build artifacts, not source.
- The source notebooks (`*.ipynb`) and the `Figures/` folder are untouched.
