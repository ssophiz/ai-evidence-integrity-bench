# Protocol v2 execution ledger

The execution ledger freezes the attempt universe before any system output is
examined. It is an offline import and audit tool. It does not call a model,
retry a failed request, or create performance results.

## Threats addressed

- dropping failures after execution;
- retrying one logical attempt until it succeeds;
- changing prompts, system configuration, source revision, or selected cases;
- exposing the tested system, path condition, semantic family, replicate, or
  expected decision to adjudicators;
- editing a recorded response without invalidating the ledger.

The ledger cannot prove that a separate runner used the frozen prompt or that
a recorded response came from a claimed model. Signed provider receipts or a
controlled runner would be separate evidence.

## Files and trust boundary

`export-model-inputs` output is the only accepted case source. A private
protocol manifest is rejected because it contains evaluation data. The system
configuration is hashed; only its declared system/model/runtime descriptor is
copied into the attempt manifest. Keep the full configuration, frozen manifest,
raw records, and execution ledger private.

The configuration must declare `system_id`, boolean `baseline`, and `model`
and `runtime` metadata. The latter two may be non-empty objects or the literal
`"unavailable"`; the tool never invents missing runtime metadata.

```json
{
  "system_id": "system-a",
  "baseline": false,
  "model": {"provider": "recorded-provider", "name": "resolved-model"},
  "runtime": "unavailable",
  "temperature": 0
}
```

Each logical attempt is keyed by the case and exported-case hash, prompt hash,
system-configuration hash, replicate number, and Git source-revision hash.
The manifest also records the selected split, ordered case universe, and
family/route/condition metadata. Those fields support clustered and paired
analysis but are excluded from the prompt hash and adjudication packets.

## Offline workflow

```powershell
python protocol_v2.py generate --families 20 --output private/manifest-v2.json
python protocol_v2.py export-model-inputs --manifest private/manifest-v2.json --split pilot --output private/pilot-inputs.json

python execution_ledger.py freeze `
  --inputs private/pilot-inputs.json `
  --system-config private/system-a.json `
  --source-revision 0123456789abcdef0123456789abcdef01234567 `
  --selected-split pilot `
  --replicates 3 `
  --output private/system-a-attempts.json
```

Run the system separately exactly once per frozen `attempt_id`. The frozen
selection rule accepts only request 1, retry 0, at terminal stage `completed`.
Import one record per attempt. A valid or other output-bearing outcome has the
exact UTF-8 `raw_response` and its source path; a `transport_failure` has
non-empty `failure` text.

```json
{
  "schema_version": "1.0",
  "records": [
    {
      "attempt_id": "attempt-...",
      "case_id": "sf-...-ko-en-agent_handoff",
      "stage": "completed",
      "request_number": 1,
      "retry_number": 0,
      "execution_outcome": "valid",
      "raw_response": "recorded system output",
      "raw_response_path": "artifacts/attempt-....txt"
    }
  ]
}
```

Then build the deterministic ledger and blinded packets:

```powershell
python execution_ledger.py import-records `
  --manifest private/system-a-attempts.json `
  --records private/system-a-records.json `
  --output private/system-a-ledger.json

python execution_ledger.py export-adjudication `
  --inputs private/pilot-inputs.json `
  --manifest private/system-a-attempts.json `
  --ledger private/system-a-ledger.json `
  --output adjudication/system-a-packets.json
```

Record order does not affect the ledger. Missing, unknown, and duplicate
attempts are rejected. Duplicate attempt IDs are treated as a retry-until-
success workflow. Only `valid` outcomes enter semantic adjudication packets;
all other outcomes remain in attempt-level accounting.

The ledger reports scheduled, started, completed, and request counts. It keeps
external `gate_rejection` separate from tested-system `protective_rejection`.

Packets contain opaque IDs, source text, instruction, and recorded response.
They omit system identity/configuration, case and attempt IDs, path condition,
semantic-family and pairing metadata, replicate number, and expected decision.

## Integrity limits

Canonical JSON SHA-256 hashes bind exported cases, prompts, configuration,
source revision, manifest, entries, and packet set. Entries form a deterministic
hash chain in frozen-attempt order. Hashes detect changes; they are not
signatures and do not establish who produced a response.
The importer rejects recorded retries and duplicate attempts, but it cannot
detect an external retry that an operator never records. That requires a
controlled runner or independently verifiable provider receipts.
Anchor the final manifest terminal hash in an external commit, release, or
timestamped record before execution. A repository-local hash alone cannot
prove when the manifest was frozen or prevent wholesale replacement.
