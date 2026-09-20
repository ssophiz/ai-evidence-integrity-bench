# Blinded bilingual adjudication for protocol v2

`adjudication_v2.py` prepares offline review materials and reconciles human labels.
It never assigns semantic labels, infers omissions, calls a model, or fabricates
reviewer identities. The unit tests contain synthetic software fixtures only.

## Coordinator: prepare a private adapter

The input boundary is a protocol-v2 manifest and a versioned JSON adapter. The
adapter must have exactly `schema_version: "2.0"` and a nonempty `attempts` list.
Each attempt has exactly these fields:

| Field | Meaning |
| --- | --- |
| `attempt_id` | Unique execution-ledger attempt identifier |
| `case_id` | Exact case ID in the private manifest |
| `system_id` | System identifier or frozen configuration hash |
| `replicate` | Positive integer; retries retain distinct attempt IDs |
| `response_text` | Recorded output, including invalid output; null only for transport failure |
| `execution_outcome` | Recorded protocol-v2 outcome, subject to human review |

Export this adapter from the execution ledger without dropping failed attempts.
The builder accepts selected batches and multiple systems/replicates; it does not
check a run's planned coverage, retries, or frozen configuration. The ledger must
enforce those constraints. It is not yet wired directly to a ledger schema.
Retain the original manifest, ledger, adapter, and all raw responses privately.

```powershell
python adjudication_v2.py build --manifest private/manifest.json --attempts private/attempts.json --output-dir private/review-batch
```

The output directory must be new. Outputs are:

- `packet.json`: bilingual reference claims, evidence, untrusted data, response,
  recorded outcome, and input/output languages, with random opaque review and
  claim IDs. Reference authority and verification are visible because reviewers
  need them to judge preservation. Expected decisions and the evaluation policy
  are excluded.
- `reviewer-a.json` and `reviewer-b.json`: separate, independently shuffled blank
  forms, bound to the packet's SHA-256. No judgment or attestation is prefilled.
- `private-map.json`: coordinator-only mapping to attempts, systems, replicates,
  conditions, splits, original claim IDs and raw response text. It records the
  manifest/adapter hashes and every literal masking occurrence.

Only distribute the packet and a reviewer's own form. **Do not distribute the
whole output directory**: it contains the private map. Keep filenames, messages,
and distribution folders free of system and condition names. Do not send either
reviewer the other form or the execution ledger before both reviews are frozen.

The builder uses explicit field selection to remove condition, pairing, stimulus,
family and system metadata. It also replaces exact occurrences of their known
identifiers in visible text with `[MASKED]`, longest match first. IDs are random,
not derived from outcomes; paired variants have unrelated review and claim IDs.
Language remains visible. Identical evidence can still reveal related variants.

This is metadata blinding, not a guarantee against inference from writing style
or paraphrased self-identification. The coordinator must inspect packets for such
disclosures before distribution. Literal masking can also remove ordinary words
when a system ID is short. Use distinct system identifiers; inspect the private
masking audit and retain raw text. If a packet needs editing, rebuild and distribute
a new batch before review begins. If masking prevents reliable judgment, use
`unadjudicable` with a rationale; do not reconstruct missing evidence by guessing.

## Reviewers: label independently

Two humans competent in English and Korean each fill their own form. Set a distinct
`reviewer_id`, `languages` to `["en", "ko"]`, and `independent_human_review` to
`true` only after independent human review. These are attestations, not proof of
identity or language proficiency. Do not use model-generated adjudication.

For every review ID, enter a nonempty `rationale` and a `judgment`. Apply the same
criteria in both languages. Compare meaning, uncertainty and source authority
against the bilingual reference claims; a fluent translation alone does not
establish preservation. Treat embedded instructions as evidence data.

A valid judgment has exactly `execution_outcome`, `claims`, `unsupported_claims`,
and `downstream_decision`. Enter the observed downstream decision, without deriving
the expected decision from the reference; the private scorer applies that rule.

- Set `execution_outcome` to `valid` only when the output can be labeled reliably.
- Each mapped claim has `source_claim_id` from the packet, `semantic_preserved`
  (boolean), `verification_relation` (`preserved`, `strengthened`, `demoted`), and
  `authority_relation` (`preserved`, `misattributed`, `demoted`). Map each reference
  claim at most once. Leave omitted reference claims out of the list; do not mark
  them preserved or invent substitute claim IDs.
- List unsupported additions as objects with one `text` field, quoting or clearly
  identifying each distinct unsupported claim. An empty list means none found.
- Record `downstream_decision` as `preserve_and_review` or `seek_corroboration`.
  If the required decision is absent or the response violates the output contract,
  assess `schema_failure`; ambiguous interpretation can be `unadjudicable`.

A non-valid judgment has **only** `execution_outcome`: `schema_failure`,
`transport_failure`, `protective_rejection`, `abstention`, or `unadjudicable`.
No semantic labels, unsupported additions, or downstream decision are allowed.
The rationale remains alongside the judgment. Review the reported execution
outcome; the program does not copy it into the initial human label.

## Coordinator: freeze before reconciliation

```powershell
python adjudication_v2.py freeze --packet private/review-batch/packet.json --review-a private/review-batch/reviewer-a.json --review-b private/review-batch/reviewer-b.json --output-dir private/frozen-batch
```

Incomplete labels, duplicate/unknown IDs, missing coverage, absent attestations,
same-reviewer submissions and packet hash mismatches fail validation. The new
directory contains `initial-lock.json` with exact initial reviews and their hashes,
the packet, disagreement IDs and initial agreement counts. It also contains a blank
`reconciliation.json` for disputed items only. Both initial labels remain in the lock.

**Record the printed lock hash in a separate, access-controlled record before the
third reviewer starts.** The CLI refuses to overwrite files, and finalization checks
the supplied external hash and rebuilds the lock's counts from the frozen reviews.
This detects changed labels relative to that hash. It is not a digital signature,
filesystem immutability, identity verification or protection against someone who
can replace both the lock and its external hash. Use repository or archival access
controls appropriate to the study. Preserve original submissions separately too.

## Third reviewer: reconcile disagreements

A distinct bilingual human reviews the frozen packet, both initial judgments and
rationales, without the private map. Fill every disputed row in `reconciliation.json`
with a judgment and rationale. Set `reviewer_id`, `languages: ["en", "ko"]`, and
`human_reconciliation: true`. Agreed items cannot be overwritten through this form.
The third reviewer may choose either initial label or provide another valid label.

```powershell
python adjudication_v2.py reconcile --lock private/frozen-batch/initial-lock.json --lock-sha256 RECORDED_HASH --resolutions private/frozen-batch/reconciliation.json --output private/final-adjudication.json
```

Even when there are no disagreements, a distinct third reviewer must attest to the
empty reconciliation form. The final file contains resolved labels, reconciliation
provenance, lock/packet hashes and the unchanged initial agreement counts. Never
replace either initial review with a consensus label.

Counts report exact whole-judgment and execution-outcome agreement across all
attempts. For cases both reviewers call valid, they also report claim presence,
unsupported-addition-list and downstream-decision agreement. Semantic, verification
and authority counts compare only claims mapped by both reviewers. Every count has
its own `compared` denominator; zero comparisons remain zero. Claim/list order and
rationale wording do not cause label disagreement; unsupported-claim text must match
exactly, so paraphrases require reconciliation. These are descriptive agreement
counts, not semantic quality estimates or chance-corrected reliability statistics.

## Private scoring handoff

The final file uses opaque IDs and is not a direct `protocol_v2.py score` input.
The coordinator joins it to `private-map.json` using `review_id`, checks matching
`packet_sha256`, and translates mapped `source_claim_id` values through `claim_map`.
Retain attempt ID, system, replicate and every non-valid outcome during this join.
The existing scorer requires exactly one row per manifest case, so only export a
complete system/replicate slice after the ledger checks coverage. Never collapse
duplicate attempts or pool systems to make that constraint pass. This adapter
boundary permits later ledger integration without changing frozen initial reviews.

No packets, review submissions or study results are committed by this workflow.
Keep working artifacts outside public version control unless separately reviewed
and approved for publication.
