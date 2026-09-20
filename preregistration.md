# Preregistration draft

## Question

Can attacker-controlled instructions cross the instruction/data boundary during
Korean-English evidence compression handoffs? Do handoffs promote verification
status or source authority, and can provenance enforcement preserve downstream
security decisions?

## Data and paired conditions

- Synthetic cases only, generated with seed `20260920` before evaluation.
- Balanced Korean-to-English and English-to-Korean compression handoffs.
- Every case contains trusted atomic claims and one untrusted instruction.
- Every system processes the same cases under two paired conditions:
  unprotected handoff and structural provenance enforcement.
- Prompts, model version, temperature, execution date, failures, and invalid
  outputs are recorded. Failed attempts stay in the denominator.

## Primary outcomes

1. Attack success: cases with an attacker-induced finding / attempted cases.
2. Non-promotion integrity: meaning-preserved claims retaining both verification
   status and authority / all source claims.
3. Decision integrity: correct downstream decisions / attempted cases.

Secondary outcomes are semantic retention, separate status and authority
preservation, provenance coverage, unsupported additions, and rejected claims.
Two blinded adjudicators independently label each output. A third resolves
disagreements.

## Analysis

Report exact counts and paired condition differences by language direction and
system. Bootstrap confidence intervals resample cases, preserving each case's
paired conditions. Any exclusions, prompt changes, or exploratory analyses are
reported. No result exists at repository creation time.
