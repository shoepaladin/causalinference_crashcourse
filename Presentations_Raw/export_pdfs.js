#!/usr/bin/env node
// Exports each built Updated_v2/*.slides.html reveal.js deck to a PDF
// (one physical page per slide) using Chromium's native print pipeline via
// reveal.js's own ?print-pdf mode. Requires `npm install` in this directory
// (or PLAYWRIGHT_CHROMIUM_PATH pointing at a local Chromium binary).
//
// Usage:
//   node export_pdfs.js                                   # export every deck
//   node export_pdfs.js "Updated_v2/1 Foundations 20230528 update.slides.html"

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

async function exportDeck(browser, htmlFile) {
  const outFile = htmlFile.replace(/\.slides\.html$/, '.pdf');
  const url = pathToFileURL(path.resolve(htmlFile)).href + '?print-pdf';
  const page = await browser.newPage({ viewport: { width: 1150, height: 740 } });
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500); // let MathJax finish rendering
  await page.pdf({ path: outFile, printBackground: true, preferCSSPageSize: true });
  await page.close();
  const { size } = fs.statSync(outFile);
  console.log(`${path.basename(outFile)}  (${(size / 1024).toFixed(0)} KB)`);
}

async function main() {
  const files = process.argv.length > 2 ? process.argv.slice(2) : listDecks();
  const browser = await chromium.launch({
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH || undefined,
  });

  for (const file of files) {
    await exportDeck(browser, file);
  }

  await browser.close();
}

main();
