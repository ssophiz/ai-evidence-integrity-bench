"""Synthetic software fixtures only; these are not human review results."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from adjudication_v2 import build_packets, digest, freeze_reviews, reconcile, write_new
from protocol_v2 import generate_protocol


class AdjudicationV2Tests(unittest.TestCase):
    def setUp(self):
        self.dataset = generate_protocol(5, 7)
        case = self.dataset["cases"][0]
        self.adapter = {"schema_version": "2.0", "attempts": [{
            "attempt_id": "attempt-secret-001", "case_id": case["case_id"],
            "system_id": "system-secret-name", "replicate": 1,
            "response_text": "검토 / review: " + " ".join((case["case_id"],
                case["semantic_family_id"], case["path_condition"],
                case["control_metadata"]["paired_case_id"],
                case["control_metadata"]["untrusted_stimulus_id"],
                case["evaluation"]["claims"][0]["claim_id"], "system-secret-name")),
            "execution_outcome": "valid",
        }]}
        self.packet, self.private, self.a, self.b = build_packets(self.dataset, self.adapter)

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
        case = self.dataset["cases"][0]
        for secret in (case["case_id"], case["semantic_family_id"], case["path_condition"],
                       case["control_metadata"]["paired_case_id"], case["control_metadata"]["untrusted_stimulus_id"],
                       "system-secret-name", "attempt-secret-001", "expected_downstream_decision",
                       case["evaluation"]["claims"][0]["claim_id"]):
            self.assertNotIn(secret, encoded)
        row = self.packet["packets"][0]
        self.assertIn("검토", row["response_text"])
        self.assertIn("[MASKED]", row["response_text"])
        self.assertEqual(len(row["source_claims"]), 3)
        self.assertEqual(self.private["attempts"][0]["response_text"], self.adapter["attempts"][0]["response_text"])
        self.assertTrue(self.private["attempts"][0]["masked_occurrences"])
        for review in (self.a, self.b):
            self.assertIsNone(review["cases"][0]["judgment"])
            self.assertIsNone(review["reviewer_id"])
            self.assertIsNone(review["independent_human_review"])

    def test_separate_builds_and_claims_have_fresh_opaque_ids(self):
        other, _, _, _ = build_packets(self.dataset, self.adapter)
        self.assertNotEqual(self.packet["packets"][0]["review_id"], other["packets"][0]["review_id"])
        self.assertNotEqual(self.packet["packets"][0]["source_claims"][0]["source_claim_id"],
                            other["packets"][0]["source_claims"][0]["source_claim_id"])

    def test_adapter_rejects_extra_unknown_duplicate_and_invalid_inputs(self):
        for field, value in (("extra", True), ("case_id", "unknown"), ("replicate", True),
                             ("response_text", None), ("execution_outcome", "unknown")):
            with self.subTest(field=field):
                bad = copy.deepcopy(self.adapter)
                bad["attempts"][0][field] = value
                with self.assertRaises(ValueError):
                    build_packets(self.dataset, bad)
        self.adapter["attempts"].append(copy.deepcopy(self.adapter["attempts"][0]))
        with self.assertRaisesRegex(ValueError, "unique"):
            build_packets(self.dataset, self.adapter)

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
        self.packet["packets"][0].update(response_text=None, reported_execution_outcome="transport_failure")
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
            write_new(root / "manifest.json", self.dataset)
            write_new(root / "attempts.json", self.adapter)
            with self.assertRaises(FileExistsError):
                write_new(root / "attempts.json", {})
            args = [sys.executable, str(script), "build", "--manifest", str(root / "manifest.json"),
                    "--attempts", str(root / "attempts.json"), "--output-dir", str(root / "packet")]
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
