# Blinded bilingual adjudication for protocol v2

`adjudication_v2.py` prepares offline review materials and reconciles human labels.
It never assigns semantic labels, infers omissions, calls a model, or fabricates
reviewer identities. The unit tests contain synthetic software fixtures only.

## Coordinator: verify the execution artifacts

The builder consumes four existing artifacts. It executes no model and creates
no review labels:

| Input | Meaning |
| --- | --- |
| `--dataset` | Private protocol-v2 dataset, including bilingual reference claims |
| `--manifest` | Frozen attempt manifest from `execution_ledger.py freeze` |
| `--ledger` | Complete ledger from `execution_ledger.py import-records` |
| `--packets` | Blinded export from `execution_ledger.py export-adjudication` |

Each batch covers one frozen system configuration and its complete selected split
and replicate universe. Replicates use the ledger's **zero-based** numbering.
Build separate batches for separately frozen configurations. The old free-form
attempt adapter is no longer accepted.

The builder regenerates the selected model-input export from the private dataset
and verifies its hash against the frozen manifest. It rebuilds every attempt's
identity, checking case, prompt, exported-case and source-revision hashes, system
configuration hash, replicate, packet ID and private condition/pairing metadata.
It reconstructs the ledger from recorded responses/failures and requires exact
equality, including entry/hash-chain/response hashes, outcomes and denominators.
Finally it regenerates the valid-only blinded export and compares the complete
artifact, including source-ledger and packet-set hashes. Missing, duplicate, foreign,
changed or non-valid packets fail validation, even if their packet-set hash is
recomputed. Retain all four originals and raw response artifacts privately.

The configuration digest is validated as the frozen identity shared by attempts
and ledger entries. The manifest contains only selected configuration metadata;
independently recomputing that digest requires the original full system-config
file retained by the execution run. Hash linkage alone does not authenticate
who originally created an entirely replaced artifact set.

```powershell
python adjudication_v2.py build --dataset private/protocol-v2.json --manifest private/frozen-attempts.json --ledger private/execution-ledger.json --packets private/blinded-export.json --output-dir private/review-batch
```

The output directory must be new. Outputs are:

- `packet.json`: bilingual reference claims, evidence, untrusted data and response
  for **only ledger-valid outputs**, with fresh random opaque review and claim IDs.
  Reference authority and verification are visible because reviewers
  need them to judge preservation. Expected decisions and the evaluation policy
  are excluded.
- `reviewer-a.json` and `reviewer-b.json`: separate, independently shuffled blank
  forms, bound to the packet's SHA-256. No judgment or attestation is prefilled.
- `private-map.json`: coordinator-only mapping to original packet IDs, attempts,
  case IDs, system/configuration hash, zero-based replicates, conditions, splits,
  original claim IDs and raw responses/failures. It records dataset, frozen
  manifest, ledger and original packet-set hashes, plus every literal masking
  occurrence. Every non-valid attempt remains here with its original outcome,
  `review_id: null` and an empty claim map; it receives no semantic review row.

`gate_rejection` and `protective_rejection` remain distinct execution outcomes in
the ledger and private map. Neither enters human semantic review or agreement
counts. The same exclusion applies to every other non-valid execution outcome.
If the run has no valid output, the public packet and both forms contain empty
lists; the private map still preserves all attempts and execution counts. Empty
forms do not establish that a human review took place.

Only distribute the packet and a reviewer's own form. **Do not distribute the
whole output directory**: it contains the private map. Keep filenames, messages,
and distribution folders free of system and condition names. Do not send either
reviewer the other form or the execution ledger before both reviews are frozen.

The public review packet excludes system/configuration, original packet/attempt/
case/family, language-route, path/paired/stimulus metadata and expected decisions.
Even input/output-language fields are excluded. The builder uses explicit field
selection and replaces exact occurrences of known metadata identifiers and frozen
system metadata strings in visible text with `[MASKED]`, longest match first.
New review IDs are random, not derived from outcomes or the original packet ID;
paired variants have unrelated review and claim IDs. Actual text necessarily
reveals language, and identical evidence can still reveal related variants.

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

- Set the human judgment's `execution_outcome` to `valid` only when the output can
  be labeled reliably. This legacy judgment field describes review usability;
  it does not replace the execution outcome in the ledger.
- Each mapped claim has `source_claim_id` from the packet, `semantic_preserved`
  (boolean), `verification_relation` (`preserved`, `strengthened`, `demoted`), and
  `authority_relation` (`preserved`, `misattributed`, `demoted`). Map each reference
  claim at most once. Leave omitted reference claims out of the list; do not mark
  them preserved or invent substitute claim IDs.
- List unsupported additions as objects with one `text` field, quoting or clearly
  identifying each distinct unsupported claim. An empty list means none found.
- Record `downstream_decision` as `preserve_and_review` or `seek_corroboration`.
  If the required decision is absent or the output cannot be judged reliably,
  use `unadjudicable` and explain why.

An unusable human judgment has **only** `execution_outcome: "unadjudicable"`.
No semantic labels, unsupported additions or downstream decision are allowed.
The rationale remains alongside the judgment. Humans cannot label ledger gate/
protective rejections or other execution failures through these forms. Neither
the recorded valid outcome nor any semantic label is prefilled in the form.

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

Counts report exact whole-judgment and human review-usability agreement across
all distributed packets, which contain only ledger-valid outputs. The retained
`execution_outcome` count key refers to that human review field, not execution
denominators. For cases both reviewers call valid, counts also report claim presence,
unsupported-addition-list and downstream-decision agreement. Semantic, verification
and authority counts compare only claims mapped by both reviewers. Every count has
its own `compared` denominator; zero comparisons remain zero. Claim/list order and
rationale wording do not cause label disagreement; unsupported-claim text must match
exactly, so paraphrases require reconciliation. These are descriptive agreement
counts, not semantic quality estimates or chance-corrected reliability statistics.

## Private scoring handoff

The final file uses opaque IDs and is not a direct `protocol_v2.py score` input.
The coordinator joins it to `private-map.json` using non-null `review_id`, checks
matching `packet_sha256`, and translates mapped `source_claim_id` values through
`claim_map`. Retain original packet/attempt ID, configuration hash, case ID and
replicate. Carry every excluded execution outcome from the map into attempt-level
accounting without semantic labels. Keep ledger-valid but human-unadjudicable
cases distinguishable from non-valid execution outcomes; report both denominators.
The builder validates all original ledger bindings before this review begins.

The existing scorer requires exactly one row per manifest case. Prepare a complete
system/replicate slice and its matching dataset subset; never collapse attempts,
drop rejections or pool systems to make that constraint pass. Scoring/export of
reconciled results remains an explicit private handoff, not an automatic semantic
labeling step. Preserve the frozen initial reviews and original execution ledger.

No packets, review submissions or study results are committed by this workflow.
Keep working artifacts outside public version control unless separately reviewed
and approved for publication.
