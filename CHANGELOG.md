# Changelog

## 1.0.0 - 2026-02-13
- Upgraded web playground contracts to V2:
  - `PlaygroundConfigV2`, `PlaygroundRunResultV2`, and `PlaygroundExportBundleV2`.
  - Backward-compatible migration path for V1 config/bundle imports and share links.
- Refactored browser runtime architecture:
  - Added structured modules (`schemas`, `validation`, `errors`, `runtime`, `ui-results`).
  - Added web-worker backed Pyodide runtime execution with deterministic cancel behavior.
- Upgraded UX and publish workflows:
  - Guided 5-step workflow shell and quick-start preset cards.
  - Results tabs with overview, per-step, scenario comparison, interpretation.
  - Summary CSV copy/download and publication bundle export panel with citation metadata.
- Hardened trust and release guardrails:
  - Enhanced static headers with CSP and security policies.
  - Expanded smoke/contract tests plus deterministic playground runtime test.
  - Added JS unit tests (Vitest) and browser integration test suite (Playwright) scaffolding.
  - Added docs: user guide, reproducibility, and limitations.

## 0.3.0-demo - 2026-02-13
- Added publish-readiness controls to the web playground:
  - Validation before run with field-level errors.
  - Structured runtime errors and debug-report copy.
  - Run facts card with reproducibility metadata.
  - Import/export bundle and URL share support.
  - Replay last run and cancel control.
- Added static hosting and release artifacts:
  - `robots.txt`, `sitemap.xml`, `_headers`, `404.html`, and legal pages.
  - CI workflow for smoke and quality checks.
