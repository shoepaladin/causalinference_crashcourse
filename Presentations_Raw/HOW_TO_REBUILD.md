# Rebuild the slides — one click

You edited a notebook in `Presentations_Raw/`. Here's how to turn that edit
back into the committed PDF deck, without remembering any commands.

## The one click

In File Explorer, open `Presentations_Raw/` and **double-click
`rebuild_slides.bat`**.

That's it. A console window opens, rebuilds **every** deck's PDF into
`Updated_v2/`, and waits for a keypress so you can read the output before it
closes.

The script is self-healing: on a fresh machine (or a fresh clone) it installs
whatever is missing before building —

| Step | What it checks | What it does if missing |
|---|---|---|
| 1 | Python `nbconvert` | `pip install "nbconvert>=7.0"` |
| 2 | `node_modules/` (reveal.js, MathJax, playwright) | `npm install` |
| 3 | headless Chromium | `npx playwright install chromium` |
| 4 | — | `python build_pdfs.py` |

The only things you must install by hand, once, are **Python 3.9+** and
**Node.js** — both need to be on your `PATH`.

### Rebuilding just one deck

Same script, with the notebook name as an argument. From PowerShell:

```powershell
cd "$HOME\OneDrive\Documents\GitHub\causalinference_crashcourse\Presentations_Raw"
.\rebuild_slides.bat "1 Foundations 20230528 update.ipynb"
```

A full rebuild of all decks takes a couple of minutes; a single deck takes
about ten seconds.

## What comes out

For each notebook, `Updated_v2/<same name>.pdf` — **this is the file to
commit.** One PDF page per slide.

You'll also see `Updated_v2/<same name>.slides.html` appear. That's the
interactive reveal.js version: fully self-contained, works offline, supports
speaker notes (press `S`). Nice for actually presenting. It is **gitignored on
purpose** — don't commit it.

## Reading the output

Near the end you'll see an overflow report per deck:

```
Updated_v2/1 Foundations 20230528 update.slides.html
  base page height: 783px, 31 slides
  OK - no overflowing slides
```

- `OK` — nothing to do.
- `FLAG ... overflow=+31px` — a **positive** overflow means that slide's
  content is taller than its page box, and Chromium will chop it at an
  arbitrary point. Fix it in the notebook (split the slide, or cut a bullet)
  and re-run.
- `FLAG ... overflow=-501px` — a **negative** number is a false alarm. It just
  means reveal.js gave that slide a 2- or 3-page box and the content doesn't
  fill the last page. Nothing is cut off; ignore it.

## Where things live

| Path | What it is |
|---|---|
| `Presentations_Raw/*.ipynb` | **the source of truth** — edit slide text here |
| `Presentations_Raw/Figures/*.png` | static images the slides reference; hand-made, nothing regenerates them |
| `Presentations_Raw/theme/custom.css` | the look — colors, fonts, tables, print rules |
| `Presentations_Raw/theme/index.html.j2` | the nbconvert slide template |
| `Presentations_Raw/Updated_v2/*.pdf` | the build output you commit |

To re-skin every deck at once, edit the CSS variables at the top of
`theme/custom.css` (`--ci-accent`, `--ci-bg`, fonts) and re-run the one click.

## Writing slides that render right

Two Markdown traps that have bitten this deck set:

1. **Blank line before a new paragraph that follows an indented bullet.**
   Without it, Markdown swallows the paragraph into the bullet above it.

   ```markdown
   1. Unconfoundedness assumption
       * AKA - there is no omitted variable bias
                                  <- this blank line is required
   Setup for an Example:
   * Observed outcome: ...
   ```

2. **Table separator rows need a trailing pipe-free cell for every column.**
   The build normalizes the malformed ones in memory, so the notebook itself
   is never rewritten — but keep them well-formed anyway:
   `|---|:---|:---|`.

## Troubleshooting

**`UnicodeEncodeError: 'charmap' codec can't encode character '\u25b8'`**
You ran `python build_pdfs.py` directly in a console stuck on cp1252. The
scripts now force UTF-8 on their own; if you see this on an old checkout,
`set PYTHONUTF8=1` first, or just use `rebuild_slides.bat`, which sets it.

**A deck reappears that you deleted.** `build_slides.py` has a hard-coded
`SOURCE_DECKS` list, and a full rebuild regenerates a PDF for every notebook
in it — including one whose PDF you deliberately removed from the repo. If
you retire a deck, delete its entry from `SOURCE_DECKS` too, or the next
rebuild brings it back. (`5 HTE Models 20230527 update` has already been
removed from that list for exactly this reason.)

**PDF has a blank page at the end.** Fixed — `theme/custom.css` now cancels
reveal.js's `page-break-after: always` on the final page. If it ever comes
back, that rule is the place to look.

## The manual, three-step version

`rebuild_slides.bat` is a wrapper around `python build_pdfs.py`, which runs:

1. `build_slides.py` — notebook → self-contained reveal.js HTML
2. `export_pdfs.js` — HTML → PDF via headless Chromium's `?print-pdf`
3. `check_overflow.js` — flags slides taller than one page

See `README_slides.md` and `Updated_v2/README.md` for the long-form
explanation of each stage.
