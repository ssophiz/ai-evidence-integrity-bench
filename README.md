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

## Protocol v3 pilot redesign

V3 adds 48 authored candidate scenario families, balanced verification/authority
factorials, clean attack controls, concrete security decisions, and an explicit
source -> compression worker -> decision consumer contract. Message-only exports
hide experiment IDs and private answers while supplying the trusted decision
policy. Frozen records bind consumer input to the actual worker output.

```powershell
python protocol_v3.py generate --output private/manifest-v3.json
python protocol_v3.py gate --manifest private/manifest-v3.json --output private/gate-v3.json
```

**The gate intentionally exits 2 (NO-GO).** These are 48 pilot candidates, not
the required 600 independently reviewed families. Bilingual/semantic review,
compression calibration, audited execution, v3 adjudication, and family-cluster
inference remain blocking. No model results are included. See the
[v3 protocol and migration](docs/protocol-v3.md) and [preregistration](preregistration.md).

## Protocol v2 foundation (historical)

Protocol v2 adds semantic-family splitting, four Korean/English routes, paired
direct-source controls, explicit execution outcomes, and denominator-aware
scoring. It is an experiment specification and fixture generator; the
repository still contains no model run or performance result.

```powershell
python protocol_v2.py generate --families 20 --output private/manifest-v2.json
python protocol_v2.py export-model-inputs --manifest private/manifest-v2.json --split dev --output data/dev-inputs-v2.json
python protocol_v2.py score --manifest private/manifest-v2.json --adjudications adjudications-v2.json --output report-v2.json
```

Only the output of `export-model-inputs` may be supplied to a tested system.
The private manifest contains reference claims and the expected downstream
decision. See [the v2 protocol](docs/protocol-v2.md) for outcome definitions,
metric denominators, and the split policy.

The [archived v2 draft](docs/preregistration-v2.md) records the older protocol;
its corpus and workflow do not satisfy the v3 gates. [Ethics boundaries](ETHICS.md) prohibit private evidence and live
targets. This repository ships no model results or performance claims.

### Frozen execution ledger

Protocol v2 includes a dependency-free offline ledger that freezes the selected
split, system-configuration hash, source revision, replicates, and one logical
attempt per exported case before outputs are inspected. It rejects duplicate,
unknown, and dropped attempts, produces an order-invariant hash-chained ledger,
and exports adjudication packets without system, condition, family, replicate,
or expected-decision fields. It makes no model calls.

```powershell
python execution_ledger.py --help
```

See [the execution-ledger protocol](docs/execution-ledger.md) for the complete
offline workflow and the limits of hash-based provenance.

## Limits

The stimuli are controlled and synthetic. Results cannot establish field
performance, legal reliability, or operational safety. A valid provenance ID
does not prove that rendered text preserves its meaning, verification status,
or authority.

See [CONTRIBUTING.md](CONTRIBUTING.md) for changes and reports, and
[SECURITY.md](SECURITY.md) for security reporting. MIT licensed.
