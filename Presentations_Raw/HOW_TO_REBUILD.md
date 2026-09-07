# Rebuild the slides — one click

You edited a notebook in `Presentations_Raw/`. Here's how to turn that edit
back into the committed PDF deck, without remembering any commands.

## The one click

In File Explorer, open `Presentations_Raw/` and **double-click
`rebuild_slides.bat`**.

A console window opens, rebuilds any deck whose notebook is newer than its
PDF, and waits for a keypress so you can read the report before it closes.

The script is self-healing: on a fresh machine (or a fresh clone) it installs
whatever is missing before building —

| Step | What it checks | What it does if missing |
|---|---|---|
| 1 | Python `nbconvert` | `pip install "nbconvert>=7.0"` |
| 2 | `node_modules/` (reveal.js, MathJax, playwright) | `npm install` |
| 3 | headless Chromium (asks playwright where its binary is) | `npx playwright install chromium` |
| 4 | — | `python build_pdfs.py` |

The only things you must install by hand, once, are **Python 3.9+** and
**Node.js** — both need to be on your `PATH`.

### Rebuilding one deck, or everything

Decks whose PDF is already newer than the notebook (and newer than
`build_slides.py` and `theme/`) are skipped, so re-running costs nothing:

```
· Up to date, skipping: 2 Causal Models 20230530 update.ipynb
```

To build a single deck, or to force a full rebuild, pass arguments straight
through. From PowerShell:

```powershell
cd "$HOME\OneDrive\Documents\GitHub\causalinference_crashcourse\Presentations_Raw"
.\rebuild_slides.bat "1 Foundations 20230528 update.ipynb"
.\rebuild_slides.bat --force
```

A full forced rebuild of all nine decks takes about 80 seconds; a single deck
takes about ten.

## What comes out

For each notebook, `Updated_v2/<same name>.pdf` — **this is the file to
commit.** One PDF page per slide.

A deck whose content didn't change is reported as `unchanged` and its file is
**not rewritten**, so a full rebuild doesn't leave you with nine modified PDFs
in `git status` when you only edited one. (Chromium stamps a fresh timestamp
into every export; the exporter compares with those stripped.)

You'll also see `Updated_v2/<same name>.slides.html` appear. That's the
interactive reveal.js version: self-contained, works offline, supports speaker
notes (press `S`). Nice for actually presenting. It is **gitignored on
purpose** — don't commit it.

## Reading the report

### `CUT` — a slide is being sliced

```
  CUT  slide 4 "Hypothesis testing and confidence intervals" (spans 2 pages)
         sliced at page 1 boundary: <LI> "This is useful because now we can model the variation i"
```

This is the one that matters. reveal.js quietly grows a tall slide's page box
to 2 or 3 pages, and Chromium then cuts whatever element happens to straddle
the break — mid-sentence, with no continuation heading. The report names the
slide **and the element being sliced**, so you know exactly what to shorten.

Fix it in the notebook — trim a bullet, or split the slide in two — and
re-run. A slide that spans 2 pages is *fine* as long as nothing straddles the
boundary; it's the slicing that's the defect, not the length.

> **Note:** this replaces an older `check_overflow.js` that measured overflow
> against the *grown* box rather than one physical page. That made genuinely
> chopped slides report a large negative "overflow" and read as safe. If you
> remember being told to ignore negative numbers — that advice was wrong, and
> the ~20 slides it waved through are the `CUT` lines you now see.

### `⚠ ... will be absorbed into the bullet above it`

```
  ⚠ 5 HTE Models 20230527 update.ipynb cell 33: this line will be absorbed
    into the bullet above it:
      'availability'
```

A Markdown trap: a non-blank, unindented line placed directly under an
*indented* bullet gets folded into that bullet instead of starting a new
paragraph. Easy to create by de-indenting a lead-in line, and invisible in the
notebook source. Add a blank line before it:

```markdown
1. Unconfoundedness assumption
    * AKA - there is no omitted variable bias
                               <- this blank line is required
Setup for an Example:
* Observed outcome: ...
```

The build only warns; it never rewrites your text.

## Where things live

| Path | What it is |
|---|---|
| `Presentations_Raw/*.ipynb` | **the source of truth** — edit slide text here |
| `Presentations_Raw/Figures/*.png` | static images the slides reference; hand-made, nothing regenerates them |
| `Presentations_Raw/theme/custom.css` | the look — colors, fonts, tables, print rules |
| `Presentations_Raw/theme/index.html.j2` | the nbconvert slide template |
| `Presentations_Raw/Updated_v2/*.pdf` | the build output you commit |

To re-skin every deck at once, edit the CSS variables at the top of
`theme/custom.css` (`--ci-accent`, `--ci-bg`, fonts) and re-run. Touching
`theme/` or `build_slides.py` makes every deck stale, so the next run rebuilds
them all.

## Adding or retiring a deck

`build_slides.py` has a `SOURCE_DECKS` list — the decks a no-argument build
covers. Add a notebook there when you write one. When you retire a deck,
delete its entry too, or every full rebuild will regenerate the PDF you just
deleted. It's a default set, not an allow-list: naming any notebook on the
command line still builds it.

## Troubleshooting

**`UnicodeEncodeError: 'charmap' codec can't encode character '\u25b8'`**
An old checkout, run in a console stuck on cp1252. The scripts now force UTF-8
themselves; `rebuild_slides.bat` also sets `PYTHONUTF8=1`.

**PDF has a blank page at the end.** Fixed — `theme/custom.css` cancels
reveal.js's `page-break-after: always` on the final page. That rule keys off
`.pdf-page:last-child`, and the exporter prints a `NOTE` if anything ever
starts following the last page, which would silently break it.

**Do I need to be online?** Only for the one-time setup (`pip install`,
`npm install`, `playwright install chromium`). After that the build makes zero
network requests, and the decks it produces are self-contained — reveal.js,
MathJax and every figure are inlined, so they present offline too.

**"Executable doesn't exist" from playwright.** The Chromium revision moved
when the `playwright` package was upgraded. `npx playwright install chromium`,
or just re-run the batch file — its check asks playwright for the real path
rather than guessing at a folder name.

## The manual version

`rebuild_slides.bat` wraps `python build_pdfs.py`, which runs:

1. `build_slides.py` — notebook → self-contained reveal.js HTML
2. `export_pdfs.js` — HTML → PDF via headless Chromium's `?print-pdf`, plus
   the page-boundary report

See `README_slides.md` and `Updated_v2/README.md` for the long-form
explanation of each stage.
