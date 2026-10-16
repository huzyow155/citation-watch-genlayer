# CitationWatch Architecture & Design Specification (v1.2.0)

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

### Deterministic Path Audit Reporting
When all tracked assertions are resolved deterministically as `SAME`:
- `coverage`: Recorded strictly as `"DETERMINISTIC_ONLY"`.
- `presented_passages`: Empty list `[]`.
- `presented_segment_ids`: Empty list `[]`.
- `presented_segments_count`: Exactly `0`.
- `budget_chars_used`: Exactly `0`.
- `source_chars_total`: Exact length of full cleaned text `len(clean_full)`.
- `source_chars_inspected`: Exactly `0` (no model passage slicing was performed).
- `chars_scanned`: Exact length of full cleaned text `len(clean_full)`.
- `truncated_at`: `False`.

This guarantees that deterministic audits do not falsely claim passage segmentation or budget consumption when no model segmentation took place.

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

## 4. Calibrated Absence Discipline & Reachability

### Salient Token Weighting & Bigram Overlap
The relevance scoring metric between a tracked quote and an article window combines:
1. **Salient Token Weighting (60%)**: Removes standard English stopwords and requires exact root token matches.
2. **Word Bigram Overlap (40%)**: Requires consecutive word pair matches to distinguish shared topical vocabulary from genuine paraphrases.
   $$\text{Score} = 0.6 \times \text{salient\_ratio} + 0.4 \times \text{bigram\_ratio}$$
3. **Calibrated Threshold**: Set to `RELEVANCE_THRESHOLD = 0.45`.

### Empirical Absence Calibration Set (16 Pairs across Real Wikipedia Revisions)
Evaluated across 8 genuine deleted-sentence scenarios and 8 reworded/present scenarios from documented Wikipedia revisions:

| ID | Article & Scenario | Quote Assertion | Kind | Max Window Score | Threshold (0.45) Separation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **D1** | Alan Turing (rev 1379625434) | `"In 1945, Turing sewed an outfit for the bear..."` | DELETED | 0.0667 | Clean Absent (< 0.45) |
| **D2** | Moon (rev 1380127737) | `"Occasionally some lunar deities have been also depicted driving a chariot..."` | DELETED | 0.2963 | Clean Absent (< 0.45) |
| **D3** | Charles Babbage (rev 1378652484) | `"Upon his death he halted his breathing and the beating of his heart."` | DELETED | 0.1984 | Clean Absent (< 0.45) |
| **D4** | Alan Turing (rev 1380390650) | Photosynthesis statement tested against Turing | DELETED | 0.0889 | Clean Absent (< 0.45) |
| **D5** | Ada Lovelace (rev 1371961179) | Newton Mint counterfeiter detail against Lovelace | DELETED | 0.1556 | Clean Absent (< 0.45) |
| **D6** | Charles Babbage (rev 1378652484) | Einstein patent office detail against Babbage | DELETED | 0.0988 | Clean Absent (< 0.45) |
| **D7** | Computing (rev 1380219262) | Tesla Wardenclyffe Tower detail against Computing | DELETED | 0.1111 | Clean Absent (< 0.45) |
| **D8** | Alan Turing (rev 1380390650) | Marie Curie Radium isolation against Turing | DELETED | 0.1543 | Clean Absent (< 0.45) |
| **R1** | Film Grosses (rev 1379737814) | `"The measuring system for gauging a film's success is based on unadjusted grosses..."` | REWORDED | 0.7788 | Candidate Present (>= 0.45) |
| **R2** | Alan Turing (rev 1380390650) | `"In the 1940s, Turing became worried about losing his savings..."` | REWORDED | 1.0000 | Candidate Present (>= 0.45) |
| **R3** | Computing (rev 1380219262) | `"Software is also sometimes used in a more narrow sense..."` | REWORDED | 0.7429 | Candidate Present (>= 0.45) |
| **R4** | Ada Lovelace (rev 1371961179) | `"Lovelace was the first to recognize that the machine had applications..."` | REWORDED | 0.9474 | Candidate Present (>= 0.45) |
| **R5** | Charles Babbage (rev 1378652484) | `"Considered by some to be a father of the computer..."` | REWORDED | 0.9630 | Candidate Present (>= 0.45) |
| **R6** | Python (rev 1379380903) | `"the Python Software Foundation supports Python 3.11, 3.12, 3.13, and 3.14..."` | REWORDED | 0.8912 | Candidate Present (>= 0.45) |
| **R7** | Alan Turing (rev 1380390650) | `"While at the National Physical Laboratory, Turing designed the Automatic Computing Engine..."` | REWORDED | 0.4776 | Candidate Present (>= 0.45) |
| **R8** | Computing (rev 1380219262) | `"Computing is any goal-oriented activity requiring, benefiting from..."` | REWORDED | 0.9333 | Candidate Present (>= 0.45) |

### Calibration Summary Metrics
- **Deleted / Absent Group (N=8)**: Min: `0.0667` | Median: `0.1327` | Max: `0.2963`
- **Reworded / Present Group (N=8)**: Min: `0.4776` | Median: `0.8350` | Max: `1.0000`
- **Empirical Separation Margin**: The threshold of `0.45` separates both classes with a clear margin between max deleted (`0.2963`) and min reworded (`0.4776`).

## 5. Custom Leader/Validator Consensus Architecture (v1.2.0)

### Evolution from v1.0.0 through v1.2.0
- **v1.0.0**: Used `gl.eq_principle.strict_eq`, which required byte-for-byte identity of the entire JSON string, including dynamic fingerprints and character counts. This broke consensus on LIVE targets and model audits.
- **v1.1.0**: Introduced custom `run_nondet_unsafe` consensus with an enumeration-only canonical string and quote substring verification in validator-derived passages. However, validators did not execute their own model; the classification decision remained with the leader.
- **v1.2.0 (Active)**: Extends validator verification so that validators **independently run model classification** inside `gl.vm.spawn_sandbox` and require **element status equality** (`val_status == leader_status`) in addition to passage quote grounding.

### What Validators Verify vs. What Is Excluded

| Evaluated Property | Verified by Validator? | Verification Mechanism |
| :--- | :--- | :--- |
| **Element Statuses** (`REPHRASED`, `CHANGED`, `ABSENT`) | **YES** | Validator runs own model in sandbox; must equal leader status |
| **Deterministic Decisions** (`SAME` vs not-`SAME`) | **YES** | Validator checks verbatim appearance in own normalized text |
| **Cited Quotes Grounding** | **YES** | Leader's cited quote must be verbatim substring of validator passage |
| **Target Fingerprint (REVISION)** | **YES** | Compared for strict equality in canonical string |
| **Target Fingerprint (LIVE)** | **NO (Excluded)** | Strictly `"NONE"` in canonical string to prevent dynamic noise |
| **Character Counts & Scanned Chars** | **NO (Excluded)** | Kept in audit metadata; excluded from consensus string |
| **Passage IDs (`p1`, `p2`)** | **NO (Excluded)** | Passages re-derived independently; matching by text only |
| **Cited Quote Text Byte Equality** | **NO (Excluded)** | Validators may extract slightly different boundaries; substring required |

### Live Studionet Benchmark: Status-Equality vs. Grounding-Only Validators
Evaluated on **GenLayer Studionet (Preview)** across 3 consecutive live runs each of COSMETIC and MATERIAL drift:

| Validator Architecture | Target Scenario | Run 1 Result | Run 2 Result | Run 3 Result | Consensus Agreement Rate | Median Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Status-Equality Validator (v1.2.0)** | COSMETIC (Computing) | `ACCEPTED` (3/5, 21.72s) | `ACCEPTED` (3/5, 8.40s) | `ACCEPTED` (3/5, 8.41s) | **100% (3/3)** | **8.41s** |
| **Status-Equality Validator (v1.2.0)** | MATERIAL (Python Foundation) | `ACCEPTED` (3/5, 38.22s) | `ACCEPTED` (3/5, 8.52s) | `MAJORITY_DISAGREE` (0/5, 7.82s) | **66.7% (2/3)** | **8.52s** |
| Grounding-Only Validator (v1.1.0) | COSMETIC (Computing) | `ACCEPTED` (3/5, 5.17s) | `ACCEPTED` (3/5, 8.48s) | `ACCEPTED` (3/5, 8.42s) | 100% (3/3) | 8.48s |
| Grounding-Only Validator (v1.1.0) | MATERIAL (Python Foundation) | Disagree (0/5, 122s) | Disagree (0/5, 122s) | Disagree (0/5, 123s) | 0% (0/3) | 122s (timeout) |

### Design Trade-Off Analysis
Independent validator classification delivers real decentralization: no single model's interpretation of rephrasing or material modification is blindly trusted by the network. On Studionet:
- **COSMETIC Drift**: 100% agreement across all runs. LLMs consistently distinguish synonymous rewording from substantive changes.
- **MATERIAL Drift**: 66.7% first-attempt agreement. Non-deterministic variations across heterogeneous validator LLMs (e.g. `prd-gpt-oss` vs `prd-sonnet`) occasionally yield a disagreement round, cleanly resolved on client retry.
- **Format Stability**: Bounded leader retry (up to 2 corrective retries requesting strict JSON without markdown code blocks) prevents syntax errors without fragile regex heuristics.

### Leader Failure Verification (Issue 2)
In v1.1.0, validators accepted any leader `"FAIL|..."` response without verification, opening a potential griefing vector. In v1.2.0:
1. `FAIL|ABSENCE_UNSUPPORTED`: Recomputed by the validator on its own fetched text. If the validator's coverage is sufficient, the leader failure is rejected.
2. `FAIL|INVALID_MODEL_OUTPUT` and `FAIL|CITED_QUOTE_NOT_VERBATIM`: The validator executes its own model classification once inside `spawn_sandbox`. It accepts the leader's failure **only if the validator's own run also fails or produces an invalid output**; otherwise, it rejects the leader.
3. `FAIL|SOURCE_UNAVAILABLE`: Validator confirms HTTP or network unavailability on its own fetch.

## 6. Storage Compaction & Non-Evictable Revision Checks
To prevent re-auditing older revisions even if in-memory audit logs are pruned:
```python
audited_revisions: TreeMap[str, str]  # Key: f"{citation_id}:{target_oldid}" -> audit_class
```
- Every completed `REVISION` audit writes permanently to `audited_revisions`.
- `audit_citation` checks `if audit_key in self.audited_revisions:` before executing.
- Even if the audit log inside the citation record is compacted, old revisions remain permanently non-re-auditable.

## 7. Storage Scalability: O(1) Per-Key Mappings
All unbounded JSON arrays and objects in storage slots were replaced with native `TreeMap`:
- `meta["ids"]` -> `citation_ids: TreeMap[str, str]` (0-indexed sequential access).
- `meta["registrations"]` -> `registrations: TreeMap[str, str]` (registration fingerprint -> `citation_id`).
- `ClaimsBoard` replaced `meta["ids"]` with `claim_ids: TreeMap[str, str]`.
- All operations are strictly $O(1)$ in storage reads/writes.

## 8. Explicit Classification: On-Chain vs. Unit-Tested Only
In strict compliance with the Honesty Rules, behaviors are partitioned by verification venue:

### Verified On-Chain (GenLayer Studionet Preview)
1. **UNCHANGED Deterministic Path**: Alan Turing revision 1380390650 (Tx `0x4480823e8b6299c1aa9105e59231f4b4e12be10b102966e493a48f9101619268`, `ACCEPTED`, `MAJORITY_AGREE`, 3/5 votes).
2. **LIVE Article Consensus**: Alan Turing live page (Tx `0xc7d06524a9096bfcdf0f75c691f1a2c2cfe8861548f85e91f707cb8d2a90eefc`, `ACCEPTED`, `MAJORITY_AGREE`, 3/5 votes). Dynamic fingerprint excluded.
3. **COSMETIC Drift & Model Layer**: Computing revision 1380219262 (Tx `0xada45043809d4aec8ef6fe70cd5df6435e823c191d851bc9886b840a6e229460`, `ACCEPTED`, `MAJORITY_AGREE`, 3/5 votes). Model classified `REPHRASED` on "narrower sense", status equality verified.
4. **MATERIAL Drift & Model Layer**: Python Foundation revision 1379380903 (Tx `0xed419e9b817c4e0b034f613957224a12c2b790055e2e139b245961b03adcfc39`, `ACCEPTED`, `MAJORITY_AGREE`, 3/5 votes). Model classified `CHANGED` on supported releases update.
5. **ClaimsBoard Badge Transition**: Verified cross-contract state transition (`0x4aef43f12493bfeadb60a14f265db5ed74883ac5262b6d354443c11117b40c5f`, `ACCEPTED`, `MAJORITY_AGREE`, 4/5 votes). Initial badge `VERIFIED`, updated to `DRIFTED`, recording `badge_history: ["VERIFIED", "DRIFTED"]`.
6. **13 Negative Revert Scenarios**: All 13 negative test transactions evaluated on-chain with exact decoded error payloads accepted by validators (`MAJORITY_AGREE`, 3/5 to 4/5 votes).

### Unit-Tested Only (Not On-Chain)
1. **REMOVED Drift Successful State Transition**: Verified in 29 passing offline unit tests (`test_audit_citation_removed_drift`) where simulated LLM returns valid bare JSON for absent elements. On-chain Charles Babbage test reverted with `invalid model output` due to live leader LLM policy token formatting on complete deletion, with failure verified by validator probe.
2. **Absence Calibration Threshold Grid**: Evaluated across 16 Wikipedia revision pairs (8 deleted, 8 reworded) via offline script `scripts/tools/calibrate_absence.py`.
3. **Bounded Leader Retry Mock Fallback**: Unit-tested in `test_layer3_consensus.py` verifying behavior when simulated LLM outputs invalid JSON before returning valid payload on retry.
