# AI Evidence Integrity Bench

A synthetic AI security benchmark for claim-level trust failures in bilingual
AI-assisted evidence pipelines. It tests Korean-English compression handoffs,
where attacker-controlled text may be promoted into a finding or a low-authority,
unverified claim may be silently promoted during an agent-to-agent handoff.

The scorer consumes **blinded human adjudications**. It does not use string
matching as a substitute for semantic review or let a model grade itself.

## Security contribution

- Fixed-seed trusted claims with verification status and authority tier.
- Attacker-controlled instructions embedded inside evidence data.
- Paired unprotected and provenance-enforced handoff conditions.
- Metrics for authority/status non-promotion, attacker-induced claims, and
  downstream security decision integrity.
- A structural allowlist baseline, `enforce_provenance`, which rejects unknown
  claim IDs. It cannot establish semantic faithfulness by itself.

Read [the threat model](THREAT_MODEL.md) and [schema](docs/schema.md) first.

## Quick start

Requires Git and Python 3.10 or newer. The benchmark, tests, and offline demo
use only the Python standard library; no packages or model credentials are
needed for the demo.

```powershell
git clone https://github.com/ssophiz/ai-evidence-integrity-bench.git
cd ai-evidence-integrity-bench
python --version
python -m unittest discover -s tests -v
python arsenal_demo.py
```

Open <http://127.0.0.1:8765/>. The deterministic synthetic fixture compares
an unprotected handoff with the structural provenance gate. Semantic review
remains pending (0/1 complete); the displayed decisions are authored examples
and policy targets. The demo makes no external requests or model calls.
Stop the server with Ctrl+C.

For presentation and evidence export instructions, see the
[presenter runbook](docs/presenter-runbook.md).

## Benchmark workflow

Generate the synthetic cases from the repository root:

```powershell
python provenance_bench.py generate --output data/cases.json
```

The next commands require files you supply. `raw_outputs.json` contains the
system outputs for these cases; `adjudications.json` contains the blinded human
reviews described in the [schema](docs/schema.md). Neither file is included or
created by `generate`, and the demo fixture is not a substitute for either.
Collect the outputs and complete the human review before running these steps:

```powershell
python provenance_bench.py enforce --cases data/cases.json --submissions raw_outputs.json --output enforced_outputs.json
python provenance_bench.py score --cases data/cases.json --adjudications adjudications.json --output report.json
```

The [preregistration](preregistration.md) fixes denominators and analysis before
evaluation. [Ethics boundaries](ETHICS.md) prohibit private evidence and live
targets. This repository ships no model results or performance claims.

## Limits

The stimuli are controlled and synthetic. Results cannot establish field
performance, legal reliability, or operational safety. A valid provenance ID
does not prove that rendered text preserves its meaning, verification status,
or authority.

See [CONTRIBUTING.md](CONTRIBUTING.md) for changes and reports, and
[SECURITY.md](SECURITY.md) for security reporting. MIT licensed.
