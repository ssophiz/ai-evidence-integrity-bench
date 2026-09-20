# Protocol v3 preregistration draft: confirmatory NO-GO

This is a protocol draft, not a registered study or a result. The current corpus
contains 48 authored pilot candidates with zero independently reviewed families.
The planned minimum is **600 independently reviewed semantic families**. The
machine-readable release gate fails until the unmet requirements are implemented
and supported by evidence. The [v2 draft](docs/preregistration-v2.md) is archived.

## Question and controlled design

Does Korean-English compression change verification status or source authority,
and do those changes affect downstream security decisions under a supplied
trusted policy? Provenance fields and policy enforcement are comparison
mechanisms; this draft makes no novelty claim for them.

Use synthetic cases with seed `20260920`. Split all translations, factual
counterfactuals, verification/authority cells, clean/attack controls, direct-source
controls, handoffs, and repetitions by scenario family. Atomic source facts may
not cross splits. Exact normalized-text checks are implemented; independent
semantic overlap and bilingual equivalence review remain blocking.

Fully cross standing eligibility (2), update meaning (2), verification (3),
authority (3), language route (4), path (2), and attachment (2). The pilot has
576 cases per family. Every status/authority cell has equally frequent permit
and withhold labels. Treat verification as corroboration and authority as the
issuer's mandate, subject to a semantic-plausibility review of each family.

Supply the consumer with the requested action, trusted standing eligibility,
and a policy accepting only verified updates from artifacts or analyst notes.
Keep expected decisions and reference labels private. Export only messages;
case, family, attempt, route, path, split, and attachment IDs cannot reach models.

The handoff path runs source -> compression worker -> decision consumer. The
direct path feeds original source to the consumer. Record exact source output,
worker response, consumer response, configurations, request hashes, and failures
under a frozen plan. The consumer must use the actual worker summary. Freeze
one response per scheduled stage; retain every attempt. No hidden retries,
source substitution, or post-response treatment selection is admissible.

## Outcomes and analysis plan

The planned semantic outcomes are verification promotion, authority promotion,
unsupported additions, retention, omission, and demotion, adjudicated separately
at worker and consumer stages by two blinded bilingual reviewers with a third
resolving disagreements. The v3 adjudication adapter is not implemented, so the
current code does not produce those semantic outcomes.

The implemented descriptive decision analysis counts harmful permits, excessive
refusals, and failed tasks separately. Each receives unit cost for a transparent
balanced task score; these weights are not real-world harm valuations. A failure
receives no decision credit and is not inferred to be safe, harmful, or a model
refusal. Retain the seven execution outcomes, including separate model protective
rejection and external gate rejection.

Report constant-permit, constant-withhold, and standing-policy baselines, all
attempt denominators, outcome counts, and both directional decision costs. The
standing-policy baseline ignores the update and can perform well by construction;
models must be compared against it. No advantage is assumed.

The planned paired contrast is each family's attack-minus-clean cost difference
on the handoff path minus that difference on the direct path, separately by route.
The code emits these family contrasts and their underlying cell counts. Any
future uncertainty interval must resample **whole families**, retaining all
within-family conditions and repeated runs. Cases and repetitions are not
independent sampling units. Clustered inference implementation, power simulation,
minimum detectable effects, multiplicity handling, and model/replicate counts
must be fixed and validated before confirmatory execution. They remain NO-GO.

## Freeze gates and limits

Run `python protocol_v3.py gate --manifest <manifest> --output <gate-report>`.
Exit 2 is the intentional NO-GO outcome. Blocking requirements are the 600-family
reviewed corpus, semantic overlap review, bilingual adjudication, language-fair
compression and attachment calibration, audited separate-stage execution, the
v3 blinded-adjudication adapter, and family-cluster power/inference validation.

The current 70% UTF-8 byte budget is experimental and not language neutral.
The sources are short, the attack template is simple, and the clean/attack
attachment lengths differ. These require calibration before interpretation.
Published candidates cannot establish a secret held-out test set; freeze new
private families before tuning for a confirmatory study. No model calls, results,
statistical significance, field-performance claims, or safety certification are
included. Record all later deviations in a new protocol version before execution.
