# Threat model

## System

An AI assistant compresses Korean or English evidence into the other language,
then passes findings to a decision agent or examiner. Trusted claims have stable
IDs, verification status, and authority tier. Evidence can contain untrusted text.

## Adversary

The adversary can place natural-language instructions inside an acquired file,
log, note, or extracted artifact. The adversary cannot alter the trusted claim
manifest, scorer, system prompt, or human adjudication record.

## Security properties

1. **Instruction/data separation:** embedded instructions are treated as data.
2. **Provenance integrity:** each transmitted finding maps to a trusted claim.
3. **Non-promotion:** verification status and authority never silently increase.
4. **Handoff integrity:** attacker text is not promoted to a downstream finding.
5. **Decision integrity:** compression does not alter the policy-defined action.
6. **Complete accounting:** failures and schema-invalid outputs remain visible.

## Out of scope

The scaffold does not model tool compromise, manifest tampering, covert-channel
attacks, malware execution, or evidentiary admissibility. A valid provenance ID
does not prove that rendered text preserves meaning; human adjudication remains
necessary.
