# Offline demo presenter runbook

Use this ten-minute demonstration to explain what a claim-ID gate checks and why accepted text still needs semantic review. The example is like attaching the right document reference to the wrong conclusion: a valid reference alone does not make the conclusion faithful.

This is an operating guide for the repository demo, not conference submission text. Keep the [verification checklist](demo-verification-checklist.md) with the presentation laptop.

## Prepare the laptop

Use a checked-out revision of this repository, Python 3.10 or later, and a browser with Korean fonts. The demo uses the Python standard library. Once these are available locally, it requires no external service, API key, model, or package download. Browser traffic goes to the local server.

Run these commands from the repository root before leaving for the venue:

```powershell
python --version
git rev-parse HEAD
git status --short
python -m unittest discover -s tests -v
python arsenal_demo.py --host 127.0.0.1 --port 8765
```

Keep that terminal open. In a second terminal, verify the running server:

```powershell
python -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:8765/healthz', timeout=5).read().decode(), end='')"
```

The health response must be `ok`. Open <http://127.0.0.1:8765/> in the browser. Start at 100% zoom; use a viewport wider than 760 CSS pixels for the side-by-side comparison. Check the Korean paragraph on the actual projector and increase zoom if the text is too small. At narrower widths, the panels stack vertically.

Prepare the evidence export below and open its `demo.html` while disconnected from the network. Keep this file and the screenshots on the laptop. Rehearse the full flow once in this condition.

## Ten-minute flow

| Time | Presenter action | Point to establish |
| --- | --- | --- |
| 0:00–1:00 | Show the title and fixture label. | This is one designed, deterministic synthetic case. The displayed claims were supplied by the demo author; they are not recorded model responses. |
| 1:00–2:30 | Select **1. Inspect inputs** and read the trusted note in English and Korean. Point to `reported` and `analyst_note`. | The source reports that a service account copied a log bundle. It does not establish verified unauthorized access. |
| 2:30–3:30 | Show the untrusted evidence field. | Instructions inside acquired evidence must remain data. The markup-looking text is displayed literally. |
| 3:30–5:00 | Select **2. Compare paths**. Inspect both claims in Path A. | The supplied unchecked handoff contains an unknown source ID and a known ID attached to promoted meaning, verification status, and authority. |
| 5:00–6:30 | Inspect the rejected and accepted cards in Path B. | The actual structural gate rejects the unknown ID and accepts the known ID. The accepted text still overstates its source. |
| 6:30–7:30 | Show the decision labels and fixture accounting. | The trusted case's policy requires `seek_corroboration`. Semantic review is still missing: completed 0/1, missing outcome 1/1. No completed human review or model decision was measured here. |
| 7:30–8:30 | Select **3. Review limits**, then open the disclosure if it is collapsed. | The gate checks membership in a trusted manifest. It does not establish faithful translation or preserved meaning, status, or authority. |
| 8:30–9:30 | Show the saved HTML and JSON evidence files. | A reviewer can inspect the exact fixture and structural result without a model account or external connection. |
| 9:30–10:00 | Return to the input view and state the next research step. | Paired model evaluation and blinded human adjudication are required before reporting model-performance results. Refer to the [preregistration](../preregistration.md). |

The current page labels Path A's illustrative action **Downstream decision produced** and Path B's illustrative expected-policy branch **Downstream decision after review**. Explain that these labels are part of the authored illustration. No downstream model runs, and no semantic adjudication has been completed. The 0/1 review count governs the interpretation.

## Claims to use precisely

| Supported wording | Boundary to preserve |
| --- | --- |
| “This fixture passes two authored claims through the structural gate.” | It is one synthetic case, not a sampled attack dataset or model trial. |
| “The gate rejects the one unknown ID and accepts the one known ID.” | The counts are fixture accounting, not a 100% defense-success estimate. |
| “The accepted claim still promotes meaning, status, and authority.” | Known provenance does not establish semantic faithfulness. |
| “The expected source-grounded decision is seek_corroboration.” | A displayed policy target is not an observed downstream outcome. |
| “The page displays English and Korean source text.” | The demo does not run a translation model or measure bilingual quality. |
| “Human semantic review remains outstanding.” | Do not turn missing adjudication into a pass, a zero-failure claim, or a safety rate. |
| “The demo runs locally without external requests or model calls.” | The live browser still makes local HTTP requests to the Python server. |

This demonstration supplies no evidence of production attack prevalence, model rankings, causal defense effectiveness, operational safety, or legal or forensic reliability. The [threat model](../THREAT_MODEL.md) defines the intended research boundary.

## Reset and offline fallback

**Reset view** loads `/` again. The page has no session state or model history; refreshing returns the same fixture. This is a view reset, not a new experimental trial. To reset the server, press Ctrl+C in its terminal, rerun the launch command, and reload the browser.

If the server cannot run, open the saved `demo.html` directly. Its styles and fixture text are self-contained. The section links work within the file; use browser reload to reset because **Reset view** points to `/`, which is intended for the local server. If the browser or projector fails, use the prepared screenshots and identify them as saved captures of the same revision.

## Export the demonstration evidence

Run this PowerShell block from the repository root before the presentation. It creates a new `demo-evidence` directory and stops if that directory already exists, protecting an earlier capture. Choose a new directory name in the block for each later rehearsal or revision.

```powershell
@'
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from arsenal_demo import demo_data, render_demo

out = Path('demo-evidence')
out.mkdir()
(out / 'demo.html').write_bytes(render_demo())
(out / 'fixture.json').write_text(
    json.dumps(demo_data(), ensure_ascii=False, indent=2) + '\n',
    encoding='utf-8',
)
manifest = {
    'capture_time_utc': datetime.now(timezone.utc).isoformat(),
    'git_revision': subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], text=True).strip(),
    'git_status': subprocess.check_output(
        ['git', 'status', '--short', '--untracked-files=no'], text=True),
    'python_version': platform.python_version(),
    'platform': platform.platform(),
    'kind': 'deterministic synthetic demonstration; no model results',
    'sha256': {
        name: hashlib.sha256((out / name).read_bytes()).hexdigest()
        for name in ('demo.html', 'fixture.json')
    },
}
(out / 'manifest.json').write_text(
    json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(out.resolve())
'@ | python -
```

`fixture.json` contains the case, authored unchecked claims, accepted claims, and rejected claims returned by the demo. It is not an adjudication file and must not be passed off as scorer input or a benchmark report. The manifest records tracked changes; check full `git status --short` separately and use a clean source checkout for an attributable release capture. A hash detects later file changes; it does not validate the research claim.

Keep test output, the completed checklist, and screenshots beside these files. Record the browser version, viewport, and whether each capture used the server or the saved HTML. Inspect the bundle for unrelated terminal tabs, personal paths, notifications, or account information before sharing.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `python` is unavailable. | Use the Python installation prepared during rehearsal, or show the saved HTML and screenshots. |
| `ModuleNotFoundError` for `arsenal_demo` or `provenance_bench`. | Run from the repository root and check that both source files are present. |
| The port is already in use. | Stop your own earlier demo process, or launch with `--port 8766` and update both browser and health-check URLs. |
| The browser cannot connect. | Check that the server terminal is still running and that the URL uses `http`, the selected port, and `127.0.0.1`. |
| Korean text appears as boxes. | Select a browser/system font with Korean glyphs or use screenshots prepared on the presentation machine. The source and exported HTML use UTF-8. |
| **Review limits** scrolls but does not open the text. | Click the disclosure heading after following the section link. |
| Refresh appears to rerun the same result. | That is expected: this fixture is deterministic and has no model calls. |
| The export reports that `demo-evidence` exists. | Use a new capture directory name; retain the earlier bundle. |
| Results or labels differ from the checklist. | Record the revision and reconcile the checklist against that source before presenting. Do not describe a changed fixture using old counts. |
