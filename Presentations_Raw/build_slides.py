#!/usr/bin/env python3
"""Build pretty, self-contained reveal.js slides from the course notebooks.

This replaces the old one-liner in ``NotebookstoHTML``. For each source
notebook it:

  1. runs ``jupyter nbconvert --to slides`` with the custom template in
     ``theme/`` (see theme/custom.css for the design system),
  2. inlines the reveal.js core, the notes plugin and MathJax 3 (vendored from
     npm, since the CDNs are blocked in some environments), and
  3. base64-embeds every figure,

so each output file in ``rendered/`` is a single, offline-capable HTML deck
that is easy to email or host. The original ``*.slides.html`` files and all
notebooks are left untouched.

Usage:
    python build_slides.py                # build every deck
    python build_slides.py "1 Foundations 20230528 update.ipynb"   # one deck
    python build_slides.py --list         # list source decks and exit
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
THEME_DIR = HERE / "theme"
OUT_DIR = HERE / "Updated_v2"
FIG_DIR = HERE / "Figures"
NODE_MODULES = HERE / "node_modules"

# Source decks that carry real slide metadata (excludes the simulation helper
# notebook, which is a data-generation script with no slideshow structure).
SOURCE_DECKS = [
    "1 Foundations 20230528 update.ipynb",
    "2 Causal Models 20230530 update.ipynb",
    "3 Inference 20230605 update.ipynb",
    "5 HTE Models 20230527 update.ipynb",
    "5 HTE Models 20230615 update.ipynb",
    "9 Arguable Validation 20230606 update.ipynb",
    "7 Regression Discontinuity 20260702 update.ipynb",
]


# --------------------------------------------------------------------------- #
# Vendored assets (reveal.js + mathjax), fetched once via npm.
# --------------------------------------------------------------------------- #
def ensure_vendor() -> dict[str, str]:
    """Make sure reveal.js + mathjax are installed locally; return their text."""
    reveal_css = NODE_MODULES / "reveal.js" / "dist" / "reveal.css"
    if not reveal_css.exists():
        print("· Installing vendored assets (reveal.js, mathjax) via npm …")
        subprocess.run(["npm", "install", "--silent", "--no-audit", "--no-fund"],
                       cwd=HERE, check=True)

    def rd(rel: str) -> str:
        return (NODE_MODULES / rel).read_text(encoding="utf-8", errors="replace")

    return {
        "reset_css": rd("reveal.js/dist/reset.css"),
        "reveal_css": rd("reveal.js/dist/reveal.css"),
        "theme_css": rd("reveal.js/dist/theme/white.css"),
        "reveal_js": rd("reveal.js/dist/reveal.js"),
        "notes_js": rd("reveal.js/plugin/notes/notes.js"),
        "mathjax_js": rd("mathjax/es5/tex-mml-svg.js"),
    }


# --------------------------------------------------------------------------- #
# nbconvert
# --------------------------------------------------------------------------- #
# Matches a GitHub-flavoured-markdown table separator row, e.g. "|---|:--:|--|".
_TABLE_SEP = re.compile(r'^\s*\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)+\|?\s*$')


def normalize_markdown(text: str) -> str:
    """Repair malformed table separators (missing leading/trailing pipe).

    Newer mistune (nbconvert 7) is stricter than the parser that produced the
    original decks: a separator like ``|---|---|---`` (no trailing pipe) makes it
    render only a single-row table. We fix such rows *in memory* so the tables
    display as the author intended — the notebooks themselves are never changed.
    """
    out = []
    for line in text.splitlines(keepends=False):
        if _TABLE_SEP.match(line) and line.count("|") >= 2:
            core = line.strip()
            if not core.startswith("|"):
                core = "| " + core
            if not core.endswith("|"):
                core = core + " |"
            out.append(core)
        else:
            out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def normalized_notebook(notebook: Path) -> Path:
    """Write a temp copy of the notebook (in the source dir, so Figures/ paths
    still resolve) with markdown tables normalized. Returns the temp path."""
    nb = json.loads(notebook.read_text(encoding="utf-8"))
    for cell in nb.get("cells", []):
        if cell.get("cell_type") == "markdown":
            src = "".join(cell.get("source", []))
            fixed = normalize_markdown(src)
            if fixed != src:
                cell["source"] = fixed.splitlines(keepends=True)
    tmp = notebook.with_name(f".__build_{notebook.stem}.ipynb")
    tmp.write_text(json.dumps(nb), encoding="utf-8")
    return tmp


def run_nbconvert(notebook: Path, workdir: Path, out_stem: str) -> str:
    """Convert one notebook to reveal HTML with the custom template."""
    cmd = [
        sys.executable, "-m", "nbconvert", str(notebook),
        "--to", "slides",
        "--template", "theme",
        f"--TemplateExporter.extra_template_basedirs={HERE}",
        "--SlidesExporter.reveal_theme=white",
        "--SlidesExporter.embed_images=True",
        "--embed-images",
        "--output-dir", str(workdir),
        "--output", out_stem,
    ]
    subprocess.run(cmd, cwd=HERE, check=True)
    return (workdir / f"{out_stem}.slides.html").read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Post-processing: inline everything so the file is standalone.
# --------------------------------------------------------------------------- #
def data_uri(path: Path) -> str | None:
    if not path.exists():
        return None
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def embed_figures(html: str) -> tuple[str, int]:
    """Rewrite any remaining local Figures/ image src to a data URI."""
    count = 0

    def repl(m: re.Match) -> str:
        nonlocal count
        quote, src = m.group("q"), m.group("src")
        rel = src.lstrip("./")
        uri = data_uri(HERE / rel)
        if uri is None:
            return m.group(0)
        count += 1
        return f'src={quote}{uri}{quote}'

    pattern = re.compile(r'src=(?P<q>["\'])(?P<src>\.?/?Figures/[^"\']+)(?P=q)')
    return pattern.sub(repl, html), count


def inline_assets(html: str, assets: dict[str, str]) -> str:
    """Replace CDN links / marker comments with inlined vendored assets."""
    # reveal core + theme stylesheets (CDN <link> -> inline <style>).
    # Match by URL only, so attribute order/self-closing style don't matter.
    html = re.sub(
        r'<link\b[^>]*\bhref="https://[^"]*/dist/reveal\.css"[^>]*>',
        f"<style>\n{assets['reset_css']}\n{assets['reveal_css']}\n</style>",
        html, count=1)
    # The reveal theme link is the last stylesheet nbconvert emits, so append
    # custom.css right after it to guarantee our design system wins.
    custom_css = (THEME_DIR / "custom.css").read_text(encoding="utf-8")
    html = re.sub(
        r'<link\b[^>]*\bhref="https://[^"]*/dist/theme/[^"]+\.css"[^>]*>',
        f'<style id="theme">\n{assets["theme_css"]}\n</style>\n'
        f'<style id="ci-custom">\n{custom_css}\n</style>',
        html, count=1)

    # Give each slide <section> an id from its first heading so decks can use
    # stable internal links like [see appendix](#/appendix-the-donut-test).
    def _slug(text: str) -> str:
        text = re.sub(r"<[^>]+>", "", text)          # strip inner tags
        text = re.sub(r"&[a-z]+;", " ", text)
        return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

    def _section_id(m: re.Match) -> str:
        head = re.search(r"<h[123][^>]*>(.*?)</h[123]>", m.group(2), re.S)
        if not head:
            return m.group(0)
        return f'{m.group(1)} id="{_slug(head.group(1))}"{m.group(2)}'

    html = re.sub(r"(<section)((?:(?!<section|</section>).)*?<h[123].*?</h[123]>)",
                  _section_id, html, flags=re.S)

    # marker comments -> inline <script>
    html = html.replace(
        "<!--__MATHJAX_JS__-->",
        f'<script id="MathJax-script">\n{assets["mathjax_js"]}\n</script>')
    html = html.replace(
        "<!--__REVEAL_JS__-->",
        f"<script>\n{assets['reveal_js']}\n</script>")
    html = html.replace(
        "<!--__NOTES_JS__-->",
        f"<script>\n{assets['notes_js']}\n</script>")
    return html


def build_deck(notebook: Path, assets: dict[str, str]) -> Path:
    print(f"▸ Building: {notebook.name}")
    tmp_nb = normalized_notebook(notebook)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            html = run_nbconvert(tmp_nb, Path(tmp), notebook.stem)
    finally:
        tmp_nb.unlink(missing_ok=True)
    html = inline_assets(html, assets)
    html, n_fig = embed_figures(html)

    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / f"{notebook.stem}.slides.html"
    out.write_text(html, encoding="utf-8")

    # sanity checks
    # Only count *active* remote loads (href/src attrs). MathJax's bundle
    # contains inert CDN strings for optional a11y features never fetched at render.
    leftover_cdn = len(re.findall(r'(?:href|src)="https://[^"]*(?:reveal\.js|/mathjax|cdnjs|unpkg|jsdelivr)[^"]*"', html))
    leftover_fig = len(re.findall(r'src=["\']\.?/?Figures/', html))
    size_mb = out.stat().st_size / 1e6
    flags = []
    if leftover_cdn:
        flags.append(f"⚠ {leftover_cdn} residual CDN refs")
    if leftover_fig:
        flags.append(f"⚠ {leftover_fig} un-embedded figures")
    status = "  ".join(flags) if flags else "self-contained ✓"
    print(f"  → {out.relative_to(HERE)}  ({size_mb:.1f} MB, {n_fig} figures inlined)  {status}")
    return out


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("decks", nargs="*", help="specific notebook(s) to build (default: all)")
    ap.add_argument("--list", action="store_true", help="list source decks and exit")
    args = ap.parse_args()

    if args.list:
        for d in SOURCE_DECKS:
            print(d)
        return 0

    decks = args.decks or SOURCE_DECKS
    missing = [d for d in decks if not (HERE / d).exists()]
    if missing:
        print("Notebook(s) not found:\n  " + "\n  ".join(missing), file=sys.stderr)
        return 1

    assets = ensure_vendor()
    for d in decks:
        build_deck(HERE / d, assets)
    print(f"\nDone. Open the decks in {OUT_DIR.relative_to(HERE.parent)}/ in any browser.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
