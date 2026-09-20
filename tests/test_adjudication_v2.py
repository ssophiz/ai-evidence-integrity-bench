"""Synthetic software fixtures only; these are not human review results."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from adjudication_v2 import build_packets, digest, freeze_reviews, reconcile, write_new
from execution_ledger import export_adjudication_packets, freeze_attempts, import_records
from protocol_v2 import EXECUTION_OUTCOMES, generate_protocol, model_view


class AdjudicationV2Tests(unittest.TestCase):
    def setUp(self):
        self.dataset = generate_protocol(5, 7)
        self.exported = model_view(self.dataset, "dev")
        self.frozen = freeze_attempts(self.exported, {"system_id": "system-secret-name", "baseline": False,
            "model": {"name": "model-secret-name"}, "runtime": "unavailable"}, "1" * 40, "dev", 2)
        case = next(row for row in self.dataset["cases"] if row["case_id"] == self.frozen["attempts"][0]["case_id"])
        self.case = case
        self.records = {"schema_version": "1.0", "records": [{
            "attempt_id": attempt["attempt_id"], "case_id": attempt["case_id"],
            "stage": "completed", "request_number": 1, "retry_number": 0,
            "raw_response_path": "fixtures/response.txt",
            "raw_response": "검토 / review: " + " ".join((case["case_id"],
                case["semantic_family_id"], case["path_condition"],
                case["control_metadata"]["paired_case_id"],
                case["control_metadata"]["untrusted_stimulus_id"],
                case["evaluation"]["claims"][0]["claim_id"], "system-secret-name", "model-secret-name",
                attempt["attempt_id"], attempt["packet_id"], attempt["system_config_sha256"], attempt["language_route"])),
            "execution_outcome": "valid" if index == 0 else ("gate_rejection" if index % 2 else "protective_rejection"),
        } for index, attempt in enumerate(self.frozen["attempts"])]}
        self.refresh()
        self.packet, self.private, self.a, self.b = self.build()

    def refresh(self):
        self.ledger = import_records(self.frozen, self.records)
        self.export_packets = export_adjudication_packets(self.exported, self.frozen, self.ledger)

    def build(self):
        return build_packets(self.dataset, self.frozen, self.ledger, self.export_packets)

    def complete(self, review, reviewer_id):
        """Populate only a unit-test fixture; production templates remain empty."""
        review["reviewer_id"] = reviewer_id
        review["languages"] = ["en", "ko"]
        review["independent_human_review"] = True
        packets = {row["review_id"]: row for row in self.packet["packets"]}
        for row in review["cases"]:
            row["rationale"] = "Synthetic software test fixture."
            row["judgment"] = {"execution_outcome": "valid", "claims": [{
                "source_claim_id": claim["source_claim_id"], "semantic_preserved": True,
                "verification_relation": "preserved", "authority_relation": "preserved",
            } for claim in packets[row["review_id"]]["source_claims"]],
                "unsupported_claims": [], "downstream_decision": "seek_corroboration"}

    def completed_pair(self):
        self.complete(self.a, "test-reviewer-a")
        self.complete(self.b, "test-reviewer-b")

    def third(self, resolution):
        resolution.update(reviewer_id="test-reviewer-c", languages=["en", "ko"], human_reconciliation=True)

    def test_packets_allowlist_and_mask_metadata_and_embedded_identifiers(self):
        encoded = json.dumps(self.packet, ensure_ascii=False)
        case = self.case
        for secret in (case["case_id"], case["semantic_family_id"], case["path_condition"],
                       case["control_metadata"]["paired_case_id"], case["control_metadata"]["untrusted_stimulus_id"],
                       "system-secret-name", "model-secret-name", "expected_downstream_decision",
                       "language_route", "input_language", "output_language", "packet_id", "system_config_sha256",
                       self.frozen["attempts"][0]["attempt_id"], self.frozen["attempts"][0]["packet_id"],
                       self.frozen["system_config_sha256"], case["language_route"],
                       case["evaluation"]["claims"][0]["claim_id"]):
            self.assertNotIn(secret, encoded)
        row = self.packet["packets"][0]
        self.assertIn("검토", row["response_text"])
        self.assertIn("[MASKED]", row["response_text"])
        self.assertEqual(len(row["source_claims"]), 3)
        self.assertEqual(self.private["attempts"][0]["response_text"], self.records["records"][0]["raw_response"])
        self.assertTrue(self.private["attempts"][0]["masked_occurrences"])
        for review in (self.a, self.b):
            self.assertIsNone(review["cases"][0]["judgment"])
            self.assertIsNone(review["reviewer_id"])
            self.assertIsNone(review["independent_human_review"])

    def test_separate_builds_and_claims_have_fresh_opaque_ids(self):
        other, _, _, _ = self.build()
        self.assertNotEqual(self.packet["packets"][0]["review_id"], other["packets"][0]["review_id"])
        self.assertNotEqual(self.packet["packets"][0]["source_claims"][0]["source_claim_id"],
                            other["packets"][0]["source_claims"][0]["source_claim_id"])

    def test_valid_only_packets_preserve_all_private_execution_outcomes_and_identities(self):
        self.assertEqual(len(self.packet["packets"]), 1)
        self.assertEqual(len(self.private["attempts"]), len(self.frozen["attempts"]))
        self.assertEqual(self.private["execution_outcomes"], self.ledger["execution_outcomes"])
        for attempt, row in zip(self.frozen["attempts"], self.private["attempts"]):
            for key in ("packet_id", "case_id", "attempt_id", "system_config_sha256", "replicate"):
                self.assertEqual(row[key], attempt[key])
            if row["execution_outcome"] != "valid":
                self.assertIsNone(row["review_id"])
                self.assertEqual(row["claim_map"], {})
        self.assertEqual({row["replicate"] for row in self.private["attempts"]}, {0, 1})

    def test_frozen_identity_changes_fail_even_with_recomputed_manifest_hash(self):
        for key, value in (("case_id", "unknown"), ("packet_id", "packet-forged"),
                           ("system_config_sha256", "2" * 64), ("replicate", 10),
                           ("replicate", False), ("language_route", "en-en")):
            with self.subTest(key=key):
                bad = copy.deepcopy(self.frozen)
                if key == "language_route" and bad["attempts"][0][key] == value:
                    value = "ko-en"
                bad["attempts"][0][key] = value
                core = {k: v for k, v in bad.items() if k not in {"schema_version", "kind", "manifest_sha256", "terminal_sha256"}}
                bad["manifest_sha256"] = bad["terminal_sha256"] = digest(core)
                with self.assertRaisesRegex(ValueError, "identity"):
                    build_packets(self.dataset, bad, self.ledger, self.export_packets)

    def test_every_nonvalid_execution_outcome_is_kept_private_without_labels(self):
        for index, record in enumerate(self.records["records"]):
            outcome = EXECUTION_OUTCOMES[index % len(EXECUTION_OUTCOMES)]
            record["execution_outcome"] = outcome
            if outcome == "transport_failure":
                record.pop("raw_response")
                record.pop("raw_response_path")
                record["failure"] = "Synthetic transport failure fixture."
        self.refresh()
        packet, private, _, _ = self.build()
        self.assertEqual(len(packet["packets"]), self.ledger["execution_outcomes"]["valid"])
        self.assertEqual(private["execution_outcomes"], self.ledger["execution_outcomes"])
        self.assertTrue(all(row["claim_map"] == {} and row["review_id"] is None
                            for row in private["attempts"] if row["execution_outcome"] != "valid"))

    def test_rehashed_ledger_cannot_change_attempt_case_or_packet_linkage(self):
        for key, value in (("case_id", self.frozen["attempts"][2]["case_id"]),
                           ("packet_id", "packet-forged"), ("replicate", 99),
                           ("raw_response_sha256", "0" * 64)):
            with self.subTest(key=key):
                ledger = copy.deepcopy(self.ledger)
                ledger["entries"][0][key] = value
                previous = "0" * 64
                for row in ledger["entries"]:
                    row["previous_entry_sha256"] = previous
                    row["entry_sha256"] = digest({k: v for k, v in row.items() if k != "entry_sha256"})
                    previous = row["entry_sha256"]
                ledger["final_entry_sha256"] = previous
                ledger["ledger_sha256"] = digest({k: v for k, v in ledger.items() if k not in {"schema_version", "kind", "ledger_sha256"}})
                with self.assertRaises(ValueError):
                    build_packets(self.dataset, self.frozen, ledger, self.export_packets)

    def test_dataset_ledger_and_packet_hash_or_coverage_mismatch_is_rejected(self):
        inputs = [self.dataset, self.frozen, self.ledger, self.export_packets]
        for index, key in ((1, "manifest_sha256"), (2, "ledger_sha256"), (3, "packet_set_sha256")):
            with self.subTest(index=index):
                bad = copy.deepcopy(inputs)
                bad[index][key] = "0" * 64
                with self.assertRaises(ValueError):
                    build_packets(*bad)
        with self.assertRaisesRegex(ValueError, "dataset/export"):
            build_packets(generate_protocol(5, 8), *inputs[1:])
        for mutation in ("extra", "missing", "duplicate", "wrong_response", "nonvalid"):
            with self.subTest(mutation=mutation):
                packets = copy.deepcopy(self.export_packets)
                if mutation == "extra":
                    packets["packets"][0]["system_id"] = "leaked"
                elif mutation == "missing":
                    packets["packets"] = []
                elif mutation == "duplicate":
                    packets["packets"].append(copy.deepcopy(packets["packets"][0]))
                elif mutation == "wrong_response":
                    packets["packets"][0]["response"] = "changed"
                else:
                    packets["packets"][0]["packet_id"] = self.frozen["attempts"][1]["packet_id"]
                packets["packet_set_sha256"] = digest({"source_ledger_sha256": packets["source_ledger_sha256"], "packets": packets["packets"]})
                with self.assertRaisesRegex(ValueError, "packet export"):
                    build_packets(self.dataset, self.frozen, self.ledger, packets)

    def test_no_valid_outputs_gives_empty_reviews_and_preserves_failed_attempts(self):
        self.records["records"][0]["execution_outcome"] = "gate_rejection"
        self.refresh()
        packet, private, a, b = self.build()
        self.assertEqual(packet["packets"], [])
        self.assertEqual(a["cases"], [])
        self.assertEqual(b["cases"], [])
        self.assertEqual(len(private["attempts"]), len(self.frozen["attempts"]))

    def test_rejections_are_not_human_semantic_outcomes(self):
        self.completed_pair()
        for outcome in ("gate_rejection", "protective_rejection", "transport_failure"):
            self.a["cases"][0]["judgment"] = {"execution_outcome": outcome}
            with self.assertRaisesRegex(ValueError, "ledger outcomes stay separate"):
                freeze_reviews(self.packet, self.a, self.b)

    def test_incomplete_review_wrong_packet_and_same_reviewer_are_rejected(self):
        with self.assertRaises(ValueError):
            freeze_reviews(self.packet, self.a, self.b)
        self.completed_pair()
        for field, value in (("packet_sha256", "wrong"), ("reviewer_id", "test-reviewer-a"),
                             ("languages", ["en"]), ("independent_human_review", False), ("cases", [])):
            with self.subTest(field=field):
                bad = copy.deepcopy(self.b)
                bad[field] = value
                with self.assertRaises(ValueError):
                    freeze_reviews(self.packet, self.a, bad)

    def test_agreement_normalizes_order_but_keeps_initials_and_counts(self):
        self.completed_pair()
        self.b["cases"][0]["judgment"]["claims"].reverse()
        lock, resolution = freeze_reviews(self.packet, self.a, self.b)
        self.assertEqual(lock["agreement_counts"]["whole_judgment"], {"agree": 1, "compared": 1})
        self.assertEqual(lock["agreement_counts"]["semantic_preserved"], {"agree": 3, "compared": 3})
        self.assertEqual(resolution["cases"], [])
        self.third(resolution)
        result = reconcile(lock, resolution, digest(lock))
        self.assertEqual(result["cases"], self.a["cases"])
        self.a["cases"][0]["judgment"]["claims"].clear()
        self.assertEqual(len(lock["initial_reviews"][0]["cases"][0]["judgment"]["claims"]), 3)

    def test_disagreement_requires_third_reviewer_resolution_and_original_lock(self):
        self.completed_pair()
        self.b["cases"][0]["judgment"]["claims"][0]["semantic_preserved"] = False
        lock, resolution = freeze_reviews(self.packet, self.a, self.b)
        lock_hash = digest(lock)
        self.assertEqual(lock["agreement_counts"]["semantic_preserved"], {"agree": 2, "compared": 3})
        self.third(resolution)
        with self.assertRaisesRegex(ValueError, "rationale"):
            reconcile(lock, resolution, lock_hash)
        resolution["cases"][0] = copy.deepcopy(self.b["cases"][0])
        result = reconcile(lock, resolution, lock_hash)
        self.assertEqual(result["cases"][0]["judgment"], self.b["cases"][0]["judgment"])
        self.assertEqual(result["agreement_counts"], lock["agreement_counts"])
        self.assertTrue(lock["initial_reviews"][0]["cases"][0]["judgment"]["claims"][0]["semantic_preserved"])
        resolution["reviewer_id"] = "test-reviewer-a"
        with self.assertRaisesRegex(ValueError, "third"):
            reconcile(lock, resolution, lock_hash)
        lock["initial_reviews"][0]["cases"][0]["rationale"] = "tampered"
        with self.assertRaisesRegex(ValueError, "lock hash mismatch"):
            reconcile(lock, resolution, lock_hash)

    def test_non_valid_judgments_cannot_carry_labels_or_decisions(self):
        self.completed_pair()
        self.a["cases"][0]["judgment"] = {"execution_outcome": "unadjudicable"}
        lock, _ = freeze_reviews(self.packet, self.a, self.b)
        self.assertEqual(lock["agreement_counts"]["semantic_preserved"]["compared"], 0)
        self.a["cases"][0]["judgment"]["downstream_decision"] = "seek_corroboration"
        with self.assertRaisesRegex(ValueError, "non-valid"):
            freeze_reviews(self.packet, self.a, self.b)

    def test_packet_rejects_added_metadata_and_labels_for_missing_response(self):
        self.completed_pair()
        bad = copy.deepcopy(self.packet)
        bad["packets"][0]["system_id"] = "revealed"
        with self.assertRaisesRegex(ValueError, "packet fields"):
            freeze_reviews(bad, self.a, self.b)
        self.packet["packets"][0].update(response_text="")
        for review in (self.a, self.b):
            review["packet_sha256"] = digest(self.packet)
        with self.assertRaisesRegex(ValueError, "recorded response"):
            freeze_reviews(self.packet, self.a, self.b)

    def test_claim_omission_counts_and_unknown_claims(self):
        self.completed_pair()
        self.b["cases"][0]["judgment"]["claims"].pop()
        lock, _ = freeze_reviews(self.packet, self.a, self.b)
        self.assertEqual(lock["agreement_counts"]["claim_presence"], {"agree": 2, "compared": 3})
        self.assertEqual(lock["agreement_counts"]["semantic_preserved"]["compared"], 2)
        self.b["cases"][0]["judgment"]["claims"][0]["source_claim_id"] = "unknown"
        with self.assertRaisesRegex(ValueError, "unknown"):
            freeze_reviews(self.packet, self.a, self.b)

    def test_exclusive_writes_and_cli_preserve_existing_artifacts(self):
        script = Path(__file__).resolve().parents[1] / "adjudication_v2.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, value in (("dataset", self.dataset), ("manifest", self.frozen), ("ledger", self.ledger), ("packets", self.export_packets)):
                write_new(root / (name + ".json"), value)
            with self.assertRaises(FileExistsError):
                write_new(root / "ledger.json", {})
            args = [sys.executable, str(script), "build", "--dataset", str(root / "dataset.json"),
                    "--manifest", str(root / "manifest.json"), "--ledger", str(root / "ledger.json"),
                    "--packets", str(root / "packets.json"), "--output-dir", str(root / "packet")]
            first = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            original = (root / "packet" / "packet.json").read_bytes()
            second = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(second.returncode, 2)
            self.assertEqual((root / "packet" / "packet.json").read_bytes(), original)

    def test_freeze_and_reconciliation_cli_preserve_frozen_files(self):
        self.completed_pair()
        script = Path(__file__).resolve().parents[1] / "adjudication_v2.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, value in (("packet", self.packet), ("a", self.a), ("b", self.b)):
                write_new(root / (name + ".json"), value)
            frozen = root / "frozen"
            run = subprocess.run([sys.executable, str(script), "freeze", "--packet", str(root / "packet.json"),
                                  "--review-a", str(root / "a.json"), "--review-b", str(root / "b.json"),
                                  "--output-dir", str(frozen)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            lock_bytes = (frozen / "initial-lock.json").read_bytes()
            lock = json.loads(lock_bytes)
            resolution = json.loads((frozen / "reconciliation.json").read_text(encoding="utf-8"))
            self.third(resolution)
            write_new(root / "resolved.json", resolution)
            args = [sys.executable, str(script), "reconcile", "--lock", str(frozen / "initial-lock.json"),
                    "--lock-sha256", digest(lock), "--resolutions", str(root / "resolved.json"),
                    "--output", str(root / "final.json")]
            run = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual((frozen / "initial-lock.json").read_bytes(), lock_bytes)
            final_bytes = (root / "final.json").read_bytes()
            self.assertEqual(subprocess.run(args, capture_output=True).returncode, 2)
            self.assertEqual((root / "final.json").read_bytes(), final_bytes)


if __name__ == "__main__":
    unittest.main()
