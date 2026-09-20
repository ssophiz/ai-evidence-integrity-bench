# USENIX Security 2027 submission package

Working title: **Evidence Is Not Instruction: Measuring and Preventing Provenance-Laundering Attacks in Agentic Forensic Pipelines**.

This is a research and submission plan. It contains no experimental results and is not a submission-ready paper. All study requirements below are proposed commitments until a dated preregistration amendment is frozen before new experiments.

An evidence note can say that a claim is verified without having authority to verify it. This study asks when an agent turns that note into an authoritative finding, and whether an external reference monitor can prevent that promotion across successive handoffs. The security target is the deployed ML pipeline's instruction/data boundary. **Security of ML** is the proposed primary topic, consistent with the venue's treatment of prompt-injection research. Forensics supplies the application and downstream decisions. [Official ML submission guidance](https://www.usenix.org/conference/usenixsecurity27/submitting-ml-work-usenix-security).

## Read and act

| Document | Decision it supports |
| --- | --- |
| [Outline and study design](outline.md) | Freeze the contribution, experiments, and analysis. |
| [Literature matrix](literature-matrix.md) | Establish what prior work already covers. |
| [Open Science appendix](open-science-appendix.md) | Assemble evidence that another researcher can inspect and rerun. |
| [Ethics](ethics.md) | Resolve data, participant, and release risks before execution. |
| [Anonymization checklist](anonymization-checklist.md) | Audit the exact reviewer-facing export. |
| [Go/no-go](go-no-go.md) | Decide on January 7 whether the evidence supports submission. |

## Schedule

The internal decision is **January 7, 2027**. Official Cycle 2 dates are **January 19** for registration, **January 26** for the paper, and **January 29** for submission artifacts, all in **AoE**. Registration fixes the title, authors, and topics and requires a nonblank tentative abstract. The paper's artifact URLs must be final by the paper deadline; the artifact grace period does not permit paper changes. Check the official source again before registration. [USENIX Security 2027 CFP](https://www.usenix.org/conference/usenixsecurity27/call-for-papers), checked September 20, 2026.

## Start today

1. Assign study, implementation, annotation, and artifact owners in a private task record. Keep identities outside the anonymous package.
2. Inventory the current generator, exporter, scorer, and structural allowlist against the proposed monitor. Record missing functionality without counting the offline demonstration as model evidence.
3. Freeze a dated amendment covering the expanded corpus, conditions, four model families, budgets, and statistical plan. Reconcile it with the existing protocol before collection; preserve both versions.
4. Reserve two independent Korean-English adjudicators and a third resolver. Pilot the rubric on development data and estimate annotation time and model cost.
5. Open the evidence ledger in [go/no-go](go-no-go.md). A requirement stays pending until its supporting artifact exists.

The existing scaffold does not establish a typed reference monitor, semantic correctness, an effective defense, or field validity. Those remain research questions. The title's word "Preventing" must be narrowed if the completed evidence supports only detection or partial mitigation.

The current offline tooling already freezes an attempt universe, binds imported outputs to an execution ledger, and prepares independent bilingual review forms with third-reviewer reconciliation. It makes no model calls and supplies no completed human reviews. The expanded corpus, runner, monitor, statistical analysis, and independent evidence still require implementation or collection.
