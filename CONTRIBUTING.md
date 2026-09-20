# Contributing

Open an [issue](https://github.com/ssophiz/ai-evidence-integrity-bench/issues)
for a reproducible bug, a documentation correction, or a proposed change to
the benchmark. Include the revision, Python version, command, expected result,
and observed result where relevant. Use synthetic examples without personal
data or credentials. For security concerns, read [SECURITY.md](SECURITY.md).

Use Python 3.10 or newer and run from the repository root:

```powershell
python -m unittest discover -s tests -v
git diff --check
```

Keep pull requests focused. Explain the problem, the resulting behavior, and
how you checked it. Add a regression test for changed scoring, validation, or
trust-boundary behavior. For demo changes, use the
[verification checklist](docs/demo-verification-checklist.md) and record any
presentation checks that remain outstanding.

Read the [threat model](THREAT_MODEL.md), [ethics boundaries](ETHICS.md), and
[preregistration](preregistration.md) before changing the experiment. Document
changes to stimuli, denominators, or metrics explicitly. Keep authored
fixtures, recorded system outputs, and human adjudications distinct; do not
present missing reviews or illustrative decisions as measured results.
