"""Offline, deterministic execution ledger for protocol-v2 experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from protocol_v2 import (
    EXECUTION_OUTCOMES,
    LANGUAGE_ROUTES,
    PATH_CONDITIONS,
    SCHEMA_VERSION,
    SPLITS,
)


LEDGER_SCHEMA_VERSION = "1.0"
MAX_JSON_BYTES = 10 * 1024 * 1024
PROMPT_FIELDS = (
    "instruction",
    "evidence_text",
    "untrusted_text",
)
ROUTING_FIELDS = ("case_id", "input_language", "output_language")
PACKET_FIELDS = (
    "packet_id",
    "instruction",
    "evidence_text",
    "untrusted_text",
    "response",
)
EXPORT_FIELDS = {
    "semantic_family_id",
    "language_route",
    "path_condition",
    "control_metadata",
    *PROMPT_FIELDS,
    *ROUTING_FIELDS,
}
CONTROL_FIELDS = {
    "is_direct_source_control",
    "upstream_transformations",
    "paired_case_id",
    "untrusted_stimulus_id",
}
SYSTEM_FIELDS = {"system_id", "baseline", "model", "runtime"}
EXECUTION_POLICY = {
    "result_selection_rule": "first_scheduled_request_only",
    "max_requests_per_attempt": 1,
    "required_terminal_stage": "completed",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    _require(path.stat().st_size <= MAX_JSON_BYTES, f"JSON exceeds {MAX_JSON_BYTES} bytes")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            _require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result

    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)
    _require(isinstance(value, dict), "top-level JSON must be an object")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _validate_export(exported: dict[str, Any]) -> list[dict[str, Any]]:
    _require(exported.get("schema_version") == SCHEMA_VERSION, "unsupported input schema")
    cases = exported.get("cases")
    _require(isinstance(cases, list) and cases, "export must contain cases")
    _require(all(isinstance(case, dict) for case in cases), "cases must be objects")
    case_ids = [case.get("case_id") for case in cases]
    _require(
        all(isinstance(case_id, str) and case_id for case_id in case_ids),
        "case IDs must be non-empty strings",
    )
    _require(len(case_ids) == len(set(case_ids)), "duplicate case ID in export")
    for case in cases:
        _require(set(case) == EXPORT_FIELDS, f"export field drift for {case.get('case_id')}")
        _require(
            all(
                isinstance(case.get(field), str)
                for field in (*PROMPT_FIELDS, *ROUTING_FIELDS)
            ),
            f"incomplete input fields for {case.get('case_id')}",
        )
        _require(isinstance(case.get("semantic_family_id"), str), "family ID is required")
        _require(case.get("language_route") in LANGUAGE_ROUTES, "invalid language route")
        _require(case.get("path_condition") in PATH_CONDITIONS, "invalid path condition")
        control = case.get("control_metadata")
        _require(
            isinstance(control, dict) and set(control) == CONTROL_FIELDS,
            "control metadata field drift",
        )
    return cases


def freeze_attempts(
    exported: dict[str, Any],
    system_config: dict[str, Any],
    source_revision: str,
    selected_split: str,
    replicates: int = 1,
) -> dict[str, Any]:
    """Freeze one logical attempt per exported case without executing a model."""
    cases = _validate_export(exported)
    _require(isinstance(system_config, dict), "system config must be an object")
    _require(SYSTEM_FIELDS <= set(system_config), "system config lacks required metadata")
    _require(
        isinstance(system_config.get("system_id"), str) and system_config["system_id"],
        "system_id must be non-empty text",
    )
    _require(isinstance(system_config.get("baseline"), bool), "baseline must be boolean")
    for field in ("model", "runtime"):
        value = system_config.get(field)
        _require(
            value == "unavailable" or isinstance(value, dict) and bool(value),
            f"{field} must be resolved metadata or 'unavailable'",
        )
    _require(selected_split in SPLITS, "selected split must be dev, pilot, or test")
    _require(isinstance(replicates, int) and 1 <= replicates <= 100, "replicates must be 1..100")
    _require(
        bool(re.fullmatch(r"[0-9a-f]{40}", source_revision)),
        "source revision must be a lowercase 40-character Git commit",
    )
    config_hash = _hash(system_config)
    revision_hash = hashlib.sha256(source_revision.encode("ascii")).hexdigest()
    attempts = []
    for case in cases:
        prompt = {field: case[field] for field in PROMPT_FIELDS}
        prompt_hash = _hash(prompt)
        exported_case_hash = _hash(case)
        for replicate in range(replicates):
            identity = {
                "case_id": case["case_id"],
                "system_config_sha256": config_hash,
                "replicate": replicate,
                "prompt_sha256": prompt_hash,
                "exported_case_sha256": exported_case_hash,
                "source_revision_sha256": revision_hash,
            }
            attempt_id = "attempt-" + _hash(identity)[:24]
            attempts.append(
                {
                    "sequence": len(attempts),
                    "frozen_stage": "scheduled",
                    "attempt_id": attempt_id,
                    "packet_id": "packet-" + _hash({"attempt_id": attempt_id})[:24],
                    "semantic_family_id": case.get("semantic_family_id"),
                    "language_route": case.get("language_route"),
                    "path_condition": case.get("path_condition"),
                    "paired_case_id": case.get("control_metadata", {}).get("paired_case_id"),
                    **identity,
                }
            )
    manifest_core = {
        "protocol_schema_version": SCHEMA_VERSION,
        "source_revision": source_revision,
        "source_revision_sha256": revision_hash,
        "system_config_sha256": config_hash,
        "system": {field: system_config[field] for field in sorted(SYSTEM_FIELDS)},
        "export_sha256": _hash(exported),
        "selected_split": selected_split,
        "attempt_universe": [case["case_id"] for case in cases],
        "replicates": replicates,
        "execution_policy": EXECUTION_POLICY,
        "attempts": attempts,
    }
    return {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "kind": "frozen-attempt-manifest",
        "manifest_sha256": _hash(manifest_core),
        "terminal_sha256": _hash(manifest_core),
        **manifest_core,
    }


def _validate_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    _require(manifest.get("schema_version") == LEDGER_SCHEMA_VERSION, "unsupported ledger schema")
    _require(manifest.get("kind") == "frozen-attempt-manifest", "not an attempt manifest")
    attempts = manifest.get("attempts")
    _require(isinstance(attempts, list) and attempts, "manifest must contain attempts")
    _require(all(isinstance(row, dict) for row in attempts), "attempts must be objects")
    core = {
        key: value
        for key, value in manifest.items()
        if key not in {"schema_version", "kind", "manifest_sha256", "terminal_sha256"}
    }
    _require(manifest.get("manifest_sha256") == _hash(core), "manifest hash mismatch")
    _require(manifest.get("terminal_sha256") == _hash(core), "manifest terminal hash mismatch")
    _require(manifest.get("execution_policy") == EXECUTION_POLICY, "execution policy drift")
    _require(
        [row.get("sequence") for row in attempts] == list(range(len(attempts))),
        "attempt sequence must be contiguous",
    )
    for field in ("attempt_id", "packet_id"):
        values = [row.get(field) for row in attempts]
        _require(None not in values and len(values) == len(set(values)), f"duplicate {field}")
    identities = [
        (row.get("case_id"), row.get("system_config_sha256"), row.get("replicate"))
        for row in attempts
    ]
    _require(
        all(identity[0] is not None for identity in identities)
        and len(identities) == len(set(identities)),
        "duplicate logical attempt",
    )
    return attempts


def import_records(
    manifest: dict[str, Any], recorded: dict[str, Any]
) -> dict[str, Any]:
    """Validate complete recorded outcomes and build an order-invariant hash chain."""
    attempts = _validate_manifest(manifest)
    _require(recorded.get("schema_version") == LEDGER_SCHEMA_VERSION, "unsupported record schema")
    rows = recorded.get("records")
    _require(isinstance(rows, list), "records must be a list")
    _require(all(isinstance(row, dict) for row in rows), "records must be objects")
    attempt_ids = [row.get("attempt_id") for row in rows]
    _require(None not in attempt_ids, "record attempt_id is required")
    _require(len(attempt_ids) == len(set(attempt_ids)), "duplicate attempt: retry-until-success detected")
    manifest_ids = {row["attempt_id"] for row in attempts}
    record_ids = set(attempt_ids)
    _require(record_ids <= manifest_ids, "record contains an unknown attempt")
    _require(manifest_ids <= record_ids, "dropped attempt: every frozen attempt needs one outcome")
    by_id = {row["attempt_id"]: row for row in rows}
    previous = "0" * 64
    entries = []
    outcome_counts = {outcome: 0 for outcome in EXECUTION_OUTCOMES}
    for attempt in attempts:
        row = by_id[attempt["attempt_id"]]
        _require(
            set(row)
            <= {
                "attempt_id",
                "case_id",
                "stage",
                "request_number",
                "retry_number",
                "execution_outcome",
                "raw_response",
                "raw_response_path",
                "failure",
            },
            f"unexpected record field for {attempt['attempt_id']}",
        )
        _require(row.get("case_id") == attempt["case_id"], "attempt/case mismatch")
        _require(row.get("stage") == "completed", "record stage must be completed")
        _require(row.get("request_number") == 1, "request number must be one")
        _require(row.get("retry_number") == 0, "retry-until-success detected")
        outcome = row.get("execution_outcome")
        _require(outcome in EXECUTION_OUTCOMES, "invalid execution outcome")
        has_response = "raw_response" in row
        has_failure = "failure" in row
        _require(not (has_response and has_failure), "record cannot contain response and failure")
        if outcome != "transport_failure":
            _require(has_response and not has_failure, f"{outcome} requires raw response")
            _require(isinstance(row["raw_response"], str), "raw response must be text")
            _require(
                isinstance(row.get("raw_response_path"), str)
                and bool(row["raw_response_path"]),
                "raw response path is required",
            )
        if outcome == "transport_failure":
            _require(has_failure and not has_response, "transport failure requires failure detail")
            _require("raw_response_path" not in row, "transport failure cannot name a response artifact")
        if has_failure:
            _require(isinstance(row["failure"], str) and row["failure"], "failure must be text")
        entry_core = {
            "sequence": attempt["sequence"],
            "attempt_id": attempt["attempt_id"],
            "packet_id": attempt["packet_id"],
            "case_id": attempt["case_id"],
            "stage": row["stage"],
            "request_number": row["request_number"],
            "retry_number": row["retry_number"],
            "execution_outcome": outcome,
            **(
                {
                    "raw_response": row["raw_response"],
                    "raw_response_path": row["raw_response_path"],
                    "raw_response_sha256": hashlib.sha256(
                        row["raw_response"].encode("utf-8")
                    ).hexdigest(),
                }
                if has_response
                else {}
            ),
            **({"failure": row["failure"]} if has_failure else {}),
            "previous_entry_sha256": previous,
        }
        entry_hash = _hash(entry_core)
        entries.append({**entry_core, "entry_sha256": entry_hash})
        previous = entry_hash
        outcome_counts[outcome] += 1
    ledger_core = {
        "manifest_sha256": manifest["manifest_sha256"],
        "entries": entries,
        "execution_outcomes": outcome_counts,
        "counts": {
            "scheduled_attempts": len(attempts),
            "started_attempts": len(entries),
            "completed_attempts": len(entries),
            "requests": sum(entry["request_number"] for entry in entries),
        },
        "final_entry_sha256": previous,
    }
    return {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "kind": "execution-ledger",
        "ledger_sha256": _hash(ledger_core),
        **ledger_core,
    }


def _validate_ledger(manifest: dict[str, Any], ledger: dict[str, Any]) -> list[dict[str, Any]]:
    attempts = _validate_manifest(manifest)
    _require(ledger.get("schema_version") == LEDGER_SCHEMA_VERSION, "unsupported ledger schema")
    _require(ledger.get("kind") == "execution-ledger", "not an execution ledger")
    _require(ledger.get("manifest_sha256") == manifest["manifest_sha256"], "ledger/manifest mismatch")
    core = {
        key: value
        for key, value in ledger.items()
        if key not in {"schema_version", "kind", "ledger_sha256"}
    }
    _require(ledger.get("ledger_sha256") == _hash(core), "ledger hash mismatch")
    entries = ledger.get("entries")
    _require(isinstance(entries, list) and len(entries) == len(attempts), "ledger entry count mismatch")
    previous = "0" * 64
    for attempt, entry in zip(attempts, entries):
        _require(entry.get("attempt_id") == attempt["attempt_id"], "ledger attempt order mismatch")
        _require(entry.get("previous_entry_sha256") == previous, "broken ledger chain")
        entry_core = {key: value for key, value in entry.items() if key != "entry_sha256"}
        _require(entry.get("entry_sha256") == _hash(entry_core), "entry hash mismatch")
        previous = entry["entry_sha256"]
    _require(ledger.get("final_entry_sha256") == previous, "final ledger hash mismatch")
    counts = {outcome: 0 for outcome in EXECUTION_OUTCOMES}
    for entry in entries:
        _require(entry.get("execution_outcome") in EXECUTION_OUTCOMES, "invalid ledger outcome")
        counts[entry["execution_outcome"]] += 1
    _require(ledger.get("execution_outcomes") == counts, "ledger outcome counts mismatch")
    expected_counts = {
        "scheduled_attempts": len(attempts),
        "started_attempts": len(entries),
        "completed_attempts": len(entries),
        "requests": len(entries),
    }
    _require(ledger.get("counts") == expected_counts, "ledger execution counts mismatch")
    return entries


def export_adjudication_packets(
    exported: dict[str, Any], manifest: dict[str, Any], ledger: dict[str, Any]
) -> dict[str, Any]:
    """Export blinded packets for valid outputs; keep identity mapping private."""
    cases = _validate_export(exported)
    attempts = _validate_manifest(manifest)
    entries = _validate_ledger(manifest, ledger)
    _require(manifest.get("export_sha256") == _hash(exported), "export/manifest mismatch")
    case_by_id = {case["case_id"]: case for case in cases}
    packets = []
    for attempt, entry in zip(attempts, entries):
        if entry["execution_outcome"] != "valid":
            continue
        case = case_by_id[attempt["case_id"]]
        packet = {
            "packet_id": attempt["packet_id"],
            "instruction": case["instruction"],
            "evidence_text": case["evidence_text"],
            "untrusted_text": case["untrusted_text"],
            "response": entry["raw_response"],
        }
        _require(set(packet) == set(PACKET_FIELDS), "adjudication packet field drift")
        packets.append(packet)
    packet_core = {
        "source_ledger_sha256": ledger["ledger_sha256"],
        "packets": packets,
    }
    return {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "kind": "blinded-adjudication-packets",
        "packet_set_sha256": _hash(packet_core),
        **packet_core,
    }


def _distinct_paths(inputs: list[Path], output: Path, parser: argparse.ArgumentParser) -> None:
    resolved_inputs = {path.resolve() for path in inputs}
    if output.resolve() in resolved_inputs:
        parser.error("output must differ from every input")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    freeze = commands.add_parser("freeze")
    freeze.add_argument("--inputs", type=Path, required=True)
    freeze.add_argument("--system-config", type=Path, required=True)
    freeze.add_argument("--source-revision", required=True)
    freeze.add_argument("--selected-split", choices=SPLITS, required=True)
    freeze.add_argument("--replicates", type=int, default=1)
    freeze.add_argument("--output", type=Path, required=True)

    record = commands.add_parser("import-records")
    record.add_argument("--manifest", type=Path, required=True)
    record.add_argument("--records", type=Path, required=True)
    record.add_argument("--output", type=Path, required=True)

    packets = commands.add_parser("export-adjudication")
    packets.add_argument("--inputs", type=Path, required=True)
    packets.add_argument("--manifest", type=Path, required=True)
    packets.add_argument("--ledger", type=Path, required=True)
    packets.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "freeze":
        _distinct_paths([args.inputs, args.system_config], args.output, parser)
        _write(
            args.output,
            freeze_attempts(
                _load(args.inputs),
                _load(args.system_config),
                args.source_revision,
                args.selected_split,
                args.replicates,
            ),
        )
    elif args.command == "import-records":
        _distinct_paths([args.manifest, args.records], args.output, parser)
        _write(args.output, import_records(_load(args.manifest), _load(args.records)))
    else:
        _distinct_paths([args.inputs, args.manifest, args.ledger], args.output, parser)
        _write(
            args.output,
            export_adjudication_packets(
                _load(args.inputs), _load(args.manifest), _load(args.ledger)
            ),
        )


if __name__ == "__main__":
    main()
