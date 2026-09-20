import copy
import json
import re
import unittest

from protocol_v2 import (
    EXECUTION_OUTCOMES,
    LANGUAGE_ROUTES,
    PATH_CONDITIONS,
    SCHEMA_VERSION,
    generate_protocol,
    model_view,
    score_protocol,
    validate_dataset,
)


class ProtocolV2Tests(unittest.TestCase):
    def test_generation_is_reproducible_and_seeded(self):
        self.assertEqual(generate_protocol(10, 7), generate_protocol(10, 7))
        self.assertNotEqual(generate_protocol(10, 7), generate_protocol(10, 8))

    def test_each_split_is_route_and_control_balanced(self):
        dataset = generate_protocol(20, 7)
        for split in ("dev", "pilot", "test"):
            rows = [row for row in dataset["cases"] if row["split"] == split]
            route_counts = {route: sum(row["language_route"] == route for row in rows) for route in LANGUAGE_ROUTES}
            condition_counts = {condition: sum(row["path_condition"] == condition for row in rows) for condition in PATH_CONDITIONS}
            self.assertEqual(len(set(route_counts.values())), 1)
            self.assertEqual(len(set(condition_counts.values())), 1)

    def test_semantic_families_do_not_cross_splits(self):
        dataset = generate_protocol(20, 7)
        family_splits = {}
        for row in dataset["cases"]:
            family_splits.setdefault(row["semantic_family_id"], set()).add(row["split"])
        self.assertTrue(all(len(splits) == 1 for splits in family_splits.values()))
        broken = copy.deepcopy(dataset)
        broken["cases"][0]["split"] = "pilot" if broken["cases"][0]["split"] != "pilot" else "dev"
        with self.assertRaisesRegex(ValueError, "split leakage"):
            validate_dataset(broken)

    def test_normalized_claim_sets_are_unique_across_splits(self):
        dataset = generate_protocol(20, 7)
        normalized = {}
        for row in dataset["cases"]:
            family_id = row["semantic_family_id"]
            claims = tuple(sorted(
                (claim["authority_tier"], claim["verification_status"], claim["text_en"], claim["text_ko"])
                for claim in row["evaluation"]["claims"]
            ))
            normalized.setdefault(family_id, claims)
        self.assertEqual(len(normalized), len(set(normalized.values())))

    def test_opaque_ids_do_not_restore_the_legacy_periodic_signal(self):
        dataset = generate_protocol(20, 20260920)
        outcomes = {}
        for row in dataset["cases"]:
            outcomes.setdefault(
                row["semantic_family_id"],
                row["evaluation"]["expected_downstream_decision"],
            )
        self.assertTrue(all(re.fullmatch(r"sf-[0-9a-f]{16}", family_id) for family_id in outcomes))
        predictions = {
            family_id: (
                "seek_corroboration"
                if int(family_id.removeprefix("sf-"), 16) % 3 == 0
                else "preserve_and_review"
            )
            for family_id in outcomes
        }
        periodic_accuracy = sum(
            predictions[family_id] == expected for family_id, expected in outcomes.items()
        ) / len(outcomes)
        majority_baseline = max(
            sum(expected == decision for expected in outcomes.values())
            for decision in ("preserve_and_review", "seek_corroboration")
        ) / len(outcomes)
        self.assertLessEqual(periodic_accuracy, majority_baseline)

    def test_model_view_does_not_leak_policy_or_expected_decision(self):
        view = model_view(generate_protocol(5, 7), "test")
        serialized = json.dumps(view, ensure_ascii=False)
        for secret in ("expected_downstream_decision", "evaluation_policy_id", '"evaluation"'):
            self.assertNotIn(secret, serialized)
        self.assertTrue(all("control_metadata" in row for row in view["cases"]))

    def test_model_input_rejects_injected_fields_and_mismatched_case_id(self):
        injected = generate_protocol(5, 7)
        injected["cases"][0]["model_input"]["expected_downstream_decision"] = "sentinel"
        with self.assertRaisesRegex(ValueError, "strict allowlist"):
            model_view(injected)
        mismatched = generate_protocol(5, 7)
        mismatched["cases"][0]["model_input"]["case_id"] = "wrong-case"
        with self.assertRaisesRegex(ValueError, "must match"):
            model_view(mismatched)
        metadata_injected = generate_protocol(5, 7)
        metadata_injected["cases"][0]["control_metadata"]["expected_downstream_decision"] = "sentinel"
        with self.assertRaisesRegex(ValueError, "strict allowlist"):
            model_view(metadata_injected)
        ordinal = generate_protocol(5, 7)
        ordinal["cases"][0]["semantic_family_id"] = "family-001"
        with self.assertRaisesRegex(ValueError, "opaque hash"):
            model_view(ordinal)

    def test_each_family_uses_one_bilingual_untrusted_template(self):
        dataset = generate_protocol(20, 7)
        by_family = {}
        for row in dataset["cases"]:
            family = by_family.setdefault(row["semantic_family_id"], {"ids": set(), "text_by_language": {}})
            family["ids"].add(row["control_metadata"]["untrusted_stimulus_id"])
            language = row["model_input"]["input_language"]
            family["text_by_language"].setdefault(language, set()).add(row["model_input"]["untrusted_text"])
        for family in by_family.values():
            self.assertEqual(len(family["ids"]), 1)
            self.assertEqual(set(family["text_by_language"]), {"ko", "en"})
            self.assertTrue(all(len(texts) == 1 for texts in family["text_by_language"].values()))

    def test_bilingual_source_and_untrusted_text_are_natural_language(self):
        rows = model_view(generate_protocol(5, 7))["cases"]
        korean = [row for row in rows if row["input_language"] == "ko"]
        english = [row for row in rows if row["input_language"] == "en"]
        self.assertTrue(all(any("가" <= char <= "힣" for char in row["evidence_text"]) for row in korean))
        self.assertTrue(all(any("가" <= char <= "힣" for char in row["untrusted_text"]) for row in korean))
        self.assertTrue(all(" " in row["evidence_text"] and " " in row["untrusted_text"] for row in english))

    def test_failure_accounting_and_denominators_are_explicit(self):
        dataset = generate_protocol(5, 7)
        rows = []
        for index, case in enumerate(dataset["cases"]):
            outcome = EXECUTION_OUTCOMES[index % len(EXECUTION_OUTCOMES)]
            row = {"case_id": case["case_id"], "execution_outcome": outcome}
            if outcome == "valid":
                claim = case["evaluation"]["claims"][0]
                row.update({
                    "claims": [{
                        "source_claim_id": claim["claim_id"],
                        "semantic_preserved": True,
                        "verification_relation": "strengthened",
                        "authority_relation": "misattributed",
                    }],
                    "unsupported_claims": [{"text": "Unsupported statement."}],
                    "downstream_decision": case["evaluation"]["expected_downstream_decision"],
                })
            rows.append(row)
        report = score_protocol(dataset, {"schema_version": SCHEMA_VERSION, "cases": rows})
        self.assertEqual(sum(report["execution_outcomes"].values()), len(dataset["cases"]))
        self.assertEqual(report["counts"]["attempted_cases"], len(dataset["cases"]))
        self.assertEqual(report["counts"]["verification_strengthenings"], report["counts"]["valid_cases"])
        self.assertEqual(report["counts"]["authority_misattributions"], report["counts"]["valid_cases"])
        self.assertLess(report["rates"]["semantic_retention_all_attempt_task_credit"], report["rates"]["semantic_retention_valid_outputs"])

    def test_all_non_valid_results_keep_semantic_rates_null(self):
        dataset = generate_protocol(5, 7)
        rows = [
            {"case_id": case["case_id"], "execution_outcome": "schema_failure"}
            for case in dataset["cases"]
        ]
        report = score_protocol(dataset, {"schema_version": SCHEMA_VERSION, "cases": rows})
        self.assertIsNone(report["rates"]["semantic_retention_valid_outputs"])
        self.assertEqual(report["rates"]["semantic_retention_all_attempt_task_credit"], 0.0)
        self.assertEqual(report["execution_outcomes"]["schema_failure"], len(rows))

    def test_non_valid_outcome_cannot_smuggle_semantic_labels(self):
        dataset = generate_protocol(5, 7)
        rows = [
            {"case_id": case["case_id"], "execution_outcome": "transport_failure"}
            for case in dataset["cases"]
        ]
        rows[0]["claims"] = [{"source_claim_id": "x"}]
        with self.assertRaisesRegex(ValueError, "cannot carry semantic labels"):
            score_protocol(dataset, {"schema_version": SCHEMA_VERSION, "cases": rows})


if __name__ == "__main__":
    unittest.main()
