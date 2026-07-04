# Updated_v2 — redesigned slide decks

This folder holds the **redesigned, self-contained** versions of the causal
inference decks. Each `*.slides.html` is a single file that:

- opens in any browser with **no internet connection** (reveal.js, MathJax and
  every figure are inlined), and
- is easy to email or drop on a static host.

The slide **content is identical** to the original notebooks — only the visual
design and the packaging changed.

| Deck | File |
|---|---|
| 1. Foundations | `1 Foundations 20230528 update.slides.html` |
| 2. Causal Models | `2 Causal Models 20230530 update.slides.html` |
| 3. Inference | `3 Inference 20230605 update.slides.html` |
| 5. HTE Models (May) | `5 HTE Models 20230527 update.slides.html` |
| 5. HTE Models (Jun) | `5 HTE Models 20230615 update.slides.html` |
| 6. Panel Models (DiD, SC, SDID) | `6 Panel Models 20260703 update.slides.html` |
| 7. Regression Discontinuity | `7 Regression Discontinuity 20260702 update.slides.html` |
| 9. Arguable Validation | `9 Arguable Validation 20230606 update.slides.html` |

Navigating a deck: **arrow keys** to move, **Esc** for the overview grid,
**F** for fullscreen, **S** for speaker notes.

---

## How to recreate these slides

Everything needed lives one level up, in `Presentations_Raw/`.

### 1. Install the tooling (once)

```bash
cd Presentations_Raw

# Python side: nbconvert / jupyter
pip install -r requirements-slides.txt

# JS assets (reveal.js + MathJax) — the build fetches these automatically,
# but you can pre-fetch them:
npm install
```

Requires **Python 3.9+** and **Node.js** (npm is used only to vendor the
reveal.js and MathJax files that get inlined into each deck).

### 2. Build

```bash
cd Presentations_Raw

# Rebuild every deck into Updated_v2/
python build_slides.py

# ...or just one:
python build_slides.py "1 Foundations 20230528 update.ipynb"

# List the source decks:
python build_slides.py --list
```

Each run overwrites `Updated_v2/<name>.slides.html`.

### 3. What the build does

`build_slides.py`:

1. **normalizes malformed Markdown table separators in memory** (e.g.
   `|---|---|---` → `|---|---|---|`) so newer `mistune` renders the tables
   correctly — the source notebooks are never modified;
2. runs `jupyter nbconvert --to slides` with the custom template in
   `Presentations_Raw/theme/` and `--embed-images`;
3. **inlines** the vendored reveal.js core, the notes plugin and MathJax, and
   base64-embeds every figure; then
4. writes the finished, self-contained deck here to `Updated_v2/`.

### 4. Change the look

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

Edit, then re-run `python build_slides.py`. The nbconvert template itself is
`Presentations_Raw/theme/index.html.j2`.

### Files involved

```
Presentations_Raw/
├── build_slides.py            # the build script
├── requirements-slides.txt    # Python deps
├── package.json               # reveal.js + mathjax (vendored, inlined)
├── theme/
│   ├── conf.json              # nbconvert template config (base = reveal)
│   ├── index.html.j2          # custom reveal template
│   └── custom.css             # the design system  ← edit this to re-skin
└── Updated_v2/                # ← the rendered decks (this folder)
```
