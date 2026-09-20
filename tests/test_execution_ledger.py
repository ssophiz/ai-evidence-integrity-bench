import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from execution_ledger import (
    PROMPT_FIELDS,
    freeze_attempts,
    import_records,
    export_adjudication_packets,
)
from protocol_v2 import generate_protocol, model_view


REVISION = "1" * 40


class ExecutionLedgerTests(unittest.TestCase):
    def setUp(self):
        self.exported = model_view(generate_protocol(5, 7), "dev")
        self.config = {
            "system_id": "fixture-a",
            "baseline": False,
            "model": {"provider": "fixture", "name": "recorded-output-only"},
            "runtime": "unavailable",
            "temperature": 0,
            "seed": 17,
        }
        self.manifest = freeze_attempts(
            self.exported, self.config, REVISION, "dev", replicates=2
        )

    def records(self):
        return {
            "schema_version": "1.0",
            "records": [
                {
                    "attempt_id": attempt["attempt_id"],
                    "case_id": attempt["case_id"],
                    "stage": "completed",
                    "request_number": 1,
                    "retry_number": 0,
                    "execution_outcome": "valid",
                    "raw_response": f"recorded-{attempt['sequence']}",
                    "raw_response_path": f"artifacts/{attempt['attempt_id']}.txt",
                }
                for attempt in self.manifest["attempts"]
            ],
        }

    def test_freeze_is_deterministic_and_keys_case_system_and_replicate(self):
        again = freeze_attempts(self.exported, self.config, REVISION, "dev", 2)
        self.assertEqual(self.manifest, again)
        self.assertEqual(len(self.manifest["attempts"]), len(self.exported["cases"]) * 2)
        self.assertEqual(self.manifest["replicates"], 2)
        self.assertEqual(
            self.manifest["attempt_universe"],
            [case["case_id"] for case in self.exported["cases"]],
        )
        self.assertEqual(
            {attempt["replicate"] for attempt in self.manifest["attempts"]}, {0, 1}
        )
        changed = freeze_attempts(
            self.exported, {**self.config, "temperature": 1}, REVISION, "dev", 2
        )
        self.assertNotEqual(
            [row["attempt_id"] for row in self.manifest["attempts"]],
            [row["attempt_id"] for row in changed["attempts"]],
        )

    def test_family_and_condition_are_private_metadata_not_prompt_identity_fields(self):
        attempt = self.manifest["attempts"][0]
        self.assertIn("semantic_family_id", attempt)
        self.assertIn("path_condition", attempt)
        self.assertIn("paired_case_id", attempt)
        self.assertEqual(
            set(PROMPT_FIELDS), {"instruction", "evidence_text", "untrusted_text"}
        )
        self.assertNotIn("case_id", PROMPT_FIELDS)

    def test_import_is_order_invariant_and_complete(self):
        records = self.records()
        ledger = import_records(self.manifest, records)
        reversed_records = copy.deepcopy(records)
        reversed_records["records"].reverse()
        self.assertEqual(ledger, import_records(self.manifest, reversed_records))
        self.assertEqual(len(ledger["entries"]), len(self.manifest["attempts"]))
        self.assertEqual(
            sum(ledger["execution_outcomes"].values()), len(self.manifest["attempts"])
        )
        self.assertEqual(
            ledger["counts"],
            {
                "scheduled_attempts": len(self.manifest["attempts"]),
                "started_attempts": len(self.manifest["attempts"]),
                "completed_attempts": len(self.manifest["attempts"]),
                "requests": len(self.manifest["attempts"]),
            },
        )

    def test_import_rejects_duplicate_drop_unknown_and_case_mismatch(self):
        records = self.records()

        duplicate = copy.deepcopy(records)
        duplicate["records"].append(copy.deepcopy(duplicate["records"][0]))
        with self.assertRaisesRegex(ValueError, "retry-until-success"):
            import_records(self.manifest, duplicate)

        dropped = copy.deepcopy(records)
        dropped["records"].pop()
        with self.assertRaisesRegex(ValueError, "dropped attempt"):
            import_records(self.manifest, dropped)

        unknown = copy.deepcopy(records)
        unknown["records"][0]["attempt_id"] = "attempt-unknown"
        with self.assertRaisesRegex(ValueError, "unknown attempt"):
            import_records(self.manifest, unknown)

        mismatched = copy.deepcopy(records)
        mismatched["records"][0]["case_id"] = "other-case"
        with self.assertRaisesRegex(ValueError, "attempt/case mismatch"):
            import_records(self.manifest, mismatched)

    def test_transport_failure_and_output_outcomes_are_recorded_exactly_once(self):
        records = self.records()
        records["records"][0] = {
            "attempt_id": self.manifest["attempts"][0]["attempt_id"],
            "case_id": self.manifest["attempts"][0]["case_id"],
            "stage": "completed",
            "request_number": 1,
            "retry_number": 0,
            "execution_outcome": "transport_failure",
            "failure": "recorded timeout",
        }
        records["records"][1]["execution_outcome"] = "schema_failure"
        ledger = import_records(self.manifest, records)
        self.assertEqual(ledger["execution_outcomes"]["transport_failure"], 1)
        self.assertEqual(ledger["execution_outcomes"]["schema_failure"], 1)
        self.assertEqual(ledger["entries"][0]["failure"], "recorded timeout")
        self.assertIn("raw_response_sha256", ledger["entries"][1])
        self.assertEqual(
            ledger["entries"][1]["raw_response_sha256"],
            hashlib.sha256(ledger["entries"][1]["raw_response"].encode()).hexdigest(),
        )

    def test_retry_and_downstream_decision_are_rejected(self):
        retry = self.records()
        retry["records"][0]["retry_number"] = 1
        retry["records"][0]["request_number"] = 2
        with self.assertRaisesRegex(ValueError, "request number|retry-until-success"):
            import_records(self.manifest, retry)

        leaked_label = self.records()
        leaked_label["records"][0]["downstream_decision"] = "preserve_and_review"
        leaked_label["records"][0]["execution_outcome"] = "schema_failure"
        with self.assertRaisesRegex(ValueError, "unexpected record field"):
            import_records(self.manifest, leaked_label)

    def test_gate_rejection_is_distinct_from_model_refusal(self):
        records = self.records()
        records["records"][0]["execution_outcome"] = "gate_rejection"
        records["records"][1]["execution_outcome"] = "protective_rejection"
        ledger = import_records(self.manifest, records)
        self.assertEqual(ledger["execution_outcomes"]["gate_rejection"], 1)
        self.assertEqual(ledger["execution_outcomes"]["protective_rejection"], 1)

    def test_blinded_packets_use_opaque_ids_and_exclude_control_information(self):
        ledger = import_records(self.manifest, self.records())
        packet_set = export_adjudication_packets(
            self.exported, self.manifest, ledger
        )
        self.assertEqual(len(packet_set["packets"]), len(self.manifest["attempts"]))
        forbidden = {
            "case_id",
            "attempt_id",
            "system",
            "system_config",
            "system_config_sha256",
            "path_condition",
            "control_metadata",
            "semantic_family_id",
            "paired_case_id",
            "untrusted_stimulus_id",
            "language_route",
            "input_language",
            "output_language",
            "expected_downstream_decision",
            "evaluation",
            "replicate",
        }

        def keys(value):
            if isinstance(value, dict):
                return set(value) | set().union(*(keys(item) for item in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(item) for item in value)) if value else set()
            return set()

        self.assertFalse(keys(packet_set["packets"]) & forbidden)
        self.assertTrue(
            all(packet["packet_id"].startswith("packet-") for packet in packet_set["packets"])
        )

    def test_tampering_breaks_manifest_ledger_and_export_binding(self):
        records = self.records()
        ledger = import_records(self.manifest, records)
        tampered_manifest = copy.deepcopy(self.manifest)
        tampered_manifest["attempts"][0]["prompt_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "manifest hash mismatch"):
            import_records(tampered_manifest, records)

        tampered_ledger = copy.deepcopy(ledger)
        tampered_ledger["entries"][0]["raw_response"] = "changed"
        with self.assertRaisesRegex(ValueError, "ledger hash mismatch"):
            export_adjudication_packets(self.exported, self.manifest, tampered_ledger)

        tampered_export = copy.deepcopy(self.exported)
        tampered_export["cases"][0]["instruction"] += " changed"
        with self.assertRaisesRegex(ValueError, "export/manifest mismatch"):
            export_adjudication_packets(tampered_export, self.manifest, ledger)

    def test_private_manifest_is_rejected_as_export(self):
        private_manifest = generate_protocol(5, 7)
        with self.assertRaisesRegex(ValueError, "export field drift"):
            freeze_attempts(private_manifest, self.config, REVISION, "dev")

    def test_cli_refuses_to_overwrite_an_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = root / "inputs.json"
            config = root / "config.json"
            inputs.write_text(json.dumps(self.exported), encoding="utf-8")
            config.write_text(json.dumps(self.config), encoding="utf-8")
            original = inputs.read_bytes()
            result = subprocess.run(
                [
                    sys.executable,
                    "execution_ledger.py",
                    "freeze",
                    "--inputs",
                    str(inputs),
                    "--system-config",
                    str(config),
                    "--source-revision",
                    REVISION,
                    "--selected-split",
                    "dev",
                    "--output",
                    str(inputs),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(inputs.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
