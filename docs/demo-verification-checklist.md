# Demo verification checklist

Complete this checklist on the presentation laptop against the revision being shown. An unchecked box is outstanding work, not a passing result. Follow the [presenter runbook](presenter-runbook.md) for commands and the ten-minute flow.

Record: date and time, operator, Git revision, source changes, Python version, browser/version, viewport, selected port, and capture directory.

## Rehearsal gates

- [ ] The repository revision is recorded, and `git status --short` has been reviewed for changes that affect the demonstration.
- [ ] `python -m unittest discover -s tests -v` completes successfully; its output is saved with the capture.
- [ ] The server starts on `127.0.0.1` at the recorded port, and `/healthz` returns `ok`.
- [ ] The title, synthetic-fixture label, source text in both languages, comparison cards, and accounting are readable on the actual display.
- [ ] All three navigation links reach their sections. The limits disclosure opens by clicking its heading.
- [ ] The trusted source has status `reported` and authority `analyst_note`.
- [ ] Path A displays two authored claims, including one with an unknown ID and one with the trusted ID attached to promoted text.
- [ ] Path B rejects `attacker-injected-claim` and accepts `arsenal-synthetic-001-claim-1`.
- [ ] The accepted claim still shows promoted status `verified` and authority `artifact`; the semantic-review warning remains visible.
- [ ] The structural counts are unknown IDs rejected 1/1 and known IDs accepted 1/1.
- [ ] Semantic accounting is completed 0/1 and missing outcome 1/1. No safety rate is presented.
- [ ] Path B labels its downstream decision as conditional on rejecting semantic promotion. Both paths separately show the expected policy decision; the presenter explains that semantic review is pending and no downstream model action was measured.
- [ ] The embedded markup is visible as text and does not execute in the browser.
- [ ] **Reset view** and reload restore the same fixture on the server; no new trial is claimed.
- [ ] The ten-minute flow has been rehearsed, including the missing-review limitation and the distinction between structural acceptance and semantic faithfulness.

## Offline fallback and evidence

- [ ] `demo.html`, `fixture.json`, and `manifest.json` were exported together from the recorded source revision.
- [ ] The exported JSON parses, and the manifest's SHA-256 values match the two exported files.
- [ ] The saved HTML opens and displays the same fixture without an external connection or a running demo server.
- [ ] The presenter uses browser reload for the saved file, because its **Reset view** link targets the server root.
- [ ] The JSON is labeled as a synthetic fixture export, not model output, adjudication, or a benchmark score.
- [ ] Test output, this completed checklist, browser/display details, and screenshots accompany the export.
- [ ] The sharing copy contains only intended synthetic evidence and presentation metadata.

## Screenshot plan

Capture the actual rendered page. Keep original images and record the revision and viewport; if an image is cropped for a slide, retain its uncropped original. Do not remove the fixture label or missing-review limitation from any presentation that uses the screenshots.

| Filename | Frame | Verification purpose |
| --- | --- | --- |
| `01-source-and-context.png` | Title, synthetic-fixture label, and both source panels. | Establish the authored example and the source's original status and authority. |
| `02-path-comparison.png` | Both path panels, including accepted and rejected claims and the semantic-review warning. | Show that an unknown ID is rejected while a known ID can still carry promoted content. |
| `03-accounting-and-limits.png` | Fixture counts and expanded limits disclosure. | Preserve the 0/1 completed reviews, missing outcome, and absence of a safety-rate claim. |
| `04-narrow-layout.png` | A narrow viewport with the panels stacked and labels readable. | Check presentation fallback on a smaller screen without horizontal clipping. |

Screenshots show the interface, not model performance or completed adjudication. A checklist pass confirms readiness to present this fixture; it does not establish effectiveness beyond it.
