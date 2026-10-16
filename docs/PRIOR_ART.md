# Prior Art & Differentiation Analysis

## Background & Prior Art Survey
The integrity of citations on the World Wide Web has been studied extensively in legal, academic, and decentralized systems:

1. **Link Rot and Content Drift in Academia & Law**:
   - Landmark studies by Zittrain et al. (Harvard Berkman Klein Center) revealed that over 50% of URLs cited in Supreme Court opinions and law review articles no longer point to the original cited content.
   - Traditional mitigations (such as Perma.cc, Archive.today, and the Wayback Machine) store static archived snapshots. However, they rely on centralized archival non-profits and lack automated, programmable mechanisms for on-chain contracts to detect when a live citation diverges.

2. **Blockchain Notarization & IPFS Hashes**:
   - Standard smart contract timestamping services record a single cryptographic byte hash (e.g. SHA-256) of a document or web page.
   - **Limitation**: Any byte-level change (CSS updates, navigation bar edits, advertising scripts, or typo corrections) breaks the hash completely. A byte hash cannot distinguish whether a page underwent a benign cosmetic adjustment or an essential factual reversal.

3. **Decentralized Oracles & TLS Verification**:
   - Protocol-level oracle solutions (such as Chainlink HTTP getters or TLSNotary/DECO) focus on proving that a specific server returned a specific byte string during an active TLS session.
   - **Limitation**: They do not provide semantic drift analysis over document evolution or element-wise tracking of specific quotes.

4. **GenLayer Intelligent Contracts Ecosystem**:
   - We conducted an ecosystem search and found no contract that tracks multi-element citation drift against immutable revision baselines with deterministic-first verbatim matching, lexical-overlap windowing, and strict model categorization.
   - Previous contracts in this repository environment focused on distinct paradigms:
     - *CommitmentLedger*: Tracking personal/organizational public commitments to future deadlines.
     - *CalibrationLedger*: Evaluating probabilistic forecasts against subsequent reality.
     - *CitationCourt*: Single-quote dispute adjudication without multi-audit history or consumer board badging.

## Novelty & Differentiation of CitationWatch
CitationWatch introduces key architectural differentiators:

1. **Immutable, Independent Baseline**: Citations must be anchored to immutable Wikipedia revision permalinks (`oldid`), preventing registrants from retroactively rewriting baseline context.
2. **Deterministic-First Execution**: Verbatim quote presence is evaluated deterministically in code. Non-deterministic AI models are invoked strictly for non-verbatim elements, ensuring zero false negatives on identical quotes and reducing consensus variance.
3. **Strict ABSENT Coverage Discipline**: Prevents false absence conclusions by mathematically requiring a full-document lexical-overlap scan before accepting an absence claim.
4. **Verbatim Grounding for Model Decisions**: The model cannot hallucinate or rephrase arbitrary external claims; any `REPHRASED` or `CHANGED` status must be grounded with a verbatim quote from a presented, fingerprinted passage.
5. **Separation of Concerns with ClaimsBoard Consumer**: Proves composability by allowing downstream smart contracts to consume semantic drift statuses without incurring model execution overhead.
