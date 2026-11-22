# Inner-page screenshot evidence

Before: c3b95c6618053e3e82922dab55bbece4173ea84d (main, including merged redesign #32).
After: 6df1bfe on feat/inner-pages.

Seven pages, two widths (1440 and 390px), before and after: 28 full-page PNGs.
Open index.html for paired comparisons. The images are kept on this evidence branch to keep the application PR focused on source changes.

Data and state: apps/web/tests/fixtures.ts, Latin script, one milk item (8600000000001, quantity 1) in local storage, assistant disabled, fixed browser time 2026-11-22T12:00:00+01:00. No live prices are used.

To capture the final pages from the application branch, set SCREENSHOT_DIR to an absolute output directory and run npm --prefix apps/web run e2e -- tests/inner-pages.spec.ts. The same fixture capture loop was used before page modifications. The new behavior tests are intended for the final implementation.

Baseline checks found one existing accessibility violation on the Quality page at 390px: the horizontal table region was not keyboard focusable. Final captures pass accessibility checks on all seven pages at both widths. Final layouts were visually inspected; Product prices and Basket totals were adjusted after mobile review.

Validation: lint and typecheck pass; 24 unit tests pass; build and size pass; 43 browser tests pass. Home initial JavaScript decreased from 105864 to 105648 gzip bytes (103.4 to 103.2 KiB), under the 105 KiB budget.
