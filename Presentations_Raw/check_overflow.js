#!/usr/bin/env node
// Scans one or more built Updated_v2/*.slides.html decks in reveal.js's
// ?print-pdf mode and reports any slide whose content is taller than a
// single physical PDF page (reveal.js's print CSS otherwise silently grows
// that slide's page box to 2-3x height, which Chromium then paginates at an
// arbitrary point when printed to PDF).
//
// Usage:
//   node check_overflow.js "Updated_v2/9 Arguable Validation 20230606 update.slides.html"
//   node check_overflow.js Updated_v2/*.slides.html

const { chromium } = require('playwright');
const path = require('path');
const { pathToFileURL } = require('url');

async function measureDeck(browser, file) {
  const url = pathToFileURL(path.resolve(file)).href + '?print-pdf';
  const page = await browser.newPage({ viewport: { width: 1150, height: 740 } });
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500); // let MathJax settle

  const baseHeight = await page.evaluate(() => {
    const heights = Array.from(document.querySelectorAll('.pdf-page'))
      .map(p => parseInt(getComputedStyle(p).height, 10));
    // the standard single-page height is the smallest one present
    return Math.min(...heights);
  });

  const results = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('.pdf-page')).map((p, i) => {
      const cs = getComputedStyle(p);
      const sec = p.querySelector('section');
      const title = sec ? ((sec.querySelector('h1,h2,h3') || {}).innerText || '(no heading)') : '(no section)';
      return {
        idx: i,
        title: title.replace(/\s+/g, ' ').trim(),
        pageHeight: parseInt(cs.height, 10),
        contentHeight: sec ? sec.scrollHeight : null,
      };
    });
  });

  await page.close();
  return { file, baseHeight, slides: results };
}

async function main() {
  const files = process.argv.slice(2);
  if (files.length === 0) {
    console.error('Usage: node check_overflow.js <deck.slides.html> [...]');
    process.exit(1);
  }

  const browser = await chromium.launch({
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH || undefined,
  });

  let anyFlagged = false;
  for (const file of files) {
    const { baseHeight, slides } = await measureDeck(browser, file);
    const flagged = slides.filter(
      s => s.pageHeight > baseHeight + 2 || (s.contentHeight ?? 0) > s.pageHeight + 2
    );
    console.log(`\n${file}`);
    console.log(`  base page height: ${baseHeight}px, ${slides.length} slides`);
    if (flagged.length === 0) {
      console.log('  OK - no overflowing slides');
    } else {
      anyFlagged = true;
      for (const s of flagged) {
        const over = (s.contentHeight ?? 0) - s.pageHeight;
        console.log(
          `  FLAG idx=${s.idx} "${s.title}" pageHeight=${s.pageHeight} contentHeight=${s.contentHeight} overflow=${over}px`
        );
      }
    }
  }

  await browser.close();
  process.exit(anyFlagged ? 1 : 0);
}

main();
