#!/usr/bin/env node
// Exports each built Updated_v2/*.slides.html reveal.js deck to a PDF (one
// physical page per slide) using Chromium's native print pipeline via
// reveal.js's own ?print-pdf mode, and reports any slide whose content is
// chopped by a page boundary. Requires `npm install` in this directory (or
// PLAYWRIGHT_CHROMIUM_PATH pointing at a local Chromium binary).
//
// Usage:
//   node export_pdfs.js                                   # export every deck
//   node export_pdfs.js "Updated_v2/1 Foundations 20230528 update.slides.html"
//
// Exit code is 1 if any slide overflows a page, so the caller can warn.

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

const UPDATED_V2_DIR = path.join(__dirname, 'Updated_v2');

function listDecks() {
  return fs
    .readdirSync(UPDATED_V2_DIR)
    .filter(f => f.endsWith('.slides.html'))
    .map(f => path.join(UPDATED_V2_DIR, f));
}

// Chromium stamps a fresh /CreationDate and /ModDate into every export, so a
// byte comparison always differs even when the deck is unchanged. Blank them
// out before comparing, otherwise a full rebuild dirties every PDF in git.
function withoutTimestamps(buf) {
  return buf.toString('latin1').replace(/\/(CreationDate|ModDate)\s*\(D:[^)]*\)/g, '');
}

// Wait for the things the print layout actually depends on, rather than a
// fixed sleep: reveal builds .pdf-page wrappers asynchronously, and MathJax
// exposes a promise that resolves when typesetting is done.
async function waitForPrintLayout(page) {
  await page.waitForSelector('.pdf-page', { timeout: 30000 });
  await page.evaluate(() => (window.MathJax && MathJax.startup)
    ? MathJax.startup.promise
    : null);
  await page.evaluate(() => document.fonts.ready);
}

// One physical page is the smallest .pdf-page box; reveal grows a slide's box
// to 2x/3x that when its content is taller. Content that ends part-way into
// the last of those pages is fine; content that crosses a boundary is not,
// because Chromium cuts it there — mid-sentence, with no continuation heading.
async function measureSlides(page) {
  return page.evaluate(() => {
    const pages = Array.from(document.querySelectorAll('.pdf-page'));
    const base = Math.min(...pages.map(p => parseInt(getComputedStyle(p).height, 10)));
    return {
      base,
      lastChildIsPdfPage:
        document.querySelector('.reveal .slides').lastElementChild
          ?.classList.contains('pdf-page') ?? false,
      slides: pages.map((p, idx) => {
        const sec = p.querySelector('section');
        const heading = sec && sec.querySelector('h1,h2,h3');
        const top = p.getBoundingClientRect().top;
        // Every element that straddles a page boundary gets sliced in the PDF.
        const cut = [];
        if (sec) {
          for (const n of sec.querySelectorAll('li,p,td,th,h1,h2,h3,img,table')) {
            for (const r of n.getClientRects()) {
              const y0 = r.top - top, y1 = r.bottom - top;
              const boundary = Math.floor(y0 / base) + 1;
              if (y1 > boundary * base && y0 < boundary * base) {
                cut.push({
                  tag: n.tagName,
                  text: (n.innerText || '(image)').replace(/\s+/g, ' ').trim().slice(0, 55),
                  atPage: boundary,
                });
              }
            }
          }
        }
        return {
          idx,
          title: heading ? heading.innerText.replace(/\s+/g, ' ').trim() : '(no heading)',
          spans: Math.round(parseInt(getComputedStyle(p).height, 10) / base),
          cut: cut.slice(0, 4),
        };
      }),
    };
  });
}

async function exportDeck(browser, htmlFile) {
  const outFile = htmlFile.replace(/\.slides\.html$/, '.pdf');
  const url = pathToFileURL(path.resolve(htmlFile)).href + '?print-pdf';
  const page = await browser.newPage({ viewport: { width: 1150, height: 740 } });
  await page.goto(url, { waitUntil: 'networkidle' });
  await waitForPrintLayout(page);

  const { base, slides, lastChildIsPdfPage } = await measureSlides(page);
  const buf = await page.pdf({ printBackground: true, preferCSSPageSize: true });
  await page.close();

  // Skip the write when only the timestamps would change, so an unchanged
  // deck stays clean in git across rebuilds.
  let unchanged = false;
  if (fs.existsSync(outFile)) {
    unchanged = withoutTimestamps(fs.readFileSync(outFile)) === withoutTimestamps(buf);
  }
  if (!unchanged) fs.writeFileSync(outFile, buf);

  const label = unchanged ? 'unchanged' : `${(buf.length / 1024).toFixed(0)} KB`;
  console.log(`\n${path.basename(outFile)}  (${label}, ${slides.length} slides)`);

  if (!lastChildIsPdfPage) {
    console.log('  NOTE: something follows the last .pdf-page; the blank-page rule in');
    console.log('        theme/custom.css targets :last-child and may no longer apply.');
  }

  const bad = slides.filter(s => s.cut.length > 0);
  if (bad.length === 0) {
    console.log('  OK - no slide is cut by a page boundary');
  } else {
    for (const s of bad) {
      console.log(`  CUT  slide ${s.idx + 1} "${s.title}" (spans ${s.spans} page${s.spans > 1 ? 's' : ''})`);
      for (const c of s.cut) {
        console.log(`         sliced at page ${c.atPage} boundary: <${c.tag}> "${c.text}"`);
      }
    }
  }
  return bad.length;
}

async function main() {
  const files = process.argv.length > 2 ? process.argv.slice(2) : listDecks();
  const browser = await chromium.launch({
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH || undefined,
  });

  let cut = 0;
  for (const file of files) {
    cut += await exportDeck(browser, file);
  }

  await browser.close();
  if (cut > 0) {
    console.log(`\n${cut} slide(s) are cut by a page boundary - see CUT lines above.`);
  }
  process.exit(cut > 0 ? 1 : 0);
}

main();
