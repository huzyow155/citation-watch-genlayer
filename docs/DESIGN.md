# CitationWatch Architecture & Design Specification (v1.1.0)

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
   NO ──> Needs Model Layer   [Salient + Bigram Overlap Selection]
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

### Deterministic Path Audit Reporting (Defect 4 Fix)
When all tracked assertions are resolved deterministically as `SAME`:
- `coverage`: Recorded strictly as `"DETERMINISTIC_ONLY"`.
- `presented_passages`: Empty list `[]`.
- `presented_segment_ids`: Empty list `[]`.
- `presented_segments_count`: Exactly `0`.
- `budget_chars_used`: Exactly `0`.
- `source_chars_total`: Exact length of full cleaned text `len(clean_full)`.
- `source_chars_inspected`: Exact length of full cleaned text scanned `len(clean_full)`.
- `truncated_at`: `False`.

This ensures that deterministic audits do not falsely claim passage segmentation or budget consumption when no model segmentation took place.

### Model Layer
The model is invoked only for quotes that no longer appear verbatim. The model receives:
1. The unresolved tracked quotes.
2. The presented passages selected deterministically by relevance overlap within the 12,000-character budget.
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

## 4. Calibrated Absence Discipline & Reachability (Defect 3 Fix)
In v1.0.0, the absence test used unweighted bag-of-words overlap over 3,000-character windows with `RELEVANCE_THRESHOLD = 0.15`. Because any 3,000-character window in a long article shares common stopwords and topic words, genuine deletions routinely scored 0.18–0.28, making `REMOVED` practically unreachable (`FAIL|ABSENCE_UNSUPPORTED`).

In v1.1.0, the relevance metric was re-engineered and calibrated against real Wikipedia diffs:
1. **Salient Token Weighting (60%)**: Removes standard English stopwords and requires exact root token matches.
2. **Word Bigram Overlap (40%)**: Requires consecutive word pair matches to distinguish shared topical vocabulary from genuine paraphrases.
   $$\text{Score} = 0.6 \times \text{salient\_ratio} + 0.4 \times \text{bigram\_ratio}$$
3. **Calibrated Threshold**: Set to `RELEVANCE_THRESHOLD = 0.45`.

### Empirical Absence Calibration Table
Evaluated across real Wikipedia diffs and article pairs:

| Target Article & Scenario | Tracked Quote | v1.0.0 Score (Bag-of-Words) | v1.1.0 Score (Salient + Bigram) | Calibrated Threshold (0.45) Result |
| :--- | :--- | :--- | :--- | :--- |
| **Charles Babbage** (Deleted Death Detail, rev 1378652484) | `"Upon his death he halted his breathing and the beating of his heart."` | 0.22 (BLOCKED) | **0.20** | **ABSENT REACHABLE** (Max score 0.20 < 0.45) |
| **Alan Turing** (Turing Machine Intro, rev 1380390650) | `"Turing introduced an abstract machine that formalised the concept of algorithm."` | 0.52 | **0.68** | **CANDIDATE WINDOW FOUND** (Score 0.68 >= 0.45) |
| **Computing** (Tightened Narrow Sense, rev 1380219262) | `"Software is also sometimes used in a more narrow sense, meaning application software only."` | 0.61 | **0.74** | **CANDIDATE WINDOW FOUND** (Score 0.74 >= 0.45) |
| **Unrelated Context** (Sports sentence tested against Computing) | `"The team won the championship in overtime after scoring three goals."` | 0.08 | **0.00** | **ABSENT REACHABLE** (Score 0.00 < 0.45) |

## 5. Custom Leader/Validator Consensus Architecture (Defect 1 Fix)

### Root Cause of v1.0.0 LIVE Disagreement
In v1.0.0, `audit_citation` wrapped `"OK|<canonical>\n---\n<json audit_data>"` in `gl.eq_principle.strict_eq`. As documented in `genlayer/gl/eq_principle.py` (lines 19–39), `strict_eq` requires byte-for-byte identity of the entire returned string:
```python
# genlayer/gl/eq_principle.py (SDK pinned hash: py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6)
def strict_eq(fn: Callable[[], str]) -> str:
    def validator(leaders_res: vm.Result) -> bool:
        if not isinstance(leaders_res, vm.Return):
            return False
        return leaders_res.calldata == fn()
    return vm.run_nondet_unsafe(fn, validator)
```
Consequently:
1. `strict_eq` compared `target_text_sha256`, character counts, passages, passage IDs, and cited quotes across all validator nodes.
2. For LIVE pages, minor whitespace or millisecond ad/footer differences yielded different target fingerprints, causing validator disagreement (Tx `0xf318baa863cb01e8747ec8f493d75e874f0ae1537cd9c4e5521032122f06c010` failed with 2/5 agreement).
3. For model audits, passage IDs (`p1` vs `p2`) or quote whitespace differences forced disagreements.

### v1.1.0 Custom Consensus Architecture
In v1.1.0, `audit_citation` replaces `strict_eq` with a specialized pair passed to `gl.vm.run_nondet_unsafe(leader_audit_eval, validator_audit_eval)`:
1. **Canonical Enumeration Comparison**:
   The header contains only:
   `"<CLASS>|<FP_OR_NONE>|e1:<STATUS>|e2:<STATUS>..."`
   Where `FP_OR_NONE` is `target_text_sha256` for `REVISION` targets, but strictly `"NONE"` for `LIVE` targets.
2. **Exclusion of Non-Deterministic Noise for LIVE Targets**:
   Character counts, total characters, and live page fingerprints are excluded from cross-validator comparison.
3. **Validator Non-Deterministic Fetching via Sandbox**:
   In GenVM, non-deterministic operations (`gl.nondet.web.render`, `gl.nondet.web.get`) cannot be called directly inside the root `validator_audit_eval` function. They must be executed inside `gl.vm.spawn_sandbox(val_fetch_fn)`.
   - Verified via on-chain probe contract `Probe2` (`0x442863622d98F506c492C0484D187a9FeB487d77`, Tx `0x386ef2d03232473837ce36542801acfeab232d72cd94fda4516ca1f987db29ea`, `MAJORITY_AGREE`, 3/5 votes).
4. **Passage ID Independence & Substring Verification**:
   For model elements (`REPHRASED` / `CHANGED`):
   - The validator re-derives passages independently from its own fetched text.
   - The validator checks that the leader's `cited_quote` is a normalized substring of **any** passage re-derived by the validator.
   - Passage IDs (`p1`, `p2`) and character offsets are **not** compared for equality.
5. **Deterministic Agreement Binding**:
   For deterministic elements, the validator's `SAME` / not-`SAME` decision must strictly equal the leader's.

## 6. Storage Compaction & Non-Evictable Revision Checks (Defect 5 Fix)
In v1.0.0, repeat audit prevention checked only the in-memory array `audits` inside the citation JSON. If history compaction evicted audits beyond index 20, an old revision could be re-audited.

In v1.1.0, `SourceDriftLedger` introduces a persistent mapping:
```python
audited_revisions: TreeMap[str, str]  # Key: f"{citation_id}:{target_oldid}" -> now_str
```
- Every completed `REVISION` audit writes to `audited_revisions`.
- `audit_citation` checks `if audit_key in self.audited_revisions:` before executing.
- Even if the audit log inside the citation record is pruned or compacted, old revisions remain permanently non-re-auditable.

## 7. Storage Scalability: Unbounded JSON Removal (Defect 6 Fix)
In v1.0.0, `meta["ids"]` and `meta["registrations"]` stored JSON-serialized arrays and objects in a single storage slot. As citations scaled, parsing and re-serializing these JSON blobs would exceed GenVM gas and memory limits.

In v1.1.0:
- `meta["ids"]` is replaced with `citation_ids: TreeMap[str, str]` (0-indexed sequential access).
- `meta["registrations"]` is replaced with `registrations: TreeMap[str, str]` (registration fingerprint -> `citation_id`).
- `ClaimsBoard` replaced `meta["ids"]` with `claim_ids: TreeMap[str, str]`.
- All operations are now $O(1)$ in storage reads/writes.

## 8. Explicit Classification: On-Chain vs. Unit-Tested Only
In compliance with the Honesty Rules, behaviors are partitioned strictly by their verification venue:

### Verified On-Chain (GenLayer Studionet Preview)
1. **Deterministic Path Audit**: Verified on Alan Turing (Tx `0x34db8077b8b6995d44977c07849841c7d9f1a130ade597b6f7ca233a8cab6f72`, `ACCEPTED`, `MAJORITY_AGREE`, 3/5 votes).
2. **LIVE Article Consensus & Agreement**: Verified on Alan Turing live page (Tx `0x01a8d6faa62a4cad2266d3d1689d4c51771ebbdb90cfcb2ca3afb6e287569ab6`, `ACCEPTED`, `MAJORITY_AGREE`, 3/5 votes). Agreement improved from 2/5 to 3/5.
3. **COSMETIC Drift & Model Layer**: Verified on Computing (Tx `0xd90d91b9ce5b91061e0d0441b7bc25f1525bdba49600d8e11f8bc7f36d0bf18a`, `ACCEPTED`, `MAJORITY_AGREE`, 3/5 votes). Model classified `REPHRASED` on "narrower sense", cited passage `p15`, validator consensus verified.
4. **ClaimsBoard Integration**: Verified on Turing and Computing claims (Tx `0x8e88696d25c92faf0c85facd5a878f3eedf35a6c208c2194787b28244aa704e5` and `0xe77981973346ee2120efcaec8c7fbf537245770b6173eec4862e9c77042af353`, `ACCEPTED`, `MAJORITY_AGREE`, 3/5 votes).
5. **10 Negative Revert Scenarios**: All 10 negative tests reverted on-chain with exact expected payloads (`MAJORITY_AGREE`, 3/5 to 5/5 votes).


### Unit-Tested Only (Not On-Chain)
1. **MATERIAL Drift State Transition**: Tested and passed in 25 offline unit tests (`test_audit_citation_material_drift`). On-chain Attempt 1 reverted with `quote not found verbatim in baseline` due to MediaWiki table whitespace normalization differences between raw wikitext and rendered text.
2. **REMOVED Absence State Transition**: Tested and passed in 25 offline unit tests (`test_absence_calibration`, `test_audit_citation_removed_drift`). On-chain Attempts 1 & 2 on Charles Babbage reverted with `invalid model output` because the GenVM leader LLM policy (`prd-kimi`) output extra explanatory tokens/formatting for deleted assertions rather than bare JSON without explanation.
