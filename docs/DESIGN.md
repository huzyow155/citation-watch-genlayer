# CitationWatch Architecture & Design Specification

## Overview & Problem Statement
When a web resource is cited in a contract, academic paper, or public claim, the target page can be silently modified over time:
- Numbers change (economic statistics, dates, counts).
- Sentences are rewritten or reversed.
- Claims disappear entirely.
- The URL remains reachable (HTTP 200), masking the underlying factual drift.

Traditional cryptographic byte hashes fail because minor HTML template updates, stylesheet changes, or typo fixes invalidate the entire hash. CitationWatch introduces **semantic drift detection** with an immutable, independent baseline and deterministic-first evaluation.

## 1. Trust Model & Baseline Immutability
1. **Immutable Baseline**: A citation is anchored against a pinned Wikipedia revision permalink (`https://<lang>.wikipedia.org/w/index.php?title=<Title>&oldid=<OldId>`). Because Wikipedia revisions are immutable and publicly archived, the registrant cannot alter the baseline retrospectively.
2. **Verbatim Quote Grounding**: The registrant supplies 1 to 4 tracked assertions, each a verbatim quote copied from the baseline revision. At registration, the contract verifies deterministically that each quote exists verbatim in the normalized baseline text. No LLM or non-deterministic model is invoked at registration.
3. **Validator Consensus**: Validators independently fetch the revision permalink, reproduce the identical normalized baseline text, and verify the quote presence. The agreed value is the sha256 fingerprint of the normalized text.

## 2. Two-Layer Audit Mechanism: Deterministic-First
Audits evaluate a later state (a later pinned revision or the live page) against the baseline using a two-stage evaluation:

```
[Target Document] -> Clean HTML -> Normalize Text
                          │
         ┌────────────────┴────────────────┐
         ▼                                 ▼
[Deterministic Layer]             [Unresolved Quotes]
Is quote verbatim in target?              │
  YES ──> SAME                            ▼
   NO ──> Needs Model Layer   [Lexical Overlap Selection]
                                  Score windows against quotes
                                  Select top windows within 12,000 char budget
                                  Segment into passages [p1..pN]
                                          │
                                          ▼
                              [Strict Model Classifier]
                              Classifies element into:
                              - REPHRASED (verbatim cited quote from passage)
                              - CHANGED   (verbatim cited quote from passage)
                              - ABSENT    (no quote; checked by coverage scan)
```

### Deterministic Layer
If the normalized baseline quote appears verbatim in the normalized target text, the element status is immediately judged as `SAME` (`decided_by = "DETERMINISTIC"`). No AI model is called for this element.

### Model Layer
The model is invoked only for quotes that no longer appear verbatim. The model receives:
1. The unresolved tracked quotes.
2. The presented passages selected deterministically by lexical-overlap score within the 12,000-character budget.
3. Strict instructions requiring verbatim citation for `REPHRASED` or `CHANGED`.

## 3. Drift Class Matrix
The overall audit drift class is derived deterministically from the element statuses:

| Condition | Audit Class | Citation Status |
| :--- | :--- | :--- |
| Any element is `CHANGED` | `MATERIAL` | `DRIFTED` |
| Else any element is `ABSENT` | `REMOVED` | `REMOVED` |
| Else any element is `REPHRASED` | `COSMETIC` | `HEALTHY` |
| Else (all elements `SAME`) | `UNCHANGED` | `HEALTHY` |

This truth table is implemented as a pure function and verified across all 340 combinatorial permutations of 1..4 elements against an independent reference implementation in the test suite.

## 4. ABSENT Discipline & Coverage Invariance
Absence of evidence requires proof of coverage. A model classification of `ABSENT` is accepted only if:
1. The model provides `passage_id = null` and `cited_quote = null`.
2. A deterministic sliding-window scan across the **full normalized target text** finds no 3,000-character window whose lexical overlap score with the quote meets or exceeds `RELEVANCE_THRESHOLD` (0.15).

If a window reaches the threshold, the topic was present in the document; the model cannot claim absence without addressing that passage. The transaction reverts with `"coverage insufficient to conclude absence"`.

## 5. Presented-Segments Rule & Exact Budget Accounting
To guarantee reproducible audits:
- **Budget Accounting**: Inspected text is strictly capped at `INSPECTION_BUDGET_CHARS` (12,000 characters), exactly including the length of window separators (`\n[...]\n`, 7 characters).
- **Segment Fingerprinting**: Presented passages are numbered (`p1`..`pN`), sha256 fingerprinted, and recorded in the audit record.
- **Verbatim Passage Citations**: Every cited quote from the model must be a verbatim substring of the cited passage. Any fabricated or non-verbatim quote causes an immediate transaction revert.

## 6. Consensus Architecture & SDK Evidence
Based on source code analysis of `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` and empirical benchmarking on GenLayer Studionet (Preview):
- The consensus value agreed across validator nodes is a compact canonical string:
  `"{CLASS}|{target_text_sha256_or_NONE}|e1:{STATUS}:{PASSAGE_ID}|..."`
- Comparing this canonical string via `gl.eq_principle.strict_eq` ensures strict agreement on outcomes, element statuses, and evidence fingerprints.
- Free-form model commentary is excluded from the consensus string to prevent trivial phrasing disagreements among validator nodes.
- For `REVISION` targets, the sha256 fingerprint of the normalized text is included in consensus because revisions are immutable. For `LIVE` targets, the fingerprint is excluded from consensus (`fingerprint_in_consensus: false`) because live pages can differ across millisecond boundaries.

## 7. Known Limitations
1. **Negation in Adjacent Context**: If a tracked quote remains verbatim while a new sentence immediately preceding or following it negates it (e.g. "It was previously believed that [Quote]"), the deterministic layer will classify the element as `SAME`. Mitigating this requires evaluating surrounding context windows even for verbatim quotes in future upgrades.
2. **LIVE Audits Non-Reproducible**: Live web pages change continuously. As demonstrated by our on-chain test (`0xf318baa863cb01e8747ec8f493d75e874f0ae1537cd9c4e5521032122f06c010`), concurrent fetches by validator nodes on live pages can observe minor HTML variations, leading to consensus divergence. Pinned revision permalinks are strongly preferred for permanent on-chain evidence.
3. **Wikipedia Vandalism**: Edits that introduce vandalism or malicious number changes on Wikipedia will be detected as `MATERIAL` drift by the contract. The contract reports drift relative to the baseline revision, not truth relative to the external world.
4. **Model Judgment as a Heuristic**: Model classification of `REPHRASED` vs `CHANGED` is an informed semantic classification, not a formal mathematical derivation.
5. **Host Scope**: Version 1.0 supports language hosts of `wikipedia.org` where revision permalinks provide immutable baselines.

## 8. Unit-Tested Only (Not On-Chain) List
The following edge cases and boundary conditions are exhaustively verified in the pure and mocked test suites (`tests/test_layer1_pure.py`, `tests/test_layer2_mocked.py`, `tests/test_layer3_consensus.py`), but were not executed as live Studionet transactions to minimize unnecessary RPC churn:
1. Combinatorial 340-permutation status mapping matrix.
2. Full sliding window overlap calculations with fractional character boundaries.
3. Multiple successive live cooldown expirations across large timestamps.
4. Passage truncation handling beyond 240 characters.
5. Exact budget boundary capping at exactly 12,000 characters with multiple multi-window overlaps.
