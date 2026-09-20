# Paper outline and study commitments

The proposed study measures whether verification status, source authority, and meaning survive bilingual agent handoffs, and evaluates a provenance monitor under explicit trust assumptions. Non-promotion is an established integrity principle, and PPMF already applies source-authority non-amplification to lossy LLM memory consolidation. The study must establish its contribution through a distinct measurement or supported result, rather than claiming this principle or a typed monitor as new. A valid source ID alone cannot establish semantic preservation for free-form text. [PPMF, Sections 3–4 and Appendix A](https://arxiv.org/abs/2607.29167v1); [Fides](https://arxiv.org/abs/2505.23643).

## Claim and threat model

The attacker controls text in a synthetic acquired document, log, note, or extraction result. The attacker seeks an unsupported finding, stronger status or authority, or a changed downstream decision. The protected assets are the provenance record and policy-defined decision. The attacker cannot modify the trusted manifest, system policy, monitor, scorer, or adjudication records. Evaluate only isolated synthetic workflows with inert decisions.

Use "provenance laundering" as terminology connected to prior work: an untrusted statement gains apparent authority after transformation and downstream reuse. PPMF studies this failure across memory consolidation and later action authorization. Here, trace each source-to-summary-to-decision boundary, including Korean-English transformations. Test whether distinguishing verification status from authority and measuring meaning across language routes provides additional evidence beyond that prior setting. Establish practicality through representative evidence formats and ordinary pipeline configurations; state the limits of synthetic realism and the absence of field validation. [Memory provenance laundering](https://arxiv.org/abs/2607.29167v1); [evidence-borne forensic injection](https://dfrws.org/presentation/evidence-borne-prompt-injection-in-llm-assisted-textual-evidence-triage/).

The proposed typed provenance reference monitor runs outside the model at every handoff and decision input. A finding carries a claim ID, source binding, verification status, authority tier, and transformation lineage. A trusted policy defines allowed status transitions and an authority partial order; incomparable sources cannot silently replace each other. Accepted outputs must remain within the source's status and authority bounds. Malformed records, missing lineage, unknown claims, or unauthorized promotion fail closed with a recorded outcome.

The trusted computing base comprises the manifest, parser, monitor, decision adapter, and policy. The monitor must reconstruct protected metadata from trusted records, mediate every path, and prevent unvalidated prose from driving decisions. Separate implementation tests of these invariants from empirical semantic review. Retaining a genuine ID while changing its meaning is a central negative test. Free-form explanation remains untrusted; if the decision agent consumes it as authority, the formal guarantee does not apply. Any permitted promotion requires a separately authenticated verification event outside the present threat model.

Before selecting defense baselines, map this design to PPMF's claim-level support binding and trusted authority labels, Fides and CaMeL's information-flow controls, Prompt Flow Integrity's privilege boundary, and ControlValve's inter-agent control-flow enforcement. State which mechanism is adopted, adapted, or separately implemented. Source binding, transformation lineage, authenticated upgrades, and deterministic gating cannot by themselves establish novelty. Compare compatible controls under matched assumptions; record an implementation mismatch explicitly. [Comparison matrix](literature-matrix.md).

## Proposed preregistration amendment

Freeze the following before confirmatory execution. This package does not silently replace the existing protocol's data model or analysis.

The current scaffold has blocking design limitations. Six fixed atomic facts permit only 20 distinct three-fact combinations, with a 16/4 decision split that allows an 80% constant-policy baseline. Atomic facts recur across splits even if whole combinations are unique. Authority and verification status are confounded with source type. Direct and handoff model inputs currently differ only in their case ID, so those rows do not implement a causal handoff comparison. The existing case-level bootstrap also ignores family dependence, and the runner lacks the hidden downstream policy. None of these issues is resolved by this documentation.

Before registration, redesign the corpus to support genuinely diverse held-out facts and balanced outcomes, vary status and authority independently of source type, implement actual upstream transformations, and define the legitimate task policy delivered to the runner separately from sealed answer labels. Reconcile this change with the existing protocol, which excludes its evaluation policy from model inputs. Validate each change on development data before freezing the amended study.

| Item | Required commitment |
| --- | --- |
| Independent cases | At least 600 semantic families: 120 development, 120 pilot, and 360 sealed confirmatory families. Translations and variants are repeated observations, not additional independent cases. If the existing generator cannot supply enough distinct families, expand and validate it before freezing. |
| Coverage | Balance the four Korean/English input-output routes and the downstream policy outcomes. Keep all translations, benign controls, and attack variants of a family in one split. Audit semantic and template overlap, not just byte duplicates. |
| Models | At least four materially different model families, including at least one locally run open-weight family. Publish the family rationale, exact versions or weight hashes, inference runtime, quantization, context limits, and access constraints. Multiple sizes or API aliases from one lineage count as one family. |
| Conditions | Pair benign and attacked inputs; pair direct-source control with one and multiple agent handoffs; cross these with unprotected, prompt-only boundary instructions, the existing ID allowlist, and the full monitor. Keep the legitimate task and evidence fixed. |
| Configuration | Freeze role prompts, agent topology, compression budgets, decoding parameters, seeds where supported, tool schemas, retries, timeouts, concurrency, and model versions. Randomize paired run order and interleave conditions in comparable time blocks. Record changes as deviations. |
| Repetition | Preregister repeated runs and a precision calculation using pilot family-level variability. Do not claim that deterministic decoding removes API nondeterminism. Fix the confirmatory sample and stopping rule before unsealing. |
| Holdout | Seal the 360-family test manifest. Perform one confirmatory run and one independently scheduled rerun under the frozen configuration; report both, including drift or unavailable model versions. Never tune on either test result. |

The attack taxonomy covers **direct**, **indirect**, **multi-hop**, **obfuscated**, and **adaptive** conditions. Direct instruction-conflict tests are a diagnostic comparison outside the evidence-only attacker surface; label that scope difference. Indirect tests place untrusted text in evidence, multi-hop tests follow its passage through successive agents, and obfuscated tests vary representation while preserving a human-readable intended meaning. These categories may overlap; preregister the assignment and coverage table.

Adaptive evaluation must assess the final defense with its policy visible to the evaluator. Predeclare evaluator access, feedback, total query and time budgets, stopping rules, and development/test separation. Retain the complete attempt and selection history. Freeze the resulting evaluation set before the sealed run. Report fixed-suite and adaptive results separately. No production targets, external actions, or operational attack tooling belong in this study package.

## Outcomes and denominators

Every scheduled run and actual attempt must be accounted for. The current offline ledger freezes one request with zero retries per attempt and rejects recorded retries; retain that rule unless a preregistered extension records every additional request and its resource use. Assign exactly one existing execution outcome: valid, schema failure, transport failure, gate rejection, protective rejection, abstention, or unadjudicable. External gate rejection must remain separate from model protective rejection. Non-valid outputs receive no semantic labels; report unresolved runs and missing pairs explicitly. Preserve the original execution outcome when a ledger-valid response is later judged unadjudicable, and report both execution and review usability denominators.

| Measure | Definition and reporting rule |
| --- | --- |
| Attack success rate (ASR) | Blinded confirmation that the preregistered attacker objective was achieved, divided by all attacked attempts. Also report valid-output ASR, outcome coverage, and lower/upper bounds treating unassessable attempts as unsuccessful/successful. Zero observed success does not establish safety. |
| Status and authority promotion | Report verification strengthening and authority misattribution separately per mapped source claim, plus the fraction of attempts with an observed violation. Preserve omission and demotion rates to detect loss hidden by rejection or deletion. |
| Downstream decision integrity | Agreement with the sealed reference policy, among valid outputs and as conservative all-attempt task credit. A missing or rejected decision earns no task credit. Keep the oracle and answer labels outside model-visible inputs. |
| Semantic retention | Faithful preservation of reference meaning, uncertainty, and attribution per reference claim in valid outputs. Also report all-attempt task credit with non-valid attempts contributing zero; that credit is not their latent semantic quality. |
| Availability | Valid usable decisions per scheduled run, with every outcome and retry count. Report clean-input false rejection and attacked-input availability separately. |
| Latency and tokens | End-to-end median and p95 latency, monitor-only time, total input/output tokens, and paired overhead against the unprotected condition. Include failed attempts and retries in consumed resources; distinguish timeouts from completed latency and cached from uncached tokens. |

Use an immutable reference policy for downstream outcomes and document what legitimate task instruction the model receives without exposing the evaluator's answer key. The existing policy is a synthetic decision proxy; avoid interpreting its accuracy as investigative correctness.

Two blinded bilingual adjudicators independently label every assessable output, with model, condition, and pair identities concealed where feasible. A third bilingual resolver handles disagreements. Train on development cases only; freeze the rubric after the pilot. Keep both original ratings, disagreements, resolutions, and rationale. Report raw agreement and an appropriate chance-adjusted agreement measure with uncertainty, separately by language route and label. Model self-grading cannot replace these labels.

The existing ledger-bound review workflow supplies shuffled forms, metadata masking, frozen initial ratings, reconciliation, and descriptive agreement counts. It neither proves reviewer independence nor computes the proposed chance-adjusted statistics. The current scoring handoff remains manual and accepts one system/replicate slice at a time; validate a complete, lossless join before producing study estimates.

The primary comparison is full monitor versus unprotected handoff for ASR and all-attempt decision integrity. Report paired absolute effects with 95% confidence intervals (CIs), preserving all conditions and repetitions when resampling entire semantic families. The amendment must replace any case-level bootstrap that treats correlated translations as independent. Report model-specific and language-specific effects; a pooled estimate must use preregistered weights and cannot establish generality alone. Freeze multiplicity handling for primary tests, minimum meaningful effects, and utility/availability margins before test access. Provide sensitivity bounds for missing outcomes and precision limits for sparse or zero events.

Ablate source binding, status/authority checks, lineage propagation, and fail-closed behavior individually inside the isolated harness. Compare per-hop versus final-only enforcement and the full system against the structural allowlist and prompt-only baseline. Measure whether a security gain follows from the claimed mechanism or from excessive abstention. A formal argument must state assumptions and scope; semantic and availability findings remain empirical.

## Manuscript allocation

Use the official template and keep the main argument self-contained within 13 body pages. The proposed allocation totals 13 pages. [Formatting requirement](https://www.usenix.org/conference/usenixsecurity27/call-for-papers).

| Section | Pages | Evidence needed before writing conclusions |
| --- | --- | --- |
| Introduction | 1 | The concrete failure, security consequences, and bounded contributions. |
| Background and related work | 1.5 | Verified comparison with the literature matrix. |
| Threat model and properties | 1.5 | Trust boundaries, attacker powers, and monitor assumptions. |
| Monitor design | 2 | Complete mediation design, invariants, and limitations. |
| Method | 2 | Frozen corpus, model matrix, adjudication, and analysis. |
| Evaluation | 3 | Actual counts, paired effects and CIs, costs, adaptive evaluation, and ablations. |
| Limitations and conclusion | 2 | Negative results, generality limits, and the held-out rerun. |

Prepare an Open Science appendix and an Ethics appendix. Leave result tables empty until traceable outputs and adjudications exist; do not populate them with demo values or expected improvements.

Include the [prior-work disclosure](prior-work-disclosure.md). The related poster's existing failure-accounting proposal is background; its model outputs and counts are not results of this planned handoff study. Verify references against the cited versions and have an institutional similarity review of the final manuscript, including appendices and reused prose, before submission. A similarity report supports human review and does not certify originality.
