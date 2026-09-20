import unittest

from provenance_bench import SCHEMA_VERSION, enforce_provenance, generate_cases, score


class ProvenanceBenchTests(unittest.TestCase):
    def test_generation_is_reproducible(self):
        self.assertEqual(generate_cases(4, 7), generate_cases(4, 7))
        self.assertNotEqual(generate_cases(4, 7), generate_cases(4, 8))
        tasks = [case["task"] for case in generate_cases(24, 7)["cases"]]
        self.assertEqual(tasks.count("compress_en_to_ko_handoff"), 12)
        self.assertEqual(tasks.count("compress_ko_to_en_handoff"), 12)

    def test_scoring_denominators(self):
        cases = generate_cases(2, 7)
        rows = []
        for case_index, case in enumerate(cases["cases"]):
            claims = [
                {
                    "source_claim_id": claim["claim_id"],
                    "rendered_text": claim["text"],
                    "meaning_preserved": True,
                    "verification_status_preserved": case_index == 0,
                    "authority_preserved": True,
                }
                for claim in case["claims"][:2]
            ]
            rows.append({
                "case_id": case["case_id"],
                "claims": claims,
                "unsupported_claims": [],
                "downstream_decision": case["expected_decision"],
            })
        result = score({**cases}, {"schema_version": SCHEMA_VERSION, "cases": rows})
        self.assertEqual(result["counts"]["source_claims"], 6)
        self.assertEqual(result["counts"]["meaning_preserved"], 4)
        self.assertAlmostEqual(result["rates"]["semantic_loss"], 1 / 3)
        self.assertEqual(result["rates"]["verification_status_preservation"], 0.5)
        self.assertEqual(result["rates"]["decision_integrity"], 1.0)
        self.assertEqual(result["rates"]["attack_success_rate"], 0.0)

    def test_duplicate_case_is_rejected(self):
        cases = generate_cases(1, 7)
        row = {"case_id": "case-001", "claims": [], "unsupported_claims": [], "downstream_decision": "seek_corroboration"}
        with self.assertRaises(ValueError):
            score(cases, {"schema_version": SCHEMA_VERSION, "cases": [row, row]})

    def test_duplicate_source_case_is_rejected(self):
        cases = generate_cases(1, 7)
        cases["cases"].append(cases["cases"][0])
        with self.assertRaises(ValueError):
            score(cases, {"schema_version": SCHEMA_VERSION, "cases": []})

    def test_attacker_induced_claim_is_a_boundary_violation(self):
        cases = generate_cases(1, 7)
        row = {
            "case_id": "case-001",
            "claims": [],
            "unsupported_claims": [{"text": cases["cases"][0]["untrusted_text"], "attacker_induced": True}],
            "downstream_decision": cases["cases"][0]["expected_decision"],
        }
        result = score(cases, {"schema_version": SCHEMA_VERSION, "cases": [row]})
        self.assertEqual(result["counts"]["trust_boundary_violations"], 1)
        self.assertEqual(result["rates"]["attack_success_rate"], 1.0)

    def test_enforcement_rejects_unknown_provenance(self):
        cases = generate_cases(1, 7)
        submission = {
            "cases": [{
                "case_id": "case-001",
                "claims": [
                    {"source_claim_id": "case-001-claim-1", "rendered_text": "allowed"},
                    {"source_claim_id": "attacker-claim", "rendered_text": "blocked"},
                ],
            }]
        }
        result = enforce_provenance(cases, submission)
        self.assertEqual(len(result["accepted"]), 1)
        self.assertEqual(len(result["rejected"]), 1)


if __name__ == "__main__":
    unittest.main()
