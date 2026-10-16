import unittest
import itertools
import json
import re
import os
import sys

# Ensure tests can import genlayer mock and contracts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import genlayer
gl = genlayer.gl

from contracts.SourceDriftLedger import (
    _parse_iso8601_utc,
    _clean_html,
    _normalize_text,
    _normalize_title,
    _validate_baseline_url,
    _validate_target_url,
    _compute_lexical_overlap,
    _select_windows_for_quotes,
    _segment_passages,
    _map_element_statuses_to_class,
    _map_class_to_status,
    INSPECTION_BUDGET_CHARS,
    RELEVANCE_THRESHOLD,
)
from contracts.ClaimsBoard import _derive_badge_from_status


class TestLayer1Pure(unittest.TestCase):

    def test_utc_parsing_offsets_and_boundaries(self):
        # 1. UTC with 'Z' suffix
        ts1, iso1 = _parse_iso8601_utc("2026-10-16T12:00:00Z")
        self.assertEqual(iso1, "2026-10-16T12:00:00Z")

        # 2. Fractional seconds
        ts2, iso2 = _parse_iso8601_utc("2026-10-16T12:00:00.123456Z")
        self.assertEqual(ts2, ts1)
        self.assertEqual(iso2, "2026-10-16T12:00:00Z")

        # 3. Positive offset (+07:00)
        ts3, iso3 = _parse_iso8601_utc("2026-10-16T19:00:00+07:00")
        self.assertEqual(ts3, ts1)
        self.assertEqual(iso3, "2026-10-16T12:00:00Z")

        # 4. Negative offset (-05:00)
        ts4, iso4 = _parse_iso8601_utc("2026-10-16T07:00:00-05:00")
        self.assertEqual(ts4, ts1)
        self.assertEqual(iso4, "2026-10-16T12:00:00Z")

        # 5. Midnight boundary
        ts5, iso5 = _parse_iso8601_utc("2026-10-16T00:00:00Z")
        self.assertTrue(iso5.endswith("T00:00:00Z"))

        # Rejections
        with self.assertRaises(gl.vm.UserError):
            _parse_iso8601_utc("not-a-date")
        with self.assertRaises(gl.vm.UserError):
            _parse_iso8601_utc("")
        with self.assertRaises(gl.vm.UserError):
            _parse_iso8601_utc(12345)

    def test_shared_normalization(self):
        raw = "The\u00a0‘Dark\u2019 “Side” of the Moon\u20141973 [1][note 2][citation needed] &amp; more."
        norm = _normalize_text(raw)
        self.assertEqual(norm, "the 'dark' \"side\" of the moon-1973 & more.")

        # Entity unescaping and dash unification
        raw2 = "Temperature &lt; 100&#176;C \u2212 50&#176;C"
        norm2 = _normalize_text(raw2)
        self.assertIn("100", norm2)
        self.assertIn("-", norm2)

    def test_clean_html_strips_boilerplate(self):
        html = """
        <html>
        <head><script>alert('xss');</script><style>body { color: red; }</style></head>
        <body>
          <nav>Navigation links</nav>
          <header>Site Header</header>
          <p>Alan Turing was a mathematician.</p>
          <footer>Footer content</footer>
        </body>
        </html>
        """
        cleaned = _clean_html(html)
        self.assertEqual(cleaned, "Alan Turing was a mathematician.")
        self.assertNotIn("Navigation", cleaned)
        self.assertNotIn("Header", cleaned)
        self.assertNotIn("Footer", cleaned)
        self.assertNotIn("alert", cleaned)

    def test_title_normalization_and_binding(self):
        # 1. Percent encoded title
        t1 = _normalize_title("Alan%20Turing")
        self.assertEqual(t1, "Alan Turing")

        # 2. Underscores
        t2 = _normalize_title("Alan_Turing")
        self.assertEqual(t2, "Alan Turing")

        # 3. Lowercase initial letter normalized to uppercase
        t3 = _normalize_title("alan_Turing")
        self.assertEqual(t3, "Alan Turing")

        # 4. Collapse extra spaces
        t4 = _normalize_title("  Alan    Turing  ")
        self.assertEqual(t4, "Alan Turing")

    def test_url_parser_security_and_spoofs(self):
        valid_baseline = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=123456"
        canon, host, title, oldid = _validate_baseline_url(valid_baseline)
        self.assertEqual(host, "en.wikipedia.org")
        self.assertEqual(title, "Alan Turing")
        self.assertEqual(oldid, "123456")

        # Rejection: non-https
        with self.assertRaises(gl.vm.UserError):
            _validate_baseline_url("http://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=123456")

        # Rejection: userinfo spoof
        with self.assertRaises(gl.vm.UserError):
            _validate_baseline_url("https://user:pass@en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=123456")

        # Rejection: non-default port
        with self.assertRaises(gl.vm.UserError):
            _validate_baseline_url("https://en.wikipedia.org:8080/w/index.php?title=Alan_Turing&oldid=123456")

        # Rejection: fragment in baseline
        with self.assertRaises(gl.vm.UserError):
            _validate_baseline_url("https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=123456#Early_life")

        # Rejection: IP literal (IPv4)
        with self.assertRaises(gl.vm.UserError):
            _validate_baseline_url("https://127.0.0.1/w/index.php?title=Alan_Turing&oldid=123456")

        # Rejection: localhost
        with self.assertRaises(gl.vm.UserError):
            _validate_baseline_url("https://localhost/w/index.php?title=Alan_Turing&oldid=123456")

        # Rejection: backslashes
        with self.assertRaises(gl.vm.UserError):
            _validate_baseline_url("https://en.wikipedia.org\\w/index.php?title=Alan_Turing&oldid=123456")

        # Rejection: look-alike host spoof (subdomain on attacker domain)
        with self.assertRaises(gl.vm.UserError):
            _validate_baseline_url("https://en.wikipedia.org.evil.com/w/index.php?title=Alan_Turing&oldid=123456")

        # Rejection: trailing dot
        with self.assertRaises(gl.vm.UserError):
            _validate_baseline_url("https://en.wikipedia.org./w/index.php?title=Alan_Turing&oldid=123456")

        # Rejection: non-permalink path
        with self.assertRaises(gl.vm.UserError):
            _validate_baseline_url("https://en.wikipedia.org/wiki/Alan_Turing")

        # Rejection: missing oldid or non-digits oldid
        with self.assertRaises(gl.vm.UserError):
            _validate_baseline_url("https://en.wikipedia.org/w/index.php?title=Alan_Turing")
        with self.assertRaises(gl.vm.UserError):
            _validate_baseline_url("https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=latest")

    def test_target_url_binding_and_oldid_ordering(self):
        base_host = "en.wikipedia.org"
        base_title = "Alan Turing"
        base_oldid = "1000"

        # Valid REVISION target later than baseline
        c_url, kind, oldid = _validate_target_url(
            "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=2000",
            base_host, base_title, base_oldid
        )
        self.assertEqual(kind, "REVISION")
        self.assertEqual(oldid, "2000")

        # Valid LIVE target
        c_url2, kind2, oldid2 = _validate_target_url(
            "https://en.wikipedia.org/wiki/Alan_Turing",
            base_host, base_title, base_oldid
        )
        self.assertEqual(kind2, "LIVE")
        self.assertIsNone(oldid2)

        # Rejection: older or equal oldid
        with self.assertRaises(gl.vm.UserError) as cm:
            _validate_target_url(
                "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1000",
                base_host, base_title, base_oldid
            )
        self.assertIn("later than baseline", str(cm.exception))

        with self.assertRaises(gl.vm.UserError) as cm:
            _validate_target_url(
                "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=999",
                base_host, base_title, base_oldid
            )
        self.assertIn("later than baseline", str(cm.exception))

        # Rejection: cross-page target
        with self.assertRaises(gl.vm.UserError) as cm:
            _validate_target_url(
                "https://en.wikipedia.org/w/index.php?title=Alonzo_Church&oldid=2000",
                base_host, base_title, base_oldid
            )
        self.assertIn("match baseline title", str(cm.exception))

        # Rejection: cross-host target
        with self.assertRaises(gl.vm.UserError) as cm:
            _validate_target_url(
                "https://de.wikipedia.org/w/index.php?title=Alan_Turing&oldid=2000",
                base_host, base_title, base_oldid
            )
        self.assertIn("host must match", str(cm.exception))

        # Rejection: LIVE target with query or fragment
        with self.assertRaises(gl.vm.UserError):
            _validate_target_url(
                "https://en.wikipedia.org/wiki/Alan_Turing?action=view",
                base_host, base_title, base_oldid
            )
        with self.assertRaises(gl.vm.UserError):
            _validate_target_url(
                "https://en.wikipedia.org/wiki/Alan_Turing#Biography",
                base_host, base_title, base_oldid
            )

    def test_drift_class_matrix_against_reference_implementation(self):
        """
        Verify the class mapping against an independent reference implementation
        for all combinations of 1..4 elements with statuses {SAME, REPHRASED, CHANGED, ABSENT}.
        """
        def reference_mapping(statuses: list[str]) -> str:
            if "CHANGED" in statuses:
                return "MATERIAL"
            if "ABSENT" in statuses:
                return "REMOVED"
            if "REPHRASED" in statuses:
                return "COSMETIC"
            if all(s == "SAME" for s in statuses):
                return "UNCHANGED"
            return "UNKNOWN"

        all_statuses = ["SAME", "REPHRASED", "CHANGED", "ABSENT"]
        count = 0
        for n in range(1, 5):
            for combo in itertools.product(all_statuses, repeat=n):
                expected = reference_mapping(list(combo))
                actual = _map_element_statuses_to_class(list(combo))
                self.assertEqual(actual, expected, f"Failed on combo: {combo}")
                count += 1

        self.assertEqual(count, 4 + 16 + 64 + 256)  # 340 total combinations

    def test_status_mapping_and_consumer_badges(self):
        # Ledger status mapping
        self.assertEqual(_map_class_to_status("UNCHANGED"), "HEALTHY")
        self.assertEqual(_map_class_to_status("COSMETIC"), "HEALTHY")
        self.assertEqual(_map_class_to_status("MATERIAL"), "DRIFTED")
        self.assertEqual(_map_class_to_status("REMOVED"), "REMOVED")

        # ClaimsBoard badge derivation
        self.assertEqual(_derive_badge_from_status("UNAUDITED|NONE|0|NONE"), "UNAUDITED")
        self.assertEqual(_derive_badge_from_status("HEALTHY|UNCHANGED|1|2026-10-16T12:00:00Z"), "VERIFIED")
        self.assertEqual(_derive_badge_from_status("HEALTHY|COSMETIC|2|2026-10-16T12:00:00Z"), "REPHRASED")
        self.assertEqual(_derive_badge_from_status("DRIFTED|MATERIAL|3|2026-10-16T12:00:00Z"), "DRIFTED")
        self.assertEqual(_derive_badge_from_status("REMOVED|REMOVED|4|2026-10-16T12:00:00Z"), "REMOVED")

    def test_exact_budget_and_separator_accounting(self):
        # Create a document longer than budget
        paragraphs = ["Paragraph " + str(i) + " contains details about Alan Turing." * 50 for i in range(20)]
        long_doc = "\n\n".join(paragraphs)
        self.assertGreater(len(long_doc), INSPECTION_BUDGET_CHARS)

        quote = "Alan Turing was an English mathematician and computer scientist"
        inspected, windows, cov, total, inspected_len, trunc = _select_windows_for_quotes(long_doc, [quote])

        self.assertLessEqual(len(inspected), INSPECTION_BUDGET_CHARS)
        self.assertEqual(inspected_len, len(inspected))
        self.assertEqual(cov, "SELECTED_WINDOWS")

        # Check passage segmentation
        passages = _segment_passages(inspected)
        self.assertGreater(len(passages), 0)
        for p in passages:
            self.assertTrue(p["id"].startswith("p"))
            self.assertGreaterEqual(len(p["text"]), 20)
            self.assertEqual(len(p["sha256"]), 64)

    def test_absent_discipline_coverage_rule(self):
        # Document contains clear keywords from the quote
        doc = "Alan Turing worked at Bletchley Park during the Second World War."
        quote = "He worked at Bletchley Park breaking German ciphers."
        score = _compute_lexical_overlap(quote, doc)
        self.assertGreaterEqual(score, RELEVANCE_THRESHOLD)

        # Document on an entirely unrelated topic
        unrelated_doc = "Photosynthesis is the biological process used by plants to synthesize nutrients."
        score2 = _compute_lexical_overlap(quote, unrelated_doc)
        self.assertLess(score2, RELEVANCE_THRESHOLD)


if __name__ == "__main__":
    unittest.main()
