import unittest

from arsenal_demo import demo_data, render_demo, route, validated_address


class ArsenalDemoTests(unittest.TestCase):
    def test_demo_is_deterministic_and_shows_both_paths(self):
        first = render_demo()
        self.assertEqual(first, render_demo())
        page = first.decode("utf-8")
        self.assertIn("Path A / unprotected", page)
        self.assertIn("Path B / provenance enforced", page)
        self.assertIn("Gate verdict: FAIL", page)
        self.assertIn("Structural verdict: 1/1 unknown IDs rejected", page)
        self.assertIn("Semantic review:</strong> REQUIRED", page)
        self.assertIn("Status:</strong> reported", page)
        self.assertIn("Authority:</strong> analyst_note", page)
        self.assertIn("Illustrative unchecked downstream decision:", page)
        self.assertIn(
            "Illustrative downstream decision if semantic promotion is rejected:", page
        )
        self.assertEqual(
            page.count("Expected policy decision:</strong> seek_corroboration"), 2
        )
        self.assertNotIn("Downstream decision after review:", page)
        self.assertIn("Completed:</strong> 0/1", page)
        self.assertIn("Missing outcome:</strong> 1/1", page)
        self.assertIn("분석관 메모", page)
        self.assertIn("not a recorded model or live-system output", page)
        self.assertIn("&lt;script&gt;alert(&#x27;evidence&#x27;)&lt;/script&gt;", page)
        self.assertNotIn("<script>alert('evidence')</script>", page)
        self.assertIn("does not prove", page)

    def test_gate_rejects_injected_claim(self):
        data = demo_data()
        self.assertEqual(len(data["accepted"]), 1)
        self.assertEqual(len(data["rejected"]), 1)
        self.assertEqual(
            data["rejected"][0]["source_claim_id"], "attacker-injected-claim"
        )
        self.assertEqual(data["accepted"][0]["verification_status"], "verified")
        self.assertEqual(data["accepted"][0]["authority_tier"], "artifact")

    def test_route_allowlist_rejects_traversal_and_unknown_paths(self):
        for path in ("/../README.md", "/%2e%2e/README.md", "/demo", "//README.md"):
            with self.subTest(path=path):
                status, _, body = route(path)
                self.assertEqual(status, 404)
                self.assertEqual(body, b"not found\n")
        self.assertEqual(route("/healthz")[0], 200)

    def test_bind_address_requires_loopback_and_valid_port(self):
        self.assertEqual(validated_address("127.0.0.1", 8765), ("127.0.0.1", 8765))
        self.assertEqual(validated_address("localhost", 8765), ("localhost", 8765))
        invalid = (("0.0.0.0", 8765), ("::1", 8765), ("example.com", 8765), ("localhost", 0), ("localhost", 65536))
        for host, port in invalid:
            with self.subTest(host=host, port=port):
                with self.assertRaises(ValueError):
                    validated_address(host, port)


if __name__ == "__main__":
    unittest.main()
