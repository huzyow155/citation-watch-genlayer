import unittest
import json
import os
import sys
import copy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import genlayer
gl = genlayer.gl

from contracts.SourceDriftLedger import SourceDriftLedger
from contracts.ClaimsBoard import ClaimsBoard


class TestLayer2Mocked(unittest.TestCase):

    def setUp(self):
        self.ledger = SourceDriftLedger()
        self.ledger.citations = {}
        self.ledger.meta = {}

        self.board = ClaimsBoard()
        self.board.claims = {}
        self.board.meta = {}
        self.board.owner = "0x1111111111111111111111111111111111111111"
        self.board.ledger_address = ""

        gl.nondet.web.pages = {}
        gl.nondet.prompt_handler = None
        gl.contracts_registry["0x2222222222222222222222222222222222222222"] = self.ledger

        # Set up standard message
        gl.message.sender_address.as_hex = "0x1111111111111111111111111111111111111111"
        gl.message_raw = {"datetime": "2026-10-16T12:00:00Z"}

        # Base wiki pages
        self.base_text = (
            "Alan Mathison Turing was an English mathematician, computer scientist, logician, "
            "cryptanalyst, philosopher and theoretical biologist. He was highly influential in the development "
            "of theoretical computer science, providing a formalisation of the concepts of algorithm and computation "
            "with the Turing machine."
        )
        self.base_url = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1000"
        gl.nondet.web.pages[self.base_url] = self.base_text

    def test_registration_atomicity_after_rejections(self):
        """Verify storage snapshot equality after EVERY rejection path in register_citation."""
        initial_citations = copy.deepcopy(self.ledger.citations)
        initial_meta = copy.deepcopy(self.ledger.meta)

        rejection_cases = [
            # 1. Invalid label
            (1234, self.base_url, json.dumps(["Alan Mathison Turing was an English mathematician"])),
            # 2. Overlong label
            ("A" * 121, self.base_url, json.dumps(["Alan Mathison Turing was an English mathematician"])),
            # 3. Non-permalink baseline
            ("Valid label", "https://en.wikipedia.org/wiki/Alan_Turing", json.dumps(["Alan Mathison Turing was an English mathematician"])),
            # 4. Invalid JSON
            ("Valid label", self.base_url, "not-json"),
            # 5. Empty quotes list
            ("Valid label", self.base_url, json.dumps([])),
            # 6. More than MAX_ELEMENTS (4)
            ("Valid label", self.base_url, json.dumps(["Quote 1 is long enough to meet thirty chars", "Quote 2 is long enough to meet thirty chars", "Quote 3 is long enough to meet thirty chars", "Quote 4 is long enough to meet thirty chars", "Quote 5 is long enough to meet thirty chars"])),
            # 7. Quote too short (< 30)
            ("Valid label", self.base_url, json.dumps(["Too short"])),
            # 8. Quote not found in baseline
            ("Valid label", self.base_url, json.dumps(["Albert Einstein formulated the theory of general relativity."])),
            # 9. Duplicate quotes in list
            ("Valid label", self.base_url, json.dumps(["Alan Mathison Turing was an English mathematician", "Alan Mathison Turing was an English mathematician"])),
            # 10. Source unavailable
            ("Valid label", "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=9999", json.dumps(["Alan Mathison Turing was an English mathematician"])),
        ]

        for idx, (label, url, quotes) in enumerate(rejection_cases):
            with self.assertRaises(gl.vm.UserError, msg=f"Rejection case {idx} did not revert"):
                self.ledger.register_citation(label, url, quotes)

            self.assertEqual(
                self.ledger.citations, initial_citations,
                f"Citations storage modified during rejection case {idx}"
            )
            self.assertEqual(
                self.ledger.meta, initial_meta,
                f"Meta storage modified during rejection case {idx}"
            )

    def test_duplicate_registration_rejection(self):
        quote = "Alan Mathison Turing was an English mathematician"
        quotes_json = json.dumps([quote])

        # First registration succeeds
        self.ledger.register_citation("Turing Bio", self.base_url, quotes_json)
        self.assertEqual(len(self.ledger.citations), 1)

        # Duplicate registration with same baseline oldid and quote must revert
        with self.assertRaises(gl.vm.UserError) as cm:
            self.ledger.register_citation("Another Label", self.base_url, quotes_json)
        self.assertIn("already registered", str(cm.exception))

    def test_audit_pointer_and_status_correctness_across_repeated_audits(self):
        """Regression test ensuring latest_audit_index and status correctly track repeated audits."""
        quote = "Alan Mathison Turing was an English mathematician"
        self.ledger.register_citation("Turing Bio", self.base_url, json.dumps([quote]))
        cid = json.loads(self.ledger.meta["ids"])[0]

        # Initially UNAUDITED
        status_str = self.ledger.get_status(cid)
        self.assertTrue(status_str.startswith("UNAUDITED|NONE|0|"))

        # Audit 1: REVISION target with verbatim quote -> UNCHANGED -> HEALTHY
        rev1_url = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1100"
        gl.nondet.web.pages[rev1_url] = self.base_text
        self.ledger.audit_citation(cid, rev1_url)

        rec = json.loads(self.ledger.get_citation(cid))
        self.assertEqual(rec["audits_total"], 1)
        self.assertEqual(rec["latest_audit_index"], 0)
        self.assertEqual(rec["status"], "HEALTHY")
        self.assertEqual(self.ledger.get_status(cid).split("|")[0], "HEALTHY")
        self.assertEqual(self.ledger.get_status(cid).split("|")[1], "UNCHANGED")

        # Audit 2: Model classifies as REPHRASED -> COSMETIC -> HEALTHY
        rev2_url = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1200"
        rephrased_text = (
            "Alan Turing was a British mathematician who pioneered theoretical computer science."
        )
        gl.nondet.web.pages[rev2_url] = rephrased_text
        gl.nondet.prompt_handler = lambda p, fmt: json.dumps({
            "elements": [{
                "id": "e1",
                "status": "REPHRASED",
                "passage_id": "p1",
                "cited_quote": "Alan Turing was a British mathematician who pioneered theoretical computer science."
            }]
        })

        self.ledger.audit_citation(cid, rev2_url)
        rec = json.loads(self.ledger.get_citation(cid))
        self.assertEqual(rec["audits_total"], 2)
        self.assertEqual(rec["latest_audit_index"], 1)
        self.assertEqual(rec["status"], "HEALTHY")
        self.assertEqual(self.ledger.get_status(cid).split("|")[0], "HEALTHY")
        self.assertEqual(self.ledger.get_status(cid).split("|")[1], "COSMETIC")

        # Audit 3: Model classifies as CHANGED -> MATERIAL -> DRIFTED
        rev3_url = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1300"
        changed_text = (
            "Alan Turing was an American chemist and biologist who studied molecular genetics."
        )
        gl.nondet.web.pages[rev3_url] = changed_text
        gl.nondet.prompt_handler = lambda p, fmt: json.dumps({
            "elements": [{
                "id": "e1",
                "status": "CHANGED",
                "passage_id": "p1",
                "cited_quote": "Alan Turing was an American chemist and biologist who studied molecular genetics."
            }]
        })

        self.ledger.audit_citation(cid, rev3_url)
        rec = json.loads(self.ledger.get_citation(cid))
        self.assertEqual(rec["audits_total"], 3)
        self.assertEqual(rec["latest_audit_index"], 2)
        self.assertEqual(rec["status"], "DRIFTED")
        self.assertEqual(self.ledger.get_status(cid).split("|")[0], "DRIFTED")
        self.assertEqual(self.ledger.get_status(cid).split("|")[1], "MATERIAL")

    def test_live_audit_cooldown(self):
        quote = "Alan Mathison Turing was an English mathematician"
        self.ledger.register_citation("Turing Bio", self.base_url, json.dumps([quote]))
        cid = json.loads(self.ledger.meta["ids"])[0]

        live_url = "https://en.wikipedia.org/wiki/Alan_Turing"
        gl.nondet.web.pages[live_url] = self.base_text

        # First live audit at 12:00:00Z succeeds
        gl.message_raw["datetime"] = "2026-10-16T12:00:00Z"
        self.ledger.audit_citation(cid, live_url)

        # Immediate second live audit at 12:01:00Z (60s later < 300s) must revert
        gl.message_raw["datetime"] = "2026-10-16T12:01:00Z"
        with self.assertRaises(gl.vm.UserError) as cm:
            self.ledger.audit_citation(cid, live_url)
        self.assertIn("live audit cooldown active", str(cm.exception))

        # Third live audit at 12:06:00Z (360s later >= 300s) succeeds
        gl.message_raw["datetime"] = "2026-10-16T12:06:00Z"
        self.ledger.audit_citation(cid, live_url)

        rec = json.loads(self.ledger.get_citation(cid))
        self.assertEqual(rec["audits_total"], 2)

    def test_already_audited_target_revision(self):
        quote = "Alan Mathison Turing was an English mathematician"
        self.ledger.register_citation("Turing Bio", self.base_url, json.dumps([quote]))
        cid = json.loads(self.ledger.meta["ids"])[0]

        rev_url = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1100"
        gl.nondet.web.pages[rev_url] = self.base_text

        self.ledger.audit_citation(cid, rev_url)

        with self.assertRaises(gl.vm.UserError) as cm:
            self.ledger.audit_citation(cid, rev_url)
        self.assertIn("target already audited", str(cm.exception))

    def test_source_unavailable_never_recorded_as_drift(self):
        quote = "Alan Mathison Turing was an English mathematician"
        self.ledger.register_citation("Turing Bio", self.base_url, json.dumps([quote]))
        cid = json.loads(self.ledger.meta["ids"])[0]

        rev_missing = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1100"
        # Not adding rev_missing to gl.nondet.web.pages -> returns 404/empty

        with self.assertRaises(gl.vm.UserError) as cm:
            self.ledger.audit_citation(cid, rev_missing)
        self.assertIn("source unavailable", str(cm.exception))

        # Verify no audit was written and status is still UNAUDITED
        rec = json.loads(self.ledger.get_citation(cid))
        self.assertEqual(rec["audits_total"], 0)
        self.assertEqual(rec["status"], "UNAUDITED")

    def test_consumer_badge_transitions_and_history(self):
        quote = "Alan Mathison Turing was an English mathematician"
        self.ledger.register_citation("Turing Bio", self.base_url, json.dumps([quote]))
        cid = json.loads(self.ledger.meta["ids"])[0]

        self.board.set_ledger("0x2222222222222222222222222222222222222222")
        self.assertEqual(self.board.get_ledger_address(), "0x2222222222222222222222222222222222222222")

        # 1. Publish claim when ledger citation is UNAUDITED
        self.board.publish_claim(cid, "Alan Turing was verified English mathematician")
        claim_id = json.loads(self.board.meta["ids"])[0]

        claim = json.loads(self.board.get_claim(claim_id))
        self.assertEqual(claim["badge"], "UNAUDITED")
        self.assertEqual(claim["badge_history"], ["UNAUDITED"])

        # Refresh while still UNAUDITED -> no duplicate entry in badge_history
        self.board.refresh_claim(claim_id)
        claim = json.loads(self.board.get_claim(claim_id))
        self.assertEqual(claim["badge_history"], ["UNAUDITED"])

        # 2. Audit ledger as UNCHANGED -> VERIFIED badge
        rev1_url = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1100"
        gl.nondet.web.pages[rev1_url] = self.base_text
        self.ledger.audit_citation(cid, rev1_url)

        self.board.refresh_claim(claim_id)
        claim = json.loads(self.board.get_claim(claim_id))
        self.assertEqual(claim["badge"], "VERIFIED")
        self.assertEqual(claim["badge_history"], ["UNAUDITED", "VERIFIED"])

        # Refresh again without status change -> no duplicate
        self.board.refresh_claim(claim_id)
        claim = json.loads(self.board.get_claim(claim_id))
        self.assertEqual(claim["badge_history"], ["UNAUDITED", "VERIFIED"])

        # 3. Audit ledger with MATERIAL drift -> DRIFTED badge
        rev2_url = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1200"
        changed_text = "Alan Turing was an American chemist."
        gl.nondet.web.pages[rev2_url] = changed_text
        gl.nondet.prompt_handler = lambda p, fmt: json.dumps({
            "elements": [{
                "id": "e1",
                "status": "CHANGED",
                "passage_id": "p1",
                "cited_quote": "Alan Turing was an American chemist."
            }]
        })
        self.ledger.audit_citation(cid, rev2_url)

        self.board.refresh_claim(claim_id)
        claim = json.loads(self.board.get_claim(claim_id))
        self.assertEqual(claim["badge"], "DRIFTED")
        self.assertEqual(claim["badge_history"], ["UNAUDITED", "VERIFIED", "DRIFTED"])


if __name__ == "__main__":
    unittest.main()
