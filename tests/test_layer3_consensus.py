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
        cid = json.loads(self.ledger.meta["ids"])[0]

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
        """Simulate leader and validator seeing different page content or disagreeing."""
        quote = "Alan Mathison Turing was an English mathematician and pioneer of theoretical computing."
        self.ledger.register_citation("Turing Bio", self.base_url, json.dumps([quote]))
        cid = json.loads(self.ledger.meta["ids"])[0]

        target_url = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1100"
        gl.nondet.web.pages[target_url] = "Alan Turing was an English mathematician who pioneered computation."

        # Simulate consensus principle returning failure / disagreement
        orig_strict_eq = gl.eq_principle.strict_eq
        try:
            gl.eq_principle.strict_eq = lambda fn: "DISAGREED"
            with self.assertRaises(gl.vm.UserError) as cm:
                self.ledger.audit_citation(cid, target_url)
            self.assertIn("audit evaluation failed", str(cm.exception))
        finally:
            gl.eq_principle.strict_eq = orig_strict_eq

    def test_long_page_dynamic_passage_id(self):
        """
        Long page test where the relevant passage sits far beyond the first segments
        and the mock cites the REAL dynamic ID of that passage.
        """
        quote = "Alan Turing solved the Enigma cipher problem during the conflict."
        baseline_page = (
            "Background intro text. " * 30 +
            quote + " " +
            "More trailing text. " * 30
        )
        gl.nondet.web.pages[self.base_url] = baseline_page
        self.ledger.register_citation("Enigma Quote", self.base_url, json.dumps([quote]))
        cid = json.loads(self.ledger.meta["ids"])[0]

        # Target has 100,000 characters of distractor text at the start
        distractor = "Unrelated historical details about agriculture in the 19th century. " * 800
        rephrased_sentence = "During the conflict Alan Turing cracked the Enigma cipher system."
        trailing = "Further unrelated details about astronomy. " * 800
        target_text = distractor + "\n\n" + rephrased_sentence + "\n\n" + trailing
        self.assertGreater(len(target_text), 80000)

        target_url = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=2000"
        gl.nondet.web.pages[target_url] = target_text

        # Handler dynamically finds which presented passage contains the rephrased sentence
        def dynamic_mock_handler(prompt_str, fmt):
            # Parse presented passages from the prompt text
            # Format in prompt: [pX] text
            lines = prompt_str.split("\n")
            target_pid = None
            for line in lines:
                if rephrased_sentence in line and line.strip().startswith("[p"):
                    target_pid = line.strip().split("]")[0][1:]
                    break

            if not target_pid:
                # If window selection failed to bring the sentence into presented passages
                return json.dumps({"elements": []})

            return json.dumps({
                "elements": [{
                    "id": "e1",
                    "status": "REPHRASED",
                    "passage_id": target_pid,
                    "cited_quote": rephrased_sentence,
                }]
            })

        gl.nondet.prompt_handler = dynamic_mock_handler
        self.ledger.audit_citation(cid, target_url)

        rec = json.loads(self.ledger.get_citation(cid))
        self.assertEqual(rec["audits_total"], 1)
        audit = rec["audits"][0]
        self.assertEqual(audit["class"], "COSMETIC")
        self.assertEqual(audit["coverage"], "SELECTED_WINDOWS")
        self.assertEqual(audit["elements"][0]["status"], "REPHRASED")
        # Dynamic passage ID should NOT be a hardcoded guess; it must match what was actually cited
        real_cited_pid = audit["elements"][0]["passage_id"]
        self.assertTrue(real_cited_pid.startswith("p"))
        # Verify the cited passage indeed contains the rephrased quote
        cited_passage = [p for p in audit["passages"] if p["id"] == real_cited_pid][0]
        self.assertIn(rephrased_sentence, cited_passage["text"])


if __name__ == "__main__":
    unittest.main()
