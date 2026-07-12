# Updated_v2 — redesigned slide decks

This folder holds the **redesigned** versions of the causal inference decks,
shipped as **PDFs** — that's the only artifact committed here. GitHub renders
PDFs inline and paginated in the repo browser, and these files are well under
1.2 MB, so they preview instantly by clicking on them above.

(There used to be a same-named self-contained `.slides.html` reveal.js
version committed alongside each PDF. Those were 2.5–3.6 MB each — too big
for GitHub's file viewer to render — so they didn't actually solve the
"preview it on GitHub" problem they were meant to. They've been removed from
the repo; see below for how to regenerate one locally if you want the
interactive/speaker-notes version for presenting.)

The slide **content is identical** to the original notebooks — only the visual
design and the packaging changed.

| Deck | PDF |
|---|---|
| 1. Foundations | `1 Foundations 20230528 update.pdf` |
| 2. Causal Models | `2 Causal Models 20230530 update.pdf` |
| 3. Inference | `3 Inference 20230605 update.pdf` |
| 5. HTE Models (May) | `5 HTE Models 20230527 update.pdf` |
| 5. HTE Models (Jun) | `5 HTE Models 20230615 update.pdf` |
| 6. Panel Models (DiD, SC, SDID) | `6 Panel Models 20260703 update.pdf` |
| 7. Regression Discontinuity | `7 Regression Discontinuity 20260702 update.pdf` |
| 8. Surrogate Models | `8 Surrogate Models 20260707 update.pdf` |
| 9. Arguable Validation | `9 Arguable Validation 20230606 update.pdf` |
| 10. Conformal Inference | `10 Conformal Inference 20260704 update.pdf` |

---

## How to rebuild these PDFs

Everything needed lives one level up, in `Presentations_Raw/`. **This is the
standard process from now on** — any time a source notebook changes, rebuild
its PDF this way and commit the result. `.slides.html` files are a local
build intermediate (gitignored); don't commit them.

### 1. Install the tooling (once)

```bash
cd Presentations_Raw

# Python side: nbconvert / jupyter
pip install -r requirements-slides.txt

# JS side: reveal.js + MathJax (vendored, inlined into the HTML) + playwright
npm install
npx playwright install chromium
```

Requires **Python 3.9+** and **Node.js**.

### 2. Build

```bash
cd Presentations_Raw

# Rebuild every deck's PDF from its notebook
python build_pdfs.py

# ...or just one:
python build_pdfs.py "1 Foundations 20230528 update.ipynb"
```

`build_pdfs.py` runs the full pipeline for each notebook:

1. **`build_slides.py`** — renders the notebook to a self-contained reveal.js
   HTML deck in `Updated_v2/*.slides.html` (normalizes malformed Markdown
   table separators in memory, runs `jupyter nbconvert --to slides` with the
   custom template in `theme/`, then inlines reveal.js/MathJax and
   base64-embeds every figure). The source notebook is never modified.
2. **`export_pdfs.js`** — opens that HTML in Chromium via reveal.js's own
   `?print-pdf` mode and prints it to `Updated_v2/*.pdf`, one physical page
   per slide.
3. **`check_overflow.js`** — flags any slide whose content is taller than one
   page. Left unfixed, reveal.js silently grows that slide's page box and
   Chromium then breaks it at an arbitrary point when printed (no
   continuation heading, sometimes mid-sentence). If a slide is flagged, fix
   it in the notebook — either shrink the content or split it into two
   slides — and re-run `python build_pdfs.py` until it's clean.

Only commit the resulting `Updated_v2/*.pdf`. The `.slides.html` build
intermediate is gitignored — keep it locally if you want the
interactive/speaker-notes version for presenting (arrow keys to move, **Esc**
for the overview grid, **F** for fullscreen, **S** for speaker notes), but
don't commit it.

You can also run the three steps individually — useful when iterating on one
deck without re-exporting all seven:

```bash
python build_slides.py "1 Foundations 20230528 update.ipynb"
node export_pdfs.js "Updated_v2/1 Foundations 20230528 update.slides.html"
node check_overflow.js "Updated_v2/1 Foundations 20230528 update.slides.html"
```

### 3. Change the look

The whole design system is in **`Presentations_Raw/theme/custom.css`**. The
variables at the top re-skin every deck at once, e.g.:

```css
:root {
  --ci-accent:   #0e7490;   /* links, table headers, bullets, accent rule */
  --ci-accent-2: #0f766e;   /* headings                                   */
  --ci-bg:       #fbfcfe;   /* slide background                           */
  /* --ci-sans / --ci-serif: font stacks */
}
```

Edit, then re-run `python build_pdfs.py`. The nbconvert template itself is
`Presentations_Raw/theme/index.html.j2`.

### Files involved

```
Presentations_Raw/
├── build_pdfs.py               # the end-to-end pipeline: notebook → HTML → PDF
├── build_slides.py             # step 1: notebook → self-contained HTML
├── export_pdfs.js              # step 2: HTML → PDF (playwright, print-pdf mode)
├── check_overflow.js           # step 3: flags slides taller than one page
├── requirements-slides.txt     # Python deps
├── package.json                # reveal.js + mathjax (vendored) + playwright (dev)
├── theme/
│   ├── conf.json                # nbconvert template config (base = reveal)
│   ├── index.html.j2            # custom reveal template
│   └── custom.css               # the design system  ← edit this to re-skin
└── Updated_v2/                  # ← the committed PDFs (this folder);
                                  #   *.slides.html appears here too when you
                                  #   build locally, but it's gitignored
```
