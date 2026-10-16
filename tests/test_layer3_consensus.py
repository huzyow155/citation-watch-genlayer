import unittest
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import genlayer
gl = genlayer.gl

from contracts.SourceDriftLedger import SourceDriftLedger


class TestLayer3Consensus(unittest.TestCase):

    def setUp(self):
        self.ledger = SourceDriftLedger()
        self.ledger.citations = {}
        self.ledger.meta = {}
        self.ledger.citation_ids = {}
        self.ledger.registrations = {}
        self.ledger.audited_revisions = {}

        gl.nondet.web.pages = {}
        gl.nondet.prompt_handler = None

        gl.message.sender_address.as_hex = "0x1111111111111111111111111111111111111111"
        gl.message_raw = {"datetime": "2026-10-16T12:00:00Z"}

        self.base_url = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1000"
        self.base_text = "Alan Mathison Turing was an English mathematician and pioneer of theoretical computing."
        gl.nondet.web.pages[self.base_url] = self.base_text

    def test_fabricated_quote_rejection(self):
        """Mock attempts to fabricate a quote not present in the presented passage -> must revert."""
        quote = "Alan Mathison Turing was an English mathematician and pioneer of theoretical computing."
        self.ledger.register_citation("Turing Bio", self.base_url, json.dumps([quote]))
        cid = json.loads(self.ledger.list_citation_ids(0, 10))[0]

        target_url = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1100"
        target_text = "Alan Turing was an English mathematician who pioneered computation."
        gl.nondet.web.pages[target_url] = target_text

        # Mock model fabricates a cited quote that is NOT in the presented passage
        gl.nondet.prompt_handler = lambda p, fmt: json.dumps({
            "elements": [{
                "id": "e1",
                "status": "REPHRASED",
                "passage_id": "p1",
                "cited_quote": "Completely invented sentence that never existed in the text."
            }]
        })

        with self.assertRaises(gl.vm.UserError) as cm:
            self.ledger.audit_citation(cid, target_url)
        self.assertIn("cited quote not found verbatim in presented passage", str(cm.exception))

    def test_validator_seeing_different_page_or_disagreement(self):
        """Simulate leader and validator disagreement via run_nondet_unsafe."""
        quote = "Alan Mathison Turing was an English mathematician and pioneer of theoretical computing."
        self.ledger.register_citation("Turing Bio", self.base_url, json.dumps([quote]))
        cid = json.loads(self.ledger.list_citation_ids(0, 10))[0]

        target_url = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1100"
        gl.nondet.web.pages[target_url] = "Alan Turing was an English mathematician who pioneered computation."

        orig_run_nondet_unsafe = gl.vm.run_nondet_unsafe
        try:
            # Force disagreement
            def mock_disagree(leader_fn, val_fn):
                res = leader_fn()
                wrapped = gl.vm.Return(calldata=res)
                # Validator votes False
                if not val_fn(wrapped):
                    raise gl.vm.VMError("validator disagreed")
                raise gl.vm.VMError("forced disagreement")

            gl.vm.run_nondet_unsafe = mock_disagree
            with self.assertRaises(gl.vm.VMError):
                self.ledger.audit_citation(cid, target_url)
        finally:
            gl.vm.run_nondet_unsafe = orig_run_nondet_unsafe

    def test_defect1_regression_quote_whitespace_agreement(self):
        """
        Regression test for Defect 1:
        Leader and validator agree on enumerations even when leader's cited_quote has extra whitespace.
        On HEAD 845d209, strict_eq failed because the entire JSON string was compared.
        """
        quote = "Alan Mathison Turing was an English mathematician and pioneer of theoretical computing."
        self.ledger.register_citation("Turing Bio", self.base_url, json.dumps([quote]))
        cid = json.loads(self.ledger.list_citation_ids(0, 10))[0]

        target_url = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1100"
        target_text = "Alan Turing was an English mathematician who pioneered computation."
        gl.nondet.web.pages[target_url] = target_text

        # Model returns quote with uneven/extra whitespace
        gl.nondet.prompt_handler = lambda p, fmt: json.dumps({
            "elements": [{
                "id": "e1",
                "status": "REPHRASED",
                "passage_id": "p1",
                "cited_quote": "  Alan   Turing was an English   mathematician who pioneered computation.  "
            }]
        })

        # Must succeed and agree because validator normalizes whitespace
        self.ledger.audit_citation(cid, target_url)
        rec = json.loads(self.ledger.get_citation(cid))
        self.assertEqual(rec["audits_total"], 1)
        self.assertEqual(rec["audits"][0]["class"], "COSMETIC")

    def test_defect1_regression_live_page_noise_agreement(self):
        """
        Regression test for Defect 1:
        Validators fetching LIVE page with different noise agree on class because fingerprint
        is excluded from consensus for LIVE targets.
        """
        quote = "Alan Mathison Turing was an English mathematician and pioneer of theoretical computing."
        self.ledger.register_citation("Turing Bio", self.base_url, json.dumps([quote]))
        cid = json.loads(self.ledger.list_citation_ids(0, 10))[0]

        live_url = "https://en.wikipedia.org/wiki/Alan_Turing"
        leader_page = "Alan Turing was an English mathematician who pioneered computation. <!-- Leader Timestamp 12:00:00.001 -->"
        validator_page = "Alan Turing was an English mathematician who pioneered computation. <!-- Validator Timestamp 12:00:00.005 -->"

        gl.nondet.prompt_handler = lambda p, fmt: json.dumps({
            "elements": [{
                "id": "e1",
                "status": "REPHRASED",
                "passage_id": "p1",
                "cited_quote": "Alan Turing was an English mathematician who pioneered computation."
            }]
        })

        orig_run_nondet = gl.vm.run_nondet_unsafe
        try:
            def simulate_differing_live_fetch(leader_fn, val_fn):
                # Leader fetches leader_page
                gl.nondet.web.pages[live_url] = leader_page
                leader_res = leader_fn()
                # Validator fetches validator_page
                gl.nondet.web.pages[live_url] = validator_page
                wrapped = gl.vm.Return(calldata=leader_res)
                valid = val_fn(wrapped)
                if not valid:
                    raise gl.vm.VMError("validator disagreed on live noise")
                return leader_res

            gl.vm.run_nondet_unsafe = simulate_differing_live_fetch
            self.ledger.audit_citation(cid, live_url)
            rec = json.loads(self.ledger.get_citation(cid))
            self.assertEqual(rec["audits_total"], 1)
            self.assertEqual(rec["audits"][0]["class"], "COSMETIC")
            self.assertFalse(rec["audits"][0]["fingerprint_in_consensus"])
        finally:
            gl.vm.run_nondet_unsafe = orig_run_nondet

    def test_defect1_regression_validator_disagrees_on_missing_quote(self):
        """
        Regression test for Defect 1:
        Validator whose own re-derived passages do not contain leader's cited quote MUST disagree.
        """
        quote = "Alan Mathison Turing was an English mathematician and pioneer of theoretical computing."
        self.ledger.register_citation("Turing Bio", self.base_url, json.dumps([quote]))
        cid = json.loads(self.ledger.list_citation_ids(0, 10))[0]

        target_url = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1100"
        gl.nondet.web.pages[target_url] = "Alan Turing was an English mathematician who pioneered computation."

        gl.nondet.prompt_handler = lambda p, fmt: json.dumps({
            "elements": [{
                "id": "e1",
                "status": "REPHRASED",
                "passage_id": "p1",
                "cited_quote": "Alan Turing was an English mathematician who pioneered computation."
            }]
        })

        orig_run_nondet = gl.vm.run_nondet_unsafe
        try:
            def simulate_missing_quote_on_validator(leader_fn, val_fn):
                leader_res = leader_fn()
                # Validator sees text that does NOT have the cited sentence
                gl.nondet.web.pages[target_url] = "Entirely unrelated article text about marine biology in the Pacific."
                wrapped = gl.vm.Return(calldata=leader_res)
                valid = val_fn(wrapped)
                if not valid:
                    raise gl.vm.UserError("audit evaluation failed")
                return leader_res

            gl.vm.run_nondet_unsafe = simulate_missing_quote_on_validator
            with self.assertRaises(gl.vm.UserError) as cm:
                self.ledger.audit_citation(cid, target_url)
            self.assertIn("audit evaluation failed", str(cm.exception))
        finally:
            gl.vm.run_nondet_unsafe = orig_run_nondet

    def test_defect1_regression_revision_fingerprint_mismatch_disagrees(self):
        """
        Regression test for Defect 1:
        For REVISION targets, if validator's fingerprint differs from leader's, validator MUST disagree.
        """
        quote = "Alan Mathison Turing was an English mathematician and pioneer of theoretical computing."
        self.ledger.register_citation("Turing Bio", self.base_url, json.dumps([quote]))
        cid = json.loads(self.ledger.list_citation_ids(0, 10))[0]

        target_url = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1100"
        gl.nondet.web.pages[target_url] = self.base_text

        orig_run_nondet = gl.vm.run_nondet_unsafe
        try:
            def simulate_revision_tamper(leader_fn, val_fn):
                leader_res = leader_fn()
                # Validator sees slightly different text for an immutable revision
                gl.nondet.web.pages[target_url] = self.base_text + " Extra byte."
                wrapped = gl.vm.Return(calldata=leader_res)
                valid = val_fn(wrapped)
                if not valid:
                    raise gl.vm.UserError("audit evaluation failed")
                return leader_res

            gl.vm.run_nondet_unsafe = simulate_revision_tamper
            with self.assertRaises(gl.vm.UserError) as cm:
                self.ledger.audit_citation(cid, target_url)
            self.assertIn("audit evaluation failed", str(cm.exception))
        finally:
            gl.vm.run_nondet_unsafe = orig_run_nondet

    def test_defect4_deterministic_path_reporting(self):
        """
        Regression test for Defect 4:
        Deterministic SAME layer must report coverage='DETERMINISTIC_ONLY' and budget_chars_used=0.
        """
        quote = "Alan Mathison Turing was an English mathematician and pioneer of theoretical computing."
        self.ledger.register_citation("Turing Bio", self.base_url, json.dumps([quote]))
        cid = json.loads(self.ledger.list_citation_ids(0, 10))[0]

        rev_url = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1100"
        gl.nondet.web.pages[rev_url] = self.base_text

        self.ledger.audit_citation(cid, rev_url)
        rec = json.loads(self.ledger.get_citation(cid))
        audit = rec["audits"][0]

        self.assertEqual(audit["coverage"], "DETERMINISTIC_ONLY")
        self.assertEqual(audit["budget_chars_used"], 0)
        self.assertEqual(audit["presented_segments_count"], 0)
        self.assertEqual(audit["presented_segment_ids"], [])
        self.assertEqual(audit["source_chars_total"], len(self.base_text))
        self.assertEqual(audit["source_chars_inspected"], len(self.base_text))
        self.assertFalse(audit["truncated_at"])

    def test_defect5_audited_revisions_protection_survives_compaction(self):
        """
        Regression test for Defect 5:
        Verify audited_revisions TreeMap prevents re-auditing earlier revisions even after
        history compaction (> 20 audits).
        """
        quote = "Alan Mathison Turing was an English mathematician and pioneer of theoretical computing."
        self.ledger.register_citation("Turing Bio", self.base_url, json.dumps([quote]))
        cid = json.loads(self.ledger.list_citation_ids(0, 10))[0]

        # Audit 22 revisions (oldid=1001 to 1022)
        for i in range(1, 23):
            oldid = 1000 + i
            url = f"https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid={oldid}"
            gl.nondet.web.pages[url] = self.base_text
            self.ledger.audit_citation(cid, url)

        rec = json.loads(self.ledger.get_citation(cid))
        self.assertEqual(rec["audits_total"], 22)
        # Stored audit summaries in JSON are capped at MAX_AUDIT_SUMMARIES (20)
        self.assertEqual(len(rec["audits"]), 20)

        # The oldest audit (oldid=1001) has been pruned from rec["audits"]
        stored_oldids = [a.get("target_oldid") for a in rec["audits"]]
        self.assertNotIn("1001", stored_oldids)

        # Attempting to re-audit oldid=1001 MUST revert via self.audited_revisions
        url_1001 = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1001"
        with self.assertRaises(gl.vm.UserError) as cm:
            self.ledger.audit_citation(cid, url_1001)
        self.assertIn("target already audited", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
