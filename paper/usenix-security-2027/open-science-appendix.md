# Open Science appendix draft

The reviewer-facing artifact has not been assembled or uploaded. Replace this planning document with verified access instructions before submission. The Open Science appendix must describe available artifacts or explain omissions. [Official CFP](https://www.usenix.org/conference/usenixsecurity27/call-for-papers).

## Artifact inventory

Each item requires a neutral archive path, version, checksum, license, and access status in the final manifest. "Planned" does not mean available.

| Artifact | Required contents | Status |
| --- | --- | --- |
| Frozen protocol | Dated preregistration and amendments, hypotheses, budgets, precision plan, and deviations. | Planned |
| Corpus | Synthetic generators, family-level split manifest, seeds, deduplication audit, bilingual alignment, and coverage counts. | Scaffold exists; expanded corpus pending |
| Evaluation truth | Source claims, status/authority policy, oracle decisions, and rubric, separated from model inputs and withheld from attack development. | Expanded manifest pending |
| Executable systems | Baselines, complete reference monitor, runner, role prompts, model-input exporter, and locked environment. | Exporter and structural baseline exist; runner and full monitor pending |
| Model manifest | Exact hosted versions, dates, local weight hashes, licenses, runtime and quantization, configurations, and hardware. | Pending |
| Run records | Inputs, raw outputs, every attempt and permitted retry, failures, model metadata, timing, tokens, and adaptive selection history. | Offline freeze/import ledger exists; actual records pending |
| Human review | Anonymized original independent labels, third-reviewer resolutions, rubric, and agreement analysis. | Ledger-bound forms and reconciliation exist; human labels and expanded statistics pending |
| Analysis | Scripts that rebuild denominators, paired estimates and CIs, sensitivity analyses, tables, and figures. | Expanded analysis pending |
| Held-out rerun | Independently scheduled execution records, comparisons, and drift report. | Pending |

## Reproduction contract

Provide two documented paths: an offline replay that rebuilds every reported table from released outputs and labels, and a fresh model run using pinned configurations. The offline path must work without credentials or network access. The fresh path must disclose required hardware, provider access, estimated cost and duration, nondeterminism, unavailable versions, and licensing limits. Those estimates must come from measured pilot runs.

Before export, run the artifact in a fresh environment and record exact commands, dependency versions, expected outputs, and checksums. Verify that all paper figures map to released records and that all scheduled runs reconcile with the denominator ledger. A reviewer should be able to distinguish protective rejection from transport failure and trace each statistic to its adjudications.

Document the separation between evaluation truth and model-facing inputs. The offline reviewer may inspect the truth; the evaluation runner must not accidentally send it to the model. Keep held-out labels sealed until the preregistered evaluation is complete.

The current ledger permits one request and no retries for each frozen attempt. Its hashes bind records but cannot authenticate a provider response or reveal unrecorded external retries. The blinded review tooling preserves original ratings and resolutions, but completed human review and a validated scoring join are still required. Document these limits alongside any expanded runner or analysis.

## Access and limitations

Insert the tested anonymous URL into the submitted paper by January 26, 2027. Complete the anonymized artifact by January 29, then freeze it. Keep access working through the Cycle 2 shepherded approval deadline, May 18, 2027, without reviewer tracking. [Official artifact policy](https://www.usenix.org/conference/usenixsecurity27/call-for-papers).

Do not use a public development repository as the anonymous artifact. Follow the [anonymization checklist](anonymization-checklist.md) on a separate export. Preserve attribution and license obligations through an appropriate anonymous distribution arrangement; resolve any incompatibility before submission.

List every omitted component, the specific restriction, its effect on claim verification, and any available substitute. Hosted model weights may be unavailable, but configurations and lawfully shareable outputs are still necessary. A claim that cannot be checked without an omitted artifact must be narrowed or removed. Do not promise public release until rights and privacy review are complete.
