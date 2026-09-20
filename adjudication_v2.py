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

from protocol_v2 import (
    AUTHORITY_RELATIONS, DECISIONS, EXECUTION_OUTCOMES, SCHEMA_VERSION,
    VERIFICATION_RELATIONS, validate_dataset,
)


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


def build_packets(dataset: dict, attempts: dict) -> tuple[dict, dict, dict, dict]:
    """No semantic judgment is generated. Returned mapping is coordinator-only."""
    validate_dataset(dataset)
    object_keys(attempts, {"schema_version", "attempts"}, "attempt adapter")
    require(attempts["schema_version"] == SCHEMA_VERSION, "unsupported adapter schema")
    require(isinstance(attempts["attempts"], list) and attempts["attempts"], "attempts must be nonempty")
    cases = {row["case_id"]: row for row in dataset["cases"]}
    seen = set()
    masks = set()
    for case in dataset["cases"]:
        masks.update((case["case_id"], case["semantic_family_id"], case["path_condition"],
                      case["control_metadata"]["paired_case_id"],
                      case["control_metadata"]["untrusted_stimulus_id"]))
        masks.update(claim["claim_id"] for claim in case["evaluation"]["claims"])
    for attempt in attempts["attempts"]:
        object_keys(attempt, {"attempt_id", "case_id", "system_id", "replicate",
                              "response_text", "execution_outcome"}, "attempt")
        require(nonempty(attempt["attempt_id"]) and attempt["attempt_id"] not in seen,
                "attempt IDs must be nonempty and unique")
        seen.add(attempt["attempt_id"])
        require(isinstance(attempt["case_id"], str) and attempt["case_id"] in cases, "unknown case ID")
        require(nonempty(attempt["system_id"]), "system ID must be nonempty")
        require(type(attempt["replicate"]) is int and attempt["replicate"] >= 1, "replicate must be positive integer")
        require(attempt["execution_outcome"] in EXECUTION_OUTCOMES, "invalid execution outcome")
        require(isinstance(attempt["response_text"], str) or attempt["response_text"] is None,
                "response_text must be text or null")
        require(attempt["response_text"] is not None or attempt["execution_outcome"] == "transport_failure",
                "only transport failure may have null response")
        masks.update((attempt["attempt_id"], attempt["system_id"]))
    pattern = re.compile("|".join(re.escape(token) for token in sorted(masks, key=lambda x: (-len(x), x))))
    packets, mapping = [], []
    for attempt in attempts["attempts"]:
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
            "input_language": case["model_input"]["input_language"],
            "output_language": case["model_input"]["output_language"],
            "source_claims": [{"source_claim_id": reverse_claims[claim["claim_id"]],
                               "text_en": mask(claim["text_en"]), "text_ko": mask(claim["text_ko"]),
                               "authority_tier": claim["authority_tier"],
                               "verification_status": claim["verification_status"]}
                              for claim in case["evaluation"]["claims"]],
            "evidence_text": mask(case["model_input"]["evidence_text"]),
            "untrusted_text": mask(case["model_input"]["untrusted_text"]),
            "response_text": mask(attempt["response_text"]),
            "reported_execution_outcome": attempt["execution_outcome"],
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
               "manifest_sha256": digest(dataset), "adapter_sha256": digest(attempts), "attempts": mapping}
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
    require(isinstance(packet["packets"], list) and packet["packets"], "packets must be nonempty")
    seen = set()
    for row in packet["packets"]:
        object_keys(row, {"review_id", "input_language", "output_language", "source_claims",
                          "evidence_text", "untrusted_text", "response_text", "reported_execution_outcome"}, "packet")
        rid = row["review_id"]
        require(isinstance(rid, str) and re.fullmatch(r"r-[0-9a-f]{32}", rid) is not None
                and rid not in seen, "packet review IDs must be opaque and unique")
        seen.add(rid)
        require(row["input_language"] in ("en", "ko") and row["output_language"] in ("en", "ko"), "invalid packet language")
        require(nonempty(row["evidence_text"]) and nonempty(row["untrusted_text"]), "packet evidence must be text")
        require(row["reported_execution_outcome"] in EXECUTION_OUTCOMES, "invalid packet outcome")
        require(isinstance(row["response_text"], str) or
                (row["response_text"] is None and row["reported_execution_outcome"] == "transport_failure"), "invalid packet response")
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
    require(outcome in EXECUTION_OUTCOMES, "invalid reviewed execution outcome")
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
    build.add_argument("--manifest", type=Path, required=True)
    build.add_argument("--attempts", type=Path, required=True)
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
            values = build_packets(load(args.manifest), load(args.attempts))
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
