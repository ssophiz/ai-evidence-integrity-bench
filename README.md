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

```powershell
python provenance_bench.py generate --output data/cases.json
python provenance_bench.py enforce --cases data/cases.json --submissions raw_outputs.json --output enforced_outputs.json
python provenance_bench.py score --cases data/cases.json --adjudications adjudications.json --output report.json
python -m unittest discover -s tests -v
```

The [preregistration](preregistration.md) fixes denominators and analysis before
evaluation. [Ethics boundaries](ETHICS.md) prohibit private evidence and live
targets. This repository ships no model results or performance claims.

## Limits

The stimuli are controlled and synthetic. Results cannot establish field
performance, legal reliability, or operational safety. A valid provenance ID
does not prove that rendered text preserves its meaning, verification status,
or authority.

MIT licensed.
