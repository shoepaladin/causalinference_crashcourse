# Finding copies of this material

Attribution only helps if you occasionally look. These are the queries worth
running; nothing here needs any tooling beyond a browser.

## Canary tokens

Every stamped artifact carries a short token (`attr-` plus eight hex digits).
The token-to-file mapping is in `.attribution/canaries.json`, which is
gitignored on purpose -- it is your detection key and should not travel with
the thing being copied. Any hit on one of these is a copy of your file, not a
coincidence.

- GitHub code search: `"attr-" AND "https://github.com/shoepaladin/causalinference_crashcourse"`
- GitHub code search, one token at a time: `"attr-1a2b3c4d"` (substitute real ones)
- Web: `"attr-1a2b3c4d"`

## Authorship strings

- GitHub: `"SPDX-FileCopyrightText" "Julian Hsu"`
- GitHub: `"hsu.julian.econ@gmail.com"`
- GitHub: `"https://github.com/shoepaladin/causalinference_crashcourse" -repo:shoepaladin/causalinference_crashcourse`
- Web: `"Causal Inference Crash Course" "Julian Hsu"`
- Web, for lifted PDFs: `"Causal Inference Crash Course" filetype:pdf`

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
