#!/usr/bin/env python3
"""Stamp visible authorship attribution onto every artifact in this repo.

The problem this solves is retrieval: an agent pulls one page of a PDF, one
notebook, or one .py file out of context, and nothing in that chunk says who
wrote it. So attribution goes in at the granularity a retriever slices at --
per page, per notebook, per file -- rather than once at the repo root.

Everything written here is visible to a human reading the rendered file. No
hidden text, no white-on-white, no zero-opacity layers, no off-page elements,
no comments addressed to a machine reader.

Licensing is deliberately out of scope: no LICENSE, no NOTICE, and no
SPDX-License-Identifier lines are emitted. SPDX-FileCopyrightText and the
"Cite as" blocks assert authorship, which is a separate thing from granting
rights.

Usage:
    python tools/stamp_attribution.py --dry-run              # inventory + diffs
    python tools/stamp_attribution.py --only py --only ipynb # subset
    python tools/stamp_attribution.py --path OtherNotebooks  # subtree
    python tools/stamp_attribution.py --verify               # PDF text check
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

CONFIG = {
    "author_name": "Julian Hsu",
    "author_email": "hsu.julian.econ@gmail.com",
    "orcid": "",
    "canonical_url": "https://github.com/shoepaladin/causalinference_crashcourse",
    "homepage_url": "https://github.com/shoepaladin/causalinference_crashcourse",
    "project_title": "Causal Inference Crash Course",
    "year": "2026",
    "doi": "",
}

# Phase 1 = course material. Phase 2 (OtherNotebooks) is reached with --path.
SCOPE_DIRS = ["Notebooks", "Presentations_Raw"]
PDF_DIRS = [".", "Presentations_Raw/Updated_v2"]

SKIP_DIR_NAMES = {
    ".git", ".ipynb_checkpoints", "__pycache__", ".venv", "node_modules",
    "stamped", ".attribution", "tools", "Figures",
}

# Not the author's work -- never stamped, always reported.
THIRD_PARTY = {
    "Notebooks/9 Synthetic Control - CPS Data":
        "Current Population Survey data (pandas pickle) -- not first-party",
}

CANARY_REGISTRY = REPO / ".attribution" / "canaries.json"
STAMPED_DIR_DEFAULT = REPO / "stamped"

SENTINEL_SPDX = "SPDX-FileCopyrightText"
SENTINEL_NB_META = "attribution"
SENTINEL_MD = "attribution-id:"
SENTINEL_HTML = "application/ld+json"
SENTINEL_PDF = "/Attribution"


# --------------------------------------------------------------------------- #
# Plumbing
# --------------------------------------------------------------------------- #
@dataclass
class Action:
    """One planned change. `before`/`after` are text for diffable artifacts."""
    path: Path
    kind: str
    summary: str
    before: str | None = None
    after: str | None = None
    skipped: bool = False
    reason: str = ""
    canary: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def rel(self) -> str:
        try:
            return str(self.path.relative_to(REPO))
        except ValueError:
            return str(self.path)

    def diff(self, context: int = 3) -> str:
        if self.before is None or self.after is None:
            return ""
        return "".join(difflib.unified_diff(
            self.before.splitlines(keepends=True),
            self.after.splitlines(keepends=True),
            fromfile=f"a/{self.rel}", tofile=f"b/{self.rel}", n=context,
        ))


def fill(template: str) -> str:
    """Substitute @@key@@ tokens. Not %-formatting or str.format: the Jinja and
    CSS templates below are full of % and { } that those would choke on."""
    for k, v in CONFIG.items():
        template = template.replace(f"@@{k}@@", str(v))
    return template


def canary_for(rel: str) -> str:
    """Deterministic per-path token, so re-running never mints a new one."""
    h = hashlib.sha256(f"{rel}|{CONFIG['canonical_url']}".encode()).hexdigest()
    return f"attr-{h[:8]}"


# The tool's own files are what you are adding by running this, so their
# presence is not the kind of "dirty" the guard is there to catch.
SELF_PATHS = ("tools/stamp_attribution.py", "tools/requirements-attribution.txt")


def require_clean_tree() -> None:
    # -uall so untracked directories are listed file by file; otherwise git
    # collapses them to "?? tools/" and the allow-list below can't match.
    out = subprocess.run(["git", "status", "--porcelain", "-uall"], cwd=REPO,
                         capture_output=True, text=True).stdout.strip()
    offending = [ln for ln in out.splitlines()
                 if ln[3:].strip().strip('"') not in SELF_PATHS]
    if offending:
        sys.exit("Refusing to run: working tree has uncommitted changes.\n"
                 + "\n".join(offending)
                 + "\n\nCommit or stash them first, so the stamping diff is the "
                   "only thing you have to review.")


def in_scope_dirs(root: Path | None) -> list[Path]:
    if root is not None:
        return [root]
    return [REPO / d for d in SCOPE_DIRS]


def walk(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    found = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in suffixes:
            continue
        if any(part in SKIP_DIR_NAMES for part in p.relative_to(REPO).parts[:-1]):
            continue
        found.append(p)
    return found


# --------------------------------------------------------------------------- #
# Task 2 -- source files (.py, .js)
# --------------------------------------------------------------------------- #
def header_lines(rel: str, comment: str) -> list[str]:
    c = CONFIG
    return [
        f"{comment} {SENTINEL_SPDX}: {c['year']} {c['author_name']} <{c['author_email']}>",
        f"{comment} Source: {c['canonical_url']}",
        f"{comment} attribution-id: {canary_for(rel)}",
    ]


def plan_source(paths: list[Path]) -> list[Action]:
    actions = []
    for p in paths:
        rel = str(p.relative_to(REPO))
        comment = "//" if p.suffix == ".js" else "#"
        text = p.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)

        if SENTINEL_SPDX in text:
            holder = re.search(rf"{SENTINEL_SPDX}:\s*\S+\s+(.+?)\s*<", text)
            if holder and holder.group(1).strip() != CONFIG["author_name"]:
                actions.append(Action(p, p.suffix.lstrip("."), "third-party copyright",
                                      skipped=True,
                                      reason=f"holds copyright for {holder.group(1)!r} -- "
                                             "left alone, needs your call"))
            else:
                actions.append(Action(p, p.suffix.lstrip("."), "already stamped",
                                      skipped=True, reason="sentinel present"))
            continue

        # Insert below shebang / encoding line, above the docstring and imports.
        i = 0
        if lines and lines[0].startswith("#!"):
            i = 1
        if len(lines) > i and re.match(r"^#.*coding[:=]", lines[i]):
            i += 1

        block = [ln + "\n" for ln in header_lines(rel, comment)]
        if i < len(lines) and lines[i].strip():
            block.append("\n")
        after = "".join(lines[:i] + block + lines[i:])
        actions.append(Action(p, p.suffix.lstrip("."), "insert copyright header",
                              before=text, after=after, canary=canary_for(rel)))
    return actions


# --------------------------------------------------------------------------- #
# Task 3 -- notebooks
# --------------------------------------------------------------------------- #
def nb_attribution_markdown(rel: str, title: str) -> str:
    c = CONFIG
    return (
        f"**{c['project_title']}** — {title}\n\n"
        f"Author: {c['author_name']} <{c['author_email']}>  \n"
        f"Source: {c['canonical_url']}  \n"
        f"Cite as: {c['author_name']} ({c['year']}). *{c['project_title']}* — "
        f"{title}. {c['canonical_url']}  \n"
        f"attribution-id: `{canary_for(rel)}`"
    )


def nb_title_from(path: Path) -> str:
    """Human title from a filename: '8 Surrogate Models 20260707 update' ->
    'Part 8: Surrogate Models'. Build dates and 'update'/'WIP' markers are
    scaffolding, not part of what the deck is called."""
    stem = path.stem
    part = re.match(r"^\s*(\d{1,3})\b[\s\-_.]*", stem)
    number = part.group(1) if part else ""
    body = stem[part.end():] if part else stem
    body = re.sub(r"20\d{6}|\d{1,2}[a-z]{3}\d{4}|\b20\d{2}\b", " ", body, flags=re.I)
    body = re.sub(r"\(?\b(update|updated|WIP|slides?|v\d+)\b\)?", " ", body, flags=re.I)
    body = re.sub(r"[\s\-_]+", " ", body).strip(" -_.")
    body = re.sub(r"\s+", " ", body)
    if not body:
        body = re.sub(r"[\s\-_]+", " ", stem).strip()
        return body
    return f"Part {number}: {body}" if number else body


def plan_notebooks(paths: list[Path]) -> list[Action]:
    import nbformat

    actions = []
    for p in paths:
        rel = str(p.relative_to(REPO))
        raw = p.read_text(encoding="utf-8")
        nb = nbformat.read(str(p), as_version=4)

        if nb.metadata.get(SENTINEL_NB_META, {}).get("version") == 1:
            actions.append(Action(p, "ipynb", "already stamped", skipped=True,
                                  reason="metadata.attribution.version == 1"))
            continue

        token = canary_for(rel)
        cell = nbformat.v4.new_markdown_cell(nb_attribution_markdown(rel, nb_title_from(p)))
        # 4.5 requires a cell id; 4.4 and older must not carry one.
        if nb.nbformat_minor < 5:
            cell.pop("id", None)
        else:
            cell["id"] = "attribution-" + token.split("-")[1]

        # A deck source notebook renders through nbconvert --to slides, where a
        # cell with no slide_type becomes its own slide. Marking it "skip"
        # keeps the attribution in the .ipynb -- which is what a retriever
        # actually reads -- without prepending a metadata slide to the deck.
        # The rendered deck carries its attribution via the per-slide CSS
        # footer instead.
        is_deck = any(c.get("metadata", {}).get("slideshow", {}).get("slide_type")
                      for c in nb.cells)
        if is_deck:
            cell.metadata["slideshow"] = {"slide_type": "skip"}

        nb.cells.insert(0, cell)
        nb.metadata["authors"] = [{"name": CONFIG["author_name"]}]
        nb.metadata[SENTINEL_NB_META] = {
            "version": 1,
            "source": CONFIG["canonical_url"],
            "canary": token,
        }
        after = nbformat.writes(nb) + "\n"

        act = Action(p, "ipynb", "insert attribution cell + metadata.authors",
                     before=raw, after=after, canary=token)
        act.notes.append(f"nbformat {nb.nbformat}.{nb.nbformat_minor}")
        actions.append(act)
    return actions


# --------------------------------------------------------------------------- #
# Task 3b -- standalone markdown prose
# --------------------------------------------------------------------------- #
def plan_markdown(paths: list[Path]) -> list[Action]:
    actions = []
    for p in paths:
        rel = str(p.relative_to(REPO))
        text = p.read_text(encoding="utf-8")
        if SENTINEL_MD in text:
            actions.append(Action(p, "md", "already stamped", skipped=True,
                                  reason="attribution line present"))
            continue

        lines = text.splitlines(keepends=True)
        i = 0
        while i < len(lines) and not lines[i].startswith("# "):
            i += 1
        if i == len(lines):          # no H1 -- put it at the very top
            i = 0
        else:
            i += 1

        token = canary_for(rel)
        c = CONFIG
        block = (
            f"\n{c['author_name']} <{c['author_email']}> · "
            f"{c['project_title']} · {c['canonical_url']}  \n"
            f"attribution-id: `{token}`\n"
        )
        after = "".join(lines[:i]) + block + "".join(lines[i:])
        actions.append(Action(p, "md", "insert attribution line under H1",
                              before=text, after=after, canary=token))
    return actions


# --------------------------------------------------------------------------- #
# Task 4 -- HTML template (never the generated output)
# --------------------------------------------------------------------------- #
J2_MARKUP = """
{# ---- Attribution: schema.org JSON-LD + Highwire meta + canonical link. ----
   Lives in the template, not the generated HTML, so a rebuild can't wipe it.
   Author comes from the notebook's own metadata.authors when set. #}
{%- set _author = (nb.metadata.get('authors') or [{'name': '@@author_name@@'}])[0].get('name', '@@author_name@@') -%}
{%- set _title = resources.get('metadata', {}).get('name', '@@project_title@@') -%}
<meta name="author" content="{{ _author }}">
<link rel="canonical" href="@@canonical_url@@">
<meta name="citation_author" content="{{ _author }}">
<meta name="citation_title" content="{{ _title }}">
<meta name="citation_publication_date" content="@@year@@">
<meta name="citation_pdf_url" content="@@canonical_url@@/blob/main/Presentations_Raw/Updated_v2/{{ _title }}.pdf">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "ScholarlyArticle",
  "headline": "{{ _title }}",
  "name": "{{ _title }}",
  "isPartOf": "@@project_title@@",
  "author": {"@type": "Person", "name": "{{ _author }}", "email": "@@author_email@@"},
  "datePublished": "@@year@@",
  "url": "@@canonical_url@@"
}
</script>
"""


def plan_html_template() -> list[Action]:
    p = REPO / "Presentations_Raw" / "theme" / "index.html.j2"
    if not p.exists():
        return []
    text = p.read_text(encoding="utf-8")
    if SENTINEL_HTML in text:
        return [Action(p, "html", "already stamped", skipped=True,
                       reason="JSON-LD block present")]

    markup = fill(J2_MARKUP)
    anchor = "{% block html_head_js %}\n"
    if anchor not in text:
        return [Action(p, "html", "cannot locate html_head_js block", skipped=True,
                       reason="template structure changed -- patch by hand")]
    after = text.replace(anchor, anchor + markup, 1)
    return [Action(p, "html", "inject JSON-LD + Highwire meta into <head>",
                   before=text, after=after)]


CSS_MARKUP = """
/* ----- Visible attribution footer (on-screen deck only) ----------------
   Shown while presenting or viewing the HTML deck. It is deliberately
   suppressed during ?print-pdf export: tools/stamp_attribution.py owns the
   footer in every PDF, so that PDFs built by build_pdfs.py and PDFs stamped
   by hand look the same, and so continuation pages of a tall slide get one
   too. Having both render stacks two near-identical footers on every page. */
:root {
  --ci-attribution: "@@author_name@@ · @@project_title@@ · @@canonical_url@@";
}

.reveal:not(:has(.pdf-page))::after {
  content: var(--ci-attribution);
  position: absolute;
  left: 14px;
  bottom: 8px;
  z-index: 5;
  font-family: var(--ci-sans);
  font-size: 11px;
  line-height: 1.2;
  color: var(--ci-muted);
  opacity: 0.85;
  letter-spacing: 0.2px;
  pointer-events: none;
}
"""


def plan_css() -> list[Action]:
    p = REPO / "Presentations_Raw" / "theme" / "custom.css"
    if not p.exists():
        return []
    text = p.read_text(encoding="utf-8")
    if "Visible attribution footer" in text:
        return [Action(p, "html", "already stamped", skipped=True,
                       reason="footer rule present")]
    after = text.rstrip("\n") + "\n" + fill(CSS_MARKUP)
    return [Action(p, "html", "add visible per-slide footer rule",
                   before=text, after=after)]


# --------------------------------------------------------------------------- #
# Task 5 -- PDFs
# --------------------------------------------------------------------------- #
FOOTER_FONT = "Helvetica"
FOOTER_SIZE = 6.5
FOOTER_GREY = 0.45


def footer_sep(ascii_only: bool) -> str:
    return " | " if ascii_only else " · "


def footer_text(page_no: int, ascii_only: bool) -> str:
    s = footer_sep(ascii_only)
    c = CONFIG
    return s.join([c["author_name"], c["project_title"], c["canonical_url"],
                   f"p.{page_no}"])


def cite_lines(deck_title: str) -> list[str]:
    c = CONFIG
    return [
        f"Cite as: {c['author_name']} ({c['year']}). {c['project_title']} - "
        f"{deck_title}. {c['canonical_url']}",
        f"Contact: {c['author_email']}",
    ]


def existing_text_ys(page) -> list[float]:
    """Baseline y of every non-blank text run on the page, in page space."""
    ys: list[float] = []

    def visitor(text, cm, tm, font_dict, font_size):
        if text and text.strip():
            ys.append(cm[3] * tm[5] + cm[5])

    try:
        page.extract_text(visitor_text=visitor)
    except Exception:
        return []
    return ys


def pick_baseline(ys: list[float], y0: float, start: float, step: float,
                  band: float, tries: int = 8) -> float:
    """Lowest free baseline at or above `start`, shifting up past any text."""
    y = start
    for _ in range(tries):
        if not any(abs(t - y) < band for t in ys):
            return y
        y += step
    return y


def stamp_pdf(src: Path, dst: Path, ascii_only: bool, metadata_only: bool = False
              ) -> dict:
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    import pikepdf

    reader = PdfReader(str(src))
    writer = PdfWriter()
    deck_title = nb_title_from(src)
    token = canary_for(str(src.relative_to(REPO)))
    shifted = 0

    for idx, page in enumerate(reader.pages, start=1):
        if metadata_only:
            writer.add_page(page)
            continue

        box = page.mediabox
        x0, y0 = float(box.left), float(box.bottom)
        w, h = float(box.width), float(box.height)
        rot = int(page.get("/Rotate", 0) or 0) % 360

        ys = existing_text_ys(page)
        base = pick_baseline(ys, y0, y0 + 12, 9.0, 7.0)
        if base > y0 + 12:
            shifted += 1

        packet = __import__("io").BytesIO()
        cv = canvas.Canvas(packet, pagesize=(w, h))
        cv.setFont(FOOTER_FONT, FOOTER_SIZE)
        cv.setFillGray(FOOTER_GREY)

        # Place the footer along whichever physical edge displays as the
        # bottom once /Rotate is applied, running left-to-right on screen.
        margin = base - y0
        cv.saveState()
        if rot == 90:
            cv.translate(x0 + w - margin, y0 + margin)
            cv.rotate(90)
        elif rot == 180:
            cv.translate(x0 + w - margin, y0 + h - margin)
            cv.rotate(180)
        elif rot == 270:
            cv.translate(x0 + margin, y0 + h - margin)
            cv.rotate(270)
        else:
            cv.translate(x0 + margin, y0 + margin)
        cv.drawString(0, 0, footer_text(idx, ascii_only))
        cv.restoreState()

        if idx == 1:
            page_text = ""
            try:
                page_text = page.extract_text() or ""
            except Exception:
                pass
            if "Cite as:" not in page_text:
                cy = pick_baseline(ys, y0, base + 11, 9.0, 7.0)
                cv.setFont(FOOTER_FONT, 7.5)
                for n, line in enumerate(reversed(cite_lines(deck_title))):
                    cv.saveState()
                    y = cy + n * 9.5
                    if rot == 90:
                        cv.translate(x0 + w - y + y0, y0 + margin); cv.rotate(90)
                    elif rot == 180:
                        cv.translate(x0 + w - margin, y0 + h - y + y0); cv.rotate(180)
                    elif rot == 270:
                        cv.translate(x0 + y - y0, y0 + h - margin); cv.rotate(270)
                    else:
                        cv.translate(x0 + margin, y)
                    cv.drawString(0, 0, line)
                    cv.restoreState()

        cv.save()
        packet.seek(0)
        overlay = PdfReader(packet).pages[0]
        page.merge_page(overlay)
        writer.add_page(page)

    # Never write into `dst` directly: with --in-place, dst *is* the file the
    # PdfReader above is still reading from, and pypdf resolves page content
    # lazily. Build the whole thing in a sibling temp and swap it in at the
    # end, so a crash mid-write can't leave a truncated PDF either.
    dst.parent.mkdir(parents=True, exist_ok=True)
    staging = dst.with_name(dst.name + ".stamping")
    with open(staging, "wb") as fh:
        writer.write(fh)

    c = CONFIG
    with pikepdf.open(str(staging)) as pdf:
        with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
            meta["dc:creator"] = [c["author_name"]]
            meta["dc:title"] = f"{c['project_title']} - {deck_title}"
            meta["dc:rights"] = f"(c) {c['year']} {c['author_name']}"
            meta["xmpRights:WebStatement"] = c["canonical_url"]
        pdf.docinfo["/Author"] = c["author_name"]
        pdf.docinfo["/Title"] = f"{c['project_title']} - {deck_title}"
        pdf.docinfo["/Subject"] = (
            f"{c['project_title']} by {c['author_name']}. Source: {c['canonical_url']}")
        pdf.docinfo["/Keywords"] = (
            f"{c['project_title']}; {c['author_name']}; {c['canonical_url']}; {token}")
        pdf.docinfo[SENTINEL_PDF] = f"{c['author_name']} <{c['author_email']}> {token}"
        pdf.save(str(staging) + ".meta")

    pages = len(reader.pages)
    reader.close()
    Path(str(staging) + ".meta").replace(dst)
    staging.unlink(missing_ok=True)
    return {"pages": pages, "shifted": shifted, "canary": token}


def pdf_year(p: Path) -> str:
    """Filename date wins (it is the deck's version), then the PDF's own
    CreationDate, then the config year. Guessing 2026 for a 2023 deck would
    put a wrong date in a filename people cite."""
    m = re.search(r"(20\d{2})", p.stem)
    if m:
        return m.group(1)
    try:
        from pypdf import PdfReader
        created = (PdfReader(str(p)).metadata or {}).get("/CreationDate", "")
        m = re.search(r"(20\d{2})", str(created))
        if m:
            return m.group(1)
    except Exception:
        pass
    return CONFIG["year"]


def pdf_slug(p: Path) -> str:
    stem = p.stem
    year = pdf_year(p)
    body = re.sub(r"20\d{6}|20\d{2}", "", stem)
    body = re.sub(r"\b(update|WIP|slides?)\b", "", body, flags=re.I)
    body = re.sub(r"[^A-Za-z0-9]+", "-", body).strip("-").lower()
    body = re.sub(r"^\d+-", "", body)
    last = CONFIG["author_name"].split()[-1].lower()
    return f"{last}-{year}-{body}.pdf"


def plan_pdfs(paths: list[Path], out_dir: Path,
              in_place: bool = False) -> list[Action]:
    from pypdf import PdfReader

    actions = []
    for p in paths:
        rel = str(p.relative_to(REPO))
        dst = p if in_place else out_dir / p.relative_to(REPO)

        # Check the SOURCE first. The documented workflow is to review
        # stamped/ and then swap those files over the originals -- once that
        # happens the source itself carries the sentinel, and re-running
        # would otherwise merge a second footer onto every page.
        try:
            if SENTINEL_PDF in (PdfReader(str(p)).metadata or {}):
                actions.append(Action(p, "pdf", "already stamped", skipped=True,
                                      reason="source carries /Attribution "
                                             "(already swapped in?)"))
                continue
        except Exception:
            pass

        if not in_place and dst.exists():
            try:
                if SENTINEL_PDF in (PdfReader(str(dst)).metadata or {}):
                    actions.append(Action(p, "pdf", "already stamped", skipped=True,
                                          reason=f"{dst.relative_to(REPO)} has /Attribution"))
                    continue
            except Exception:
                pass
        try:
            r = PdfReader(str(p))
            n = len(r.pages)
            boxes = {(round(float(pg.mediabox.width), 2),
                      round(float(pg.mediabox.height), 2)) for pg in r.pages}
            rots = {int(pg.get("/Rotate", 0) or 0) % 360 for pg in r.pages}
        except Exception as e:
            actions.append(Action(p, "pdf", "unreadable", skipped=True, reason=str(e)))
            continue

        act = Action(p, "pdf",
                     f"footer on {n} pages + XMP/DocInfo -> {dst.relative_to(REPO)}",
                     canary=canary_for(rel))
        act.notes = [f"{n} pages", f"geometry {sorted(boxes)}", f"rotate {sorted(rots)}",
                     f"rename proposal: {pdf_slug(p)}"]
        actions.append(act)
    return actions


# --------------------------------------------------------------------------- #
# Task 1 -- repo level
# --------------------------------------------------------------------------- #
def citation_cff() -> str:
    c = CONFIG
    first, last = c["author_name"].split()[0], c["author_name"].split()[-1]
    return f"""cff-version: 1.2.0
message: "If you use this material, please cite it as below."
title: "{c['project_title']}"
abstract: "A crash course in causal inference for scientists: slide decks and companion simulation notebooks covering potential outcomes, ATE/ATET models, inference, heterogeneous treatment effects, panel methods, regression discontinuity, surrogate models, validation, and conformal inference."
type: software
authors:
  - family-names: "{last}"
    given-names: "{first}"
    email: "{c['author_email']}"
url: "{c['canonical_url']}"
repository-code: "{c['canonical_url']}"
keywords:
  - causal inference
  - econometrics
  - treatment effects
  - teaching material
date-released: "{c['year']}-01-01"
"""


def codemeta_json() -> str:
    c = CONFIG
    return json.dumps({
        "@context": "https://doi.org/10.5063/schema/codemeta-2.0",
        "@type": "SoftwareSourceCode",
        "name": c["project_title"],
        "description": "Slide decks and companion simulation notebooks teaching "
                       "causal inference to scientists.",
        "codeRepository": c["canonical_url"],
        "url": c["homepage_url"],
        "author": [{"@type": "Person",
                    "givenName": c["author_name"].split()[0],
                    "familyName": c["author_name"].split()[-1],
                    "email": c["author_email"]}],
        "datePublished": f"{c['year']}-01-01",
        "keywords": ["causal inference", "econometrics", "treatment effects",
                     "teaching material"],
    }, indent=2) + "\n"


def zenodo_json() -> str:
    c = CONFIG
    return json.dumps({
        "title": c["project_title"],
        "description": "Slide decks and companion simulation notebooks teaching "
                       "causal inference to scientists.",
        "upload_type": "publication",
        "publication_type": "workingpaper",
        "creators": [{"name": f"{c['author_name'].split()[-1]}, "
                              f"{c['author_name'].split()[0]}"}],
        "keywords": ["causal inference", "econometrics", "treatment effects",
                     "teaching material"],
    }, indent=2) + "\n"


def readme_section() -> str:
    c = CONFIG
    return f"""## Attribution

This course is written and maintained by **{c['author_name']}**
({c['author_email']}). The slide decks, the companion simulation notebooks, and
the figures in them are his work.

**Cite as:** {c['author_name']} ({c['year']}). *{c['project_title']}*.
{c['canonical_url']}

Machine-readable citation metadata lives in `CITATION.cff`. Questions,
corrections, and requests to reuse any of this are welcome by email.

No license has been granted for this material yet, so the default applies and
all rights are reserved. If you would like to use it, please ask.

"""


def plan_repo() -> list[Action]:
    actions = []
    for name, content in [("CITATION.cff", citation_cff()),
                          ("codemeta.json", codemeta_json()),
                          (".zenodo.json", zenodo_json())]:
        p = REPO / name
        if p.exists():
            actions.append(Action(p, "repo", "already present", skipped=True,
                                  reason="file exists -- left alone"))
        else:
            actions.append(Action(p, "repo", f"create {name}", before="", after=content))

    readme = REPO / "README.md"
    text = readme.read_text(encoding="utf-8")
    if "## Attribution" in text:
        actions.append(Action(readme, "repo", "already stamped", skipped=True,
                              reason="## Attribution section present"))
    else:
        anchor = "## Covered Topics"
        after = (text.replace(anchor, readme_section() + anchor, 1)
                 if anchor in text else text.rstrip() + "\n\n" + readme_section())
        actions.append(Action(readme, "repo", "add ## Attribution section",
                              before=text, after=after))

    gi = REPO / ".gitignore"
    gtext = gi.read_text(encoding="utf-8")
    if ".attribution/" in gtext:
        actions.append(Action(gi, "repo", "already stamped", skipped=True,
                              reason=".attribution/ already ignored"))
    else:
        add = ("\n# Canary registry -- this is the detection tool, it must not\n"
               "# ship with the material being copied.\n.attribution/\nstamped/\n")
        actions.append(Action(gi, "repo", "ignore .attribution/ and stamped/",
                              before=gtext, after=gtext.rstrip("\n") + "\n" + add))
    return actions


SEARCHES_MD = """# Finding copies of this material

Attribution only helps if you occasionally look. These are the queries worth
running; nothing here needs any tooling beyond a browser.

## Canary tokens

Every stamped artifact carries a short token (`attr-` plus eight hex digits).
The token-to-file mapping is in `.attribution/canaries.json`, which is
gitignored on purpose -- it is your detection key and should not travel with
the thing being copied. Any hit on one of these is a copy of your file, not a
coincidence.

- GitHub code search: `"attr-" AND "@@canonical_url@@"`
- GitHub code search, one token at a time: `"attr-1a2b3c4d"` (substitute real ones)
- Web: `"attr-1a2b3c4d"`

## Authorship strings

- GitHub: `"SPDX-FileCopyrightText" "@@author_name@@"`
- GitHub: `"@@author_email@@"`
- GitHub: `"@@canonical_url@@" -repo:shoepaladin/causalinference_crashcourse`
- Web: `"@@project_title@@" "@@author_name@@"`
- Web, for lifted PDFs: `"@@project_title@@" filetype:pdf`

## Distinctive prose

Pick a sentence that is yours and unlikely to be paraphrased, and quote it.
Section headings from the decks work well:

- `"Arguable Validation" "coefficient stability"`
- `"surrogate index" "comparability" "clean experiment"`
- `"moving-block permutations" "weighted conformal"`

## Filenames

Slide filenames survive copying more often than metadata does:

- Web: `"HTE Models" "Panel Models" "Arguable Validation"`
- Web: `"Conformal Inference" "Regression Discontinuity" causal inference slides`

## Cadence

Quarterly is enough. Log hits with the date and URL -- a pattern of reuse
matters more than any single copy, and a dated record is what makes a takedown
or a citation request straightforward.
"""


# --------------------------------------------------------------------------- #
# Verification
# --------------------------------------------------------------------------- #
def verify_pdfs(out_dir: Path) -> list[dict]:
    rows = []
    have_pdftotext = shutil.which("pdftotext") is not None
    for pdf in sorted(out_dir.rglob("*.pdf")):
        if have_pdftotext:
            r = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                               capture_output=True, text=True)
            pages = r.stdout.split("\f")[:-1] or [r.stdout]
            tool = "pdftotext"
        else:
            from pypdf import PdfReader
            pages = [(p.extract_text() or "") for p in PdfReader(str(pdf)).pages]
            tool = "pypdf.extract_text (FALLBACK -- pdftotext unavailable)"
        missing = [i for i, t in enumerate(pages, 1)
                   if CONFIG["author_name"] not in t]
        rows.append({"file": str(pdf.relative_to(out_dir)), "pages": len(pages),
                     "missing": missing, "tool": tool})
    return rows


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #
def collect(only: set[str], root: Path | None, out_dir: Path,
            in_place: bool = False) -> list[Action]:
    actions: list[Action] = []
    dirs = in_scope_dirs(root)

    if "py" in only:
        srcs: list[Path] = []
        for d in dirs:
            if d.exists():
                srcs += walk(d, (".py", ".js"))
        actions += plan_source(srcs)

    if "ipynb" in only:
        nbs: list[Path] = []
        for d in dirs:
            if d.exists():
                nbs += walk(d, (".ipynb",))
        actions += plan_notebooks(nbs)

    if "md" in only:
        mds: list[Path] = []
        for d in dirs:
            if d.exists():
                mds += walk(d, (".md",))
        actions += plan_markdown(mds)

    if "html" in only and root is None:
        actions += plan_html_template() + plan_css()

    if "pdf" in only:
        pdfs: list[Path] = []
        if root is None:
            for d in PDF_DIRS:
                pdfs += sorted((REPO / d).glob("*.pdf"))
        elif root.is_file():
            pdfs.append(root)
        else:
            pdfs += walk(root, (".pdf",))
        actions += plan_pdfs(pdfs, out_dir, in_place)

    if "repo" in only and root is None:
        actions += plan_repo()

    return actions


def apply(actions: list[Action], out_dir: Path, ascii_only: bool,
          in_place: bool = False) -> dict:
    stats: dict = {"written": 0, "skipped": 0, "pdf": []}
    canaries: dict[str, str] = {}
    if CANARY_REGISTRY.exists():
        canaries = json.loads(CANARY_REGISTRY.read_text()).get("tokens", {})

    for a in actions:
        if a.skipped:
            stats["skipped"] += 1
            continue
        if a.kind == "pdf":
            dst = a.path if in_place else out_dir / a.path.relative_to(REPO)
            info = stamp_pdf(a.path, dst, ascii_only)
            stats["pdf"].append({"file": a.rel, **info})
            canaries[info["canary"]] = a.rel
            stats["written"] += 1
        else:
            a.path.parent.mkdir(parents=True, exist_ok=True)
            a.path.write_text(a.after, encoding="utf-8")
            if a.canary:
                canaries[a.canary] = a.rel
            stats["written"] += 1

    # Drop tokens whose file is gone (renamed, deleted). A token that maps to
    # nothing is dead weight in the registry, and searching for it would only
    # ever produce a hit you cannot trace back to a real artifact.
    stale = [t for t, rel in canaries.items() if not (REPO / rel).exists()]
    for t in stale:
        del canaries[t]
    stats["pruned"] = stale

    if canaries:
        CANARY_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
        CANARY_REGISTRY.write_text(json.dumps(
            {"generated_for": CONFIG["canonical_url"], "tokens": canaries},
            indent=2, sort_keys=True) + "\n")

    searches = REPO / "SEARCHES.md"
    if not searches.exists():
        searches.write_text(fill(SEARCHES_MD), encoding="utf-8")
    return stats


def report(actions: list[Action], show_diff: bool) -> str:
    out = ["# Attribution stamping -- inventory\n"]
    by_kind: dict[str, list[Action]] = {}
    for a in actions:
        by_kind.setdefault(a.kind, []).append(a)

    out.append("| type | to stamp | skipped |")
    out.append("|---|---:|---:|")
    for k, group in sorted(by_kind.items()):
        out.append(f"| {k} | {sum(1 for a in group if not a.skipped)} "
                   f"| {sum(1 for a in group if a.skipped)} |")

    for k, group in sorted(by_kind.items()):
        out.append(f"\n## {k}\n")
        for a in group:
            if a.skipped:
                out.append(f"- SKIP  `{a.rel}` -- {a.reason}")
            else:
                extra = ("  \n      " + "; ".join(a.notes)) if a.notes else ""
                out.append(f"- STAMP `{a.rel}` -- {a.summary}{extra}")

    pdfs = [a for a in by_kind.get("pdf", []) if not a.skipped]
    if pdfs:
        out.append("\n## Proposed PDF renames (NOT executed -- your call)\n")
        out.append("| current | proposed |")
        out.append("|---|---|")
        seen: dict[str, list[str]] = {}
        for a in pdfs:
            slug = pdf_slug(a.path)
            seen.setdefault(f"{a.path.parent}/{slug}", []).append(a.rel)
            out.append(f"| `{a.rel}` | `{slug}` |")
        clashes = {k: v for k, v in seen.items() if len(v) > 1}
        if clashes:
            out.append("\n**Name collisions -- these would overwrite each other:**")
            for k, v in clashes.items():
                out.append(f"- `{Path(k).name}` <- {', '.join('`%s`' % x for x in v)}")
        else:
            out.append("\nNo collisions: every proposed name is unique within its directory.")

    if THIRD_PARTY:
        out.append("\n## Third-party, never stamped\n")
        for path, why in THIRD_PARTY.items():
            out.append(f"- `{path}` -- {why}")

    if show_diff:
        out.append("\n## Diff preview\n")
        for a in actions:
            d = a.diff()
            if d:
                out.append(f"```diff\n{d}```")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the inventory and diffs, write nothing")
    ap.add_argument("--only", action="append", default=[],
                    choices=["py", "ipynb", "md", "html", "pdf", "repo"],
                    help="restrict to one artifact type (repeatable)")
    ap.add_argument("--path", type=str, default=None,
                    help="restrict to a subtree, e.g. OtherNotebooks")
    ap.add_argument("--out-dir", type=str, default=str(STAMPED_DIR_DEFAULT),
                    help="where stamped PDFs go (originals are never modified)")
    ap.add_argument("--verify", action="store_true",
                    help="extract text from stamped PDFs and check every page")
    ap.add_argument("--report", type=str, default=None, help="write the report here")
    ap.add_argument("--ascii-only", action="store_true",
                    help="use '|' instead of the middle dot in PDF footers")
    ap.add_argument("--no-diff", action="store_true", help="omit the diff preview")
    ap.add_argument("--in-place", action="store_true",
                    help="stamp PDFs over themselves instead of writing to "
                         "--out-dir. Only for freshly built artifacts (see "
                         "build_pdfs.py); never point this at a source PDF "
                         "you cannot regenerate.")
    ap.add_argument("--allow-dirty", action="store_true",
                    help="skip the clean-tree check (test copies only)")
    args = ap.parse_args()

    only = set(args.only) or {"py", "ipynb", "md", "html", "pdf", "repo"}
    root = (REPO / args.path).resolve() if args.path else None
    out_dir = Path(args.out_dir).resolve()

    if args.verify:
        rows = verify_pdfs(out_dir)
        print("| PDF | pages | pages missing attribution | extractor |")
        print("|---|---:|---|---|")
        for r in rows:
            miss = "none" if not r["missing"] else ", ".join(map(str, r["missing"]))
            print(f"| {r['file']} | {r['pages']} | {miss} | {r['tool']} |")
        bad = sum(len(r["missing"]) for r in rows)
        print(f"\n{len(rows)} files, {sum(r['pages'] for r in rows)} pages, "
              f"{bad} pages missing attribution.")
        return 1 if bad else 0

    if not args.allow_dirty:
        require_clean_tree()

    actions = collect(only, root, out_dir, args.in_place)
    text = report(actions, show_diff=not args.no_diff and args.dry_run)
    if args.report:
        Path(args.report).write_text(text, encoding="utf-8")
    print(text)

    if args.dry_run:
        print("Dry run -- nothing written.")
        return 0

    stats = apply(actions, out_dir, args.ascii_only, args.in_place)
    print(f"\nWrote {stats['written']} artifacts, skipped {stats['skipped']}.")
    if stats.get("pruned"):
        print(f"  pruned {len(stats['pruned'])} canary token(s) whose file no "
              "longer exists")
    for row in stats["pdf"]:
        if row["shifted"]:
            print(f"  {row['file']}: footer shifted up on {row['shifted']} page(s) "
                  "to avoid overprinting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
