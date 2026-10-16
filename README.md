# CitationWatch: Semantic Drift Ledger on GenLayer Studionet (Preview)

> Intelligent Contract system for semantic citation drift detection against immutable Wikipedia revision baselines.

[![GenLayer Studionet](https://img.shields.io/badge/Network-GenLayer%20Studionet%20(Preview)-blue)](https://explorer-studio.genlayer.com)
[![Chain ID](https://img.shields.io/badge/Chain%20ID-61999-brightgreen)](https://studio.genlayer.com/api)
[![Status](https://img.shields.io/badge/Contracts-Accepted%20by%20Validators-success)](https://explorer-studio.genlayer.com)

---

## What and Why

A web page cited in a contract, research publication, or public record can be silently modified—numbers change, sentences are reversed, or claims disappear—while the URL continues to return HTTP 200. Traditional cryptographic byte hashing is brittle because minor formatting, CSS, or navigation edits break the hash entirely.

**CitationWatch** introduces semantic drift detection with an honest, reproducible baseline:
1. **Immutable Baseline**: Citations are registered against pinned, immutable Wikipedia revision permalinks (`oldid`).
2. **Deterministic-First Layer**: Tracked verbatim quotes from the baseline are verified deterministically. If a quote remains verbatim in the target document, it is immediately marked `SAME` without invoking an AI model.
3. **Strict Model Layer for Paraphrases & Changes**: For quotes that no longer appear verbatim, validator models evaluate whether the assertion is `REPHRASED` (cosmetic rewording), `CHANGED` (material factual conflict), or `ABSENT` (sentence deleted). Every classification requires verbatim quotation from fingerprinted document passages.
4. **ABSENT Discipline**: Absence of evidence requires proof of coverage. A model claim of `ABSENT` is rejected unless a full-document lexical-overlap scan proves no relevant passage exists.
5. **ClaimsBoard Consumer**: Proves cross-contract composability by consuming citation status strings and maintaining verified badges (`VERIFIED`, `REPHRASED`, `DRIFTED`, `REMOVED`).

---

## Contract Method Reference

### SourceDriftLedger (`contracts/SourceDriftLedger.py`)

| Method Type | Signature | Description |
| :--- | :--- | :--- |
| `write` | `register_citation(label: str, baseline_url: str, quotes_json: str) -> None` | Deterministically verifies 1..4 quotes against an immutable Wikipedia revision and registers the baseline record. |
| `write` | `audit_citation(citation_id: str, target_url: str) -> None` | Audits the citation against a later revision or live page, applying the deterministic layer and model layer within a 12,000 char budget. |
| `view` | `get_citation(citation_id: str) -> str` | Returns the complete JSON citation object with element fingerprints, full audit detail, and compact history. |
| `view` | `get_status(citation_id: str) -> str` | Returns a compact string: `STATUS\|CLASS\|AUDITS_TOTAL\|LATEST_AUDITED_AT`. |
| `view` | `get_audit_history(citation_id: str) -> str` | Returns the complete JSON audit history array. |
| `view` | `list_citation_ids(offset: int, limit: int) -> str` | Returns a paginated JSON list of citation IDs, newest-first. |
| `view` | `get_meta() -> str` | Returns metadata including schema version, nonce, and citation counts. |

### ClaimsBoard (`contracts/ClaimsBoard.py`)

| Method Type | Signature | Description |
| :--- | :--- | :--- |
| `write` | `set_ledger(ledger_address: str) -> None` | One-time owner-only configuration binding the consumer to the deployed `SourceDriftLedger`. |
| `write` | `publish_claim(citation_id: str, headline: str) -> None` | Publishes a headline bound to an existing ledger citation, initializing its badge via cross-contract view call. |
| `write` | `refresh_claim(entry_id: str) -> None` | Re-queries the ledger and updates the claim badge, appending to history only upon status change. |
| `view` | `get_claim(entry_id: str) -> str` | Returns the JSON claim record including current badge and badge history. |
| `view` | `list_claim_ids(offset: int, limit: int) -> str` | Returns a paginated JSON list of published claim IDs. |
| `view` | `get_ledger_address() -> str` | Returns the configured ledger address. |

---

## On-Chain Verification & Evidence

The table below is generated from `scripts/deploy/live_evidence.json` and records every on-chain transaction executed on **GenLayer Studionet (Preview)**.

<!-- EVIDENCE_TABLE_START -->

### Deployed Contracts on GenLayer Studionet (Preview)

| Contract | Address | Deploy Tx Hash | Source SHA-256 (Local & On-Chain) | Status | Consensus |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SourceDriftLedger** (Main) | [`0x0d24CC10b5396C718c019E239c90c7eE6b17BE57`](https://explorer-studio.genlayer.com/address/0x0d24CC10b5396C718c019E239c90c7eE6b17BE57) | `0x8058288116cb78df58dd1c5dd1a84383ac8bc6ea3ca1b3bd06b81f2beb40d874` | `e3b4bf9ce11e5f418126585820916f442bd22f23610bbfdb3a3de8065eeb3bd8` | ACCEPTED | MAJORITY_AGREE |
| **ClaimsBoard** (Consumer) | [`0x76Ef8E906c8Fec113c4Db846e60196E58e6B818D`](https://explorer-studio.genlayer.com/address/0x76Ef8E906c8Fec113c4Db846e60196E58e6B818D) | `0x4865176578ebf2b800c5fe61ca75a0bcafddf8f6464bb8ace32b2134824fc04c` | `3fc42682eebb7522edb5d0039969fea0232456596a37eda9f1ce698639ee3a10` | ACCEPTED | MAJORITY_AGREE |

**Cross-Contract Linking (`set_ledger`):**
- Tx Hash: `0x02f91c5c28318f6e330d27332181b7bc38bffd96a9fa2cdf2f882727e51cddcd`
- Status: `ACCEPTED`
- Configured Ledger on Consumer: `0x0d24CC10b5396C718c019E239c90c7eE6b17BE57`

### On-Chain Execution Scenarios & Evidence

| Scenario | Citation ID / Target | Registration Tx | Audit / Action Tx | Validator Agreement | Outcome Class | Final Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Scenario 1: UNCHANGED Revision Audit** (Alan Turing) | `a984e9a3885e`<br>oldid 1380390650 | `0x282199b8d13ea5c8a15b4e09e60291dbff1b1926a8745ac42dd0d5ea2ab1f2ad` | `0x03901425b132d9b9a8cc1782cb3c9617e3d0e58deb153ed8a796e2825cf15edd` | Register: 3/5<br>Audit: 3/5 | `UNCHANGED` | `HEALTHY` |
| **Scenario 2: LIVE Page Audit** (Non-Reproducible) | `a984e9a3885e`<br>/wiki/Alan_Turing | (inherited from S1) | `0xf318baa863cb01e8747ec8f493d75e874f0ae1537cd9c4e5521032122f06c010` | Audit: 0/5 (Disagreed) | `NON_REPRODUCIBLE` | `UNDETERMINED` |
| **Scenario 3: ClaimsBoard Integration** (Publish + Refresh) | Claim: `175c4c8df043`<br>Citation: `a984e9a3885e` | Publish: `0x218d9fcef79b2b813cf741f2635fc7f4c09cfd81095b7abeba0d039802b16a5a` | Refresh: `0xf18d3cd4946c4a1cf1d071c15c5ebc60c844af8ea091d5c13e911c2bd2c3c203` | Publish: 3/5<br>Refresh: 4/5 | Initial: `VERIFIED` | Badge: `VERIFIED` |
| **Scenario 4: Film Gross Metric** (Overlong Document) | `a984e9a3885e` | `0xbbb159322de6f75b8e70df96802dd09935ef42b197e0a57d4d2aec37c63d31bf` | `0x871e092e1bfd5b850d549eed00b0abed856ab973e646eca14b1f2c4372a0a631` | Register: 0/5<br>Audit: 5/5 | (Registration Disagreed) | `REVERTED` |

### On-Chain Negative Tests & Revert Payloads

All negative tests were submitted directly to the GenLayer Studionet RPC and evaluated by validator consensus. Revert messages below were decoded from the on-chain leader receipts:

| Test Case | Invoked Function | Transaction Hash | Status | Consensus | Agreement | Decoded Revert Payload |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Quote Not Verbatim in Baseline** | `register_citation` | `0xd0b085359710df97e06fb5af0c01e978a3370e44d1fd9a49e8cf6c2631bfe40c` | ACCEPTED | MAJORITY_AGREE | 3/5 | `quote not found verbatim in baseline` |
| **Non-Permalink Baseline URL** | `register_citation` | `0xcb130a1605d47797d89408bf885716e6cb222c5033dc0e24237c799d336a5dee` | ACCEPTED | MAJORITY_AGREE | 3/5 | `baseline must be an immutable revision permalink` |
| **Target Revision Older or Equal to Baseline** | `audit_citation` | `0x480b1ebb10a2cf5b6d38da671b22448033349d4c8d37250035bb340e6e9daed4` | ACCEPTED | MAJORITY_AGREE | 3/5 | `target revision must be later than baseline` |
| **Cross-Page Target URL Mismatch** | `audit_citation` | `0x1c65f47fb909a80e2bd25c2f79ca6aad4859759a7933e8569229ca6ee2a8825e` | ACCEPTED | MAJORITY_AGREE | 3/5 | `target title must match baseline title` |
| **Cross-Host Target URL Mismatch** | `audit_citation` | `0xd96459f768bf41792ea35c683d8db1d5bb1bac5ea191bf9b12fe09ab35660df4` | ACCEPTED | MAJORITY_AGREE | 3/5 | `target URL host must match baseline host` |
| **Non-Allowlisted Domain** | `register_citation` | `0xdd36c191d0c979227f138ca14ef7029d166906d3808147ae22b112d4a15e52d8` | ACCEPTED | MAJORITY_AGREE | 4/5 | `source URL must be a wikipedia.org language domain` |
| **Userinfo URL Spoof** | `register_citation` | `0x5ede866537e381cea91f56207c2681999ccb0c972cbc29ad9993b97981a19256` | ACCEPTED | MAJORITY_AGREE | 3/5 | `source URL cannot contain userinfo` |
| **Fragment URL Spoof in Baseline** | `register_citation` | `0x8443bd13d58298ca3ade7fefcc2b5b730acb72804f4c5ab9142690f1093dd71a` | ACCEPTED | MAJORITY_AGREE | 3/5 | `baseline URL cannot contain fragment` |
| **Duplicate Citation Registration** | `register_citation` | `0x992ffbe72878a7a0a09cfdefce4f762e8674e1b8e72c7f674a879247cf34b490` | ACCEPTED | MAJORITY_AGREE | 5/5 | `already registered` |
| **Repeated Target Revision Audit** | `audit_citation` | `0x5d8b4bb2b22b3c2692ab43ed2e0c20af6d89f665b47acd4524c65dda21d03849` | ACCEPTED | MAJORITY_AGREE | 3/5 | `target already audited` |
| **Audit Nonexistent Citation** | `audit_citation` | `0x89ea8f911ae3248532f0ffd70f463afcd5b884cff0907349f3de96c812d1dbbc` | ACCEPTED | MAJORITY_AGREE | 3/5 | `citation not found` |

<!-- EVIDENCE_TABLE_END -->

---

## Superseded Deployments

The following table records earlier contract iterations superseded during development:

| Contract | Address | Deploy Tx Hash | Superseded Reason |
| :--- | :--- | :--- | :--- |
| Probe Contract | `0x2eeF70885ff485D248A682443b4399A8A093F346` | `0x493cb3f124f947f8ee32801082c2d2fe7f318af3dea4a063a0a69d637f386b3f` | Initial runtime probe for SDK validation and Wikipedia fetch benchmarking. |

---

## Quick Start & Verification

Run the full verification pipeline:
```bash
npm run check
```
This single command executes:
1. Unit tests (Layer 1 pure, Layer 2 mocked, Layer 3 consensus mocks).
2. Pure ASCII scanner across all contract source files.
3. Banned wording scanner.
4. Secret scanner.
5. On-chain source code verification via RPC (`eth_getTransactionByHash`).
6. Evidence consistency check across deployments, evidence JSON, and documentation.
