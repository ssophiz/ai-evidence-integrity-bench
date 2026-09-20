"""Offline blinded human review: build packets, freeze reviews, reconcile labels."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import re
import uuid
from pathlib import Path
from typing import Any

from execution_ledger import (
    LEDGER_SCHEMA_VERSION, PROMPT_FIELDS, SYSTEM_FIELDS, _validate_manifest,
    export_adjudication_packets, import_records,
)
from protocol_v2 import (
    AUTHORITY_RELATIONS, DECISIONS, SCHEMA_VERSION,
    SPLITS, VERIFICATION_RELATIONS, model_view, validate_dataset,
)

REVIEW_OUTCOMES = ("valid", "unadjudicable")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def object_keys(value: Any, keys: set[str], name: str) -> None:
    require(isinstance(value, dict) and set(value) == keys, f"invalid {name} fields")


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def linked_attempts(dataset: dict, frozen: dict, ledger: dict, exported_packets: dict) -> list[dict]:
    """Rebuild identities and ledger records; hashes alone do not prove linkage."""
    validate_dataset(dataset)
    object_keys(frozen, {"schema_version", "kind", "manifest_sha256", "terminal_sha256",
        "protocol_schema_version", "source_revision", "source_revision_sha256", "system_config_sha256",
        "system", "export_sha256", "selected_split", "attempt_universe", "replicates", "execution_policy", "attempts"},
        "frozen manifest")
    attempts = _validate_manifest(frozen)
    object_keys(frozen["system"], SYSTEM_FIELDS, "frozen system metadata")
    require(nonempty(frozen["system"]["system_id"]), "frozen system ID required")
    require(frozen.get("protocol_schema_version") == SCHEMA_VERSION, "protocol schema mismatch")
    require(frozen.get("selected_split") in SPLITS, "invalid frozen split")
    require(type(frozen.get("replicates")) is int and 1 <= frozen["replicates"] <= 100,
            "invalid frozen replicates")
    config_hash = frozen.get("system_config_sha256")
    require(isinstance(config_hash, str) and re.fullmatch(r"[0-9a-f]{64}", config_hash) is not None,
            "invalid frozen system configuration hash")
    revision = frozen.get("source_revision")
    require(isinstance(revision, str) and re.fullmatch(r"[0-9a-f]{40}", revision) is not None, "invalid source revision")
    revision_hash = hashlib.sha256(revision.encode("ascii")).hexdigest()
    require(frozen.get("source_revision_sha256") == revision_hash, "source revision hash mismatch")
    exported = model_view(dataset, frozen["selected_split"])
    require(digest(exported) == frozen.get("export_sha256"), "private dataset/export hash mismatch")
    require(frozen.get("attempt_universe") == [case["case_id"] for case in exported["cases"]], "attempt universe mismatch")
    expected_attempts = []
    for case in exported["cases"]:
        for replicate in range(frozen["replicates"]):
            identity = {"case_id": case["case_id"], "system_config_sha256": config_hash,
                        "replicate": replicate, "prompt_sha256": digest({key: case[key] for key in PROMPT_FIELDS}),
                        "exported_case_sha256": digest(case), "source_revision_sha256": revision_hash}
            attempt_id = "attempt-" + digest(identity)[:24]
            expected_attempts.append({"sequence": len(expected_attempts), "frozen_stage": "scheduled",
                "attempt_id": attempt_id, "packet_id": "packet-" + digest({"attempt_id": attempt_id})[:24],
                "semantic_family_id": case["semantic_family_id"], "language_route": case["language_route"],
                "path_condition": case["path_condition"], "paired_case_id": case["control_metadata"]["paired_case_id"], **identity})
    require(digest(attempts) == digest(expected_attempts), "frozen attempt identity/configuration/replicate mismatch")
    require(isinstance(ledger.get("entries"), list) and all(isinstance(row, dict) for row in ledger["entries"]), "ledger entries required")
    record_fields = {"attempt_id", "case_id", "stage", "request_number", "retry_number",
                     "execution_outcome", "raw_response", "raw_response_path", "failure"}
    rebuilt = import_records(frozen, {"schema_version": LEDGER_SCHEMA_VERSION,
        "records": [{key: value for key, value in row.items() if key in record_fields} for row in ledger["entries"]]})
    require(digest(rebuilt) == digest(ledger), "execution ledger linkage or hash mismatch")
    expected_packets = export_adjudication_packets(exported, frozen, ledger)
    require(digest(exported_packets) == digest(expected_packets), "blinded packet export/hash/valid-output coverage mismatch")
    packet_by_id = {row["packet_id"]: row for row in exported_packets["packets"]}
    return [{**attempt, **entry,
             "system_id": frozen["system"]["system_id"],
             "response_text": packet_by_id[attempt["packet_id"]]["response"] if entry["execution_outcome"] == "valid" else None}
            for attempt, entry in zip(attempts, ledger["entries"])]


def build_packets(dataset: dict, frozen: dict, ledger: dict, exported_packets: dict) -> tuple[dict, dict, dict, dict]:
    """No semantic judgment is generated. Returned mapping is coordinator-only."""
    attempts = linked_attempts(dataset, frozen, ledger, exported_packets)
    cases = {row["case_id"]: row for row in dataset["cases"]}
    masks = set()
    for case in dataset["cases"]:
        masks.update((case["case_id"], case["semantic_family_id"], case["path_condition"],
                      case["control_metadata"]["paired_case_id"],
                      case["control_metadata"]["untrusted_stimulus_id"]))
        masks.update(claim["claim_id"] for claim in case["evaluation"]["claims"])
    for attempt in attempts:
        masks.update((attempt["attempt_id"], attempt["packet_id"], attempt["system_id"],
                      attempt["system_config_sha256"], attempt["language_route"]))
    def config_strings(value: Any) -> None:
        if isinstance(value, str) and value:
            masks.add(value)
        elif isinstance(value, dict):
            for nested in value.values():
                config_strings(nested)
        elif isinstance(value, list):
            for nested in value:
                config_strings(nested)
    config_strings(frozen["system"])
    pattern = re.compile("|".join(re.escape(token) for token in sorted(masks, key=lambda x: (-len(x), x))))
    packets, mapping = [], []
    for attempt in attempts:
        if attempt["execution_outcome"] != "valid":
            mapping.append({**attempt, "review_id": None, "claim_map": {}, "masked_occurrences": {}})
            continue
        case = cases[attempt["case_id"]]
        review_id = "r-" + uuid.uuid4().hex
        claim_map = {"c-" + uuid.uuid4().hex: claim["claim_id"] for claim in case["evaluation"]["claims"]}
        reverse_claims = {value: key for key, value in claim_map.items()}
        replacements: dict[str, int] = {}

        def mask(text: str | None) -> str | None:
            if text is None:
                return None

            def replace(match: re.Match) -> str:
                token = match.group()
                replacements[token] = replacements.get(token, 0) + 1
                return "[MASKED]"

            return pattern.sub(replace, text)

        packets.append({
            "review_id": review_id,
            "source_claims": [{"source_claim_id": reverse_claims[claim["claim_id"]],
                               "text_en": mask(claim["text_en"]), "text_ko": mask(claim["text_ko"]),
                               "authority_tier": claim["authority_tier"],
                               "verification_status": claim["verification_status"]}
                              for claim in case["evaluation"]["claims"]],
            "evidence_text": mask(case["model_input"]["evidence_text"]),
            "untrusted_text": mask(case["model_input"]["untrusted_text"]),
            "response_text": mask(attempt["response_text"]),
        })
        mapping.append({"review_id": review_id, **attempt, "claim_map": claim_map,
                        "path_condition": case["path_condition"],
                        "semantic_family_id": case["semantic_family_id"],
                        "language_route": case["language_route"], "split": case["split"],
                        "masked_occurrences": replacements})
    random.SystemRandom().shuffle(packets)
    packet = {"schema_version": SCHEMA_VERSION, "packets": packets}
    packet_hash = digest(packet)
    private = {"schema_version": SCHEMA_VERSION, "packet_sha256": packet_hash,
               "dataset_sha256": digest(dataset), "frozen_manifest_sha256": frozen["manifest_sha256"],
               "ledger_sha256": ledger["ledger_sha256"], "packet_set_sha256": exported_packets["packet_set_sha256"],
               "system_config_sha256": frozen["system_config_sha256"],
               "execution_outcomes": copy.deepcopy(ledger["execution_outcomes"]), "attempts": mapping}
    templates = []
    for slot in ("A", "B"):
        rows = [{"review_id": row["review_id"], "judgment": None, "rationale": None} for row in packets]
        random.SystemRandom().shuffle(rows)
        templates.append({"schema_version": SCHEMA_VERSION, "packet_sha256": packet_hash,
                          "reviewer_slot": slot, "reviewer_id": None, "languages": [],
                          "independent_human_review": None, "cases": rows})
    return packet, private, templates[0], templates[1]


def validate_packet(packet: dict) -> None:
    object_keys(packet, {"schema_version", "packets"}, "packet document")
    require(packet["schema_version"] == SCHEMA_VERSION, "unsupported packet schema")
    require(isinstance(packet["packets"], list), "packets must be a list")
    seen = set()
    for row in packet["packets"]:
        object_keys(row, {"review_id", "source_claims", "evidence_text", "untrusted_text", "response_text"}, "packet")
        rid = row["review_id"]
        require(isinstance(rid, str) and re.fullmatch(r"r-[0-9a-f]{32}", rid) is not None
                and rid not in seen, "packet review IDs must be opaque and unique")
        seen.add(rid)
        require(nonempty(row["evidence_text"]) and nonempty(row["untrusted_text"]), "packet evidence must be text")
        require(isinstance(row["response_text"], str), "invalid packet response")
        require(isinstance(row["source_claims"], list) and row["source_claims"], "source claims must be nonempty")
        claim_ids = set()
        for claim in row["source_claims"]:
            object_keys(claim, {"source_claim_id", "text_en", "text_ko", "authority_tier", "verification_status"}, "source claim")
            cid = claim["source_claim_id"]
            require(isinstance(cid, str) and re.fullmatch(r"c-[0-9a-f]{32}", cid) is not None
                    and cid not in claim_ids, "source claim IDs must be opaque and unique")
            claim_ids.add(cid)
            require(nonempty(claim["text_en"]) and nonempty(claim["text_ko"]), "bilingual claim text required")
            require(claim["authority_tier"] in ("artifact", "analyst_note", "third_party"), "invalid source authority")
            require(claim["verification_status"] in ("verified", "reported", "unverified"), "invalid source verification")


def validate_judgment(value: Any, packet: dict) -> None:
    require(isinstance(value, dict), "human judgment is required")
    outcome = value.get("execution_outcome")
    require(outcome in REVIEW_OUTCOMES, "human review outcome must be valid or unadjudicable; ledger outcomes stay separate")
    if outcome != "valid":
        object_keys(value, {"execution_outcome"}, "non-valid judgment (no semantic labels allowed)")
        return
    object_keys(value, {"execution_outcome", "claims", "unsupported_claims", "downstream_decision"}, "valid judgment")
    require(nonempty(packet["response_text"]), "valid judgment requires recorded response text")
    require(isinstance(value["claims"], list), "claims must be a list")
    known = {claim["source_claim_id"] for claim in packet["source_claims"]}
    seen = set()
    for claim in value["claims"]:
        object_keys(claim, {"source_claim_id", "semantic_preserved", "verification_relation", "authority_relation"}, "claim judgment")
        claim_id = claim["source_claim_id"]
        require(isinstance(claim_id, str) and claim_id in known and claim_id not in seen, "unknown or duplicate source claim")
        seen.add(claim_id)
        require(type(claim["semantic_preserved"]) is bool, "semantic_preserved must be boolean")
        require(claim["verification_relation"] in VERIFICATION_RELATIONS, "invalid verification relation")
        require(claim["authority_relation"] in AUTHORITY_RELATIONS, "invalid authority relation")
    require(isinstance(value["unsupported_claims"], list), "unsupported_claims must be a list")
    for claim in value["unsupported_claims"]:
        object_keys(claim, {"text"}, "unsupported claim")
        require(nonempty(claim["text"]), "unsupported claim text must be nonempty")
    require(value["downstream_decision"] in DECISIONS, "invalid downstream decision")


def normalized(judgment: dict) -> dict:
    result = copy.deepcopy(judgment)
    if result["execution_outcome"] == "valid":
        result["claims"].sort(key=lambda row: row["source_claim_id"])
        result["unsupported_claims"].sort(key=lambda row: row["text"])
    return result


def validate_review(review: dict, packet: dict, slot: str) -> dict:
    object_keys(review, {"schema_version", "packet_sha256", "reviewer_slot", "reviewer_id",
                         "languages", "independent_human_review", "cases"}, "review")
    require(review["schema_version"] == SCHEMA_VERSION and review["packet_sha256"] == digest(packet), "review packet mismatch")
    require(review["reviewer_slot"] == slot and nonempty(review["reviewer_id"]), "invalid reviewer identity or slot")
    require(review["languages"] == ["en", "ko"] and review["independent_human_review"] is True,
            "reviewer must attest independent human review and English/Korean competence")
    require(isinstance(review["cases"], list), "review cases must be a list")
    packets = {row["review_id"]: row for row in packet["packets"]}
    rows = {}
    for row in review["cases"]:
        object_keys(row, {"review_id", "judgment", "rationale"}, "review row")
        require(isinstance(row["review_id"], str) and row["review_id"] in packets and row["review_id"] not in rows,
                "unknown or duplicate review ID")
        require(nonempty(row["rationale"]), "human rationale is required")
        validate_judgment(row["judgment"], packets[row["review_id"]])
        rows[row["review_id"]] = row
    require(set(rows) == set(packets), "review must cover every packet")
    return rows


def freeze_reviews(packet: dict, review_a: dict, review_b: dict) -> tuple[dict, dict]:
    validate_packet(packet)
    a = validate_review(review_a, packet, "A")
    b = validate_review(review_b, packet, "B")
    require(review_a["reviewer_id"] != review_b["reviewer_id"], "two distinct reviewers required")
    agreements = {name: {"agree": 0, "compared": 0} for name in (
        "whole_judgment", "execution_outcome", "claim_presence", "semantic_preserved",
        "verification_relation", "authority_relation", "unsupported_claims", "downstream_decision")}

    def count(name: str, left: Any, right: Any) -> None:
        agreements[name]["compared"] += 1
        agreements[name]["agree"] += int(left == right)

    disputes = []
    for row in packet["packets"]:
        rid = row["review_id"]
        left, right = normalized(a[rid]["judgment"]), normalized(b[rid]["judgment"])
        count("whole_judgment", left, right)
        count("execution_outcome", left["execution_outcome"], right["execution_outcome"])
        if left != right:
            disputes.append({"review_id": rid, "judgment": None, "rationale": None})
        if left["execution_outcome"] == right["execution_outcome"] == "valid":
            for name in ("unsupported_claims", "downstream_decision"):
                count(name, left[name], right[name])
            lc = {claim["source_claim_id"]: claim for claim in left["claims"]}
            rc = {claim["source_claim_id"]: claim for claim in right["claims"]}
            for claim in row["source_claims"]:
                cid = claim["source_claim_id"]
                count("claim_presence", cid in lc, cid in rc)
                if cid in lc and cid in rc:
                    for name in ("semantic_preserved", "verification_relation", "authority_relation"):
                        count(name, lc[cid][name], rc[cid][name])
    lock = {"schema_version": SCHEMA_VERSION, "packet": copy.deepcopy(packet),
            "initial_reviews": [copy.deepcopy(review_a), copy.deepcopy(review_b)],
            "initial_review_sha256": [digest(review_a), digest(review_b)], "agreement_counts": agreements,
            "disputed_review_ids": [row["review_id"] for row in disputes]}
    reconciliation = {"schema_version": SCHEMA_VERSION, "lock_sha256": digest(lock),
                      "reviewer_id": None, "languages": [], "human_reconciliation": None, "cases": disputes}
    return lock, reconciliation


def reconcile(lock: dict, resolutions: dict, expected_lock_sha256: str) -> dict:
    require(digest(lock) == expected_lock_sha256, "initial review lock hash mismatch")
    object_keys(lock, {"schema_version", "packet", "initial_reviews", "initial_review_sha256",
                       "agreement_counts", "disputed_review_ids"}, "initial review lock")
    require(isinstance(lock["initial_reviews"], list) and len(lock["initial_reviews"]) == 2, "two frozen initial reviews required")
    require(lock["initial_review_sha256"] == [digest(r) for r in lock["initial_reviews"]], "initial review hash mismatch")
    rebuilt, _ = freeze_reviews(lock["packet"], *lock["initial_reviews"])
    require(rebuilt == lock, "invalid review lock")
    object_keys(resolutions, {"schema_version", "lock_sha256", "reviewer_id", "languages", "human_reconciliation", "cases"}, "reconciliation")
    require(resolutions["schema_version"] == SCHEMA_VERSION and resolutions["lock_sha256"] == expected_lock_sha256,
            "reconciliation lock mismatch")
    require(nonempty(resolutions["reviewer_id"]) and resolutions["reviewer_id"] not in
            {r["reviewer_id"] for r in lock["initial_reviews"]}, "distinct third reviewer required")
    require(resolutions["languages"] == ["en", "ko"] and resolutions["human_reconciliation"] is True,
            "third reviewer must attest human reconciliation and English/Korean competence")
    require(isinstance(resolutions["cases"], list), "resolutions must be a list")
    packets = {row["review_id"]: row for row in lock["packet"]["packets"]}
    resolved = {}
    for row in resolutions["cases"]:
        object_keys(row, {"review_id", "judgment", "rationale"}, "resolution row")
        rid = row["review_id"]
        require(isinstance(rid, str) and rid in lock["disputed_review_ids"] and rid not in resolved,
                "unknown, agreed, or duplicate resolution ID")
        require(nonempty(row["rationale"]), "human reconciliation rationale required")
        validate_judgment(row["judgment"], packets[rid])
        resolved[rid] = copy.deepcopy(row)
    require(set(resolved) == set(lock["disputed_review_ids"]), "every disagreement requires resolution")
    rows = [resolved.get(row["review_id"], copy.deepcopy(row)) for row in lock["initial_reviews"][0]["cases"]]
    return {"schema_version": SCHEMA_VERSION, "packet_sha256": digest(lock["packet"]),
            "lock_sha256": expected_lock_sha256, "reconciliation": copy.deepcopy(resolutions),
            "agreement_counts": copy.deepcopy(lock["agreement_counts"]), "cases": rows}


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "JSON document must be an object")
    return value


def write_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--dataset", type=Path, required=True)
    build.add_argument("--manifest", type=Path, required=True)
    build.add_argument("--ledger", type=Path, required=True)
    build.add_argument("--packets", type=Path, required=True)
    build.add_argument("--output-dir", type=Path, required=True)
    freeze = commands.add_parser("freeze")
    freeze.add_argument("--packet", type=Path, required=True)
    freeze.add_argument("--review-a", type=Path, required=True)
    freeze.add_argument("--review-b", type=Path, required=True)
    freeze.add_argument("--output-dir", type=Path, required=True)
    final = commands.add_parser("reconcile")
    final.add_argument("--lock", type=Path, required=True)
    final.add_argument("--lock-sha256", required=True)
    final.add_argument("--resolutions", type=Path, required=True)
    final.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "build":
            values = build_packets(load(args.dataset), load(args.manifest), load(args.ledger), load(args.packets))
            args.output_dir.mkdir(parents=True, exist_ok=False)
            for name, value in zip(("packet.json", "private-map.json", "reviewer-a.json", "reviewer-b.json"), values):
                write_new(args.output_dir / name, value)
        elif args.command == "freeze":
            lock, resolution = freeze_reviews(load(args.packet), load(args.review_a), load(args.review_b))
            args.output_dir.mkdir(parents=True, exist_ok=False)
            write_new(args.output_dir / "initial-lock.json", lock)
            write_new(args.output_dir / "reconciliation.json", resolution)
            print("Record this lock SHA-256 separately before reconciliation: " + digest(lock))
        else:
            result = reconcile(load(args.lock), load(args.resolutions), args.lock_sha256)
            write_new(args.output, result)
    except (ValueError, OSError) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    main()
