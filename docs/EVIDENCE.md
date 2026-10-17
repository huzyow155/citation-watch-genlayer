# On-Chain Evidence & Verification Log

This document provides complete, unedited receipts and validator consensus measurements for all on-chain operations executed on **GenLayer Studionet (Preview)** (Chain ID 61999).

### Deployed Contracts on GenLayer Studionet (Preview)

| Contract | Address | Deploy Tx Hash | Source SHA-256 (Local & On-Chain) | Status | Consensus |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SourceDriftLedger** (Main v1.2.0) | [`0xFC7593432D4e8A2ceda911497807E4aCC7c7B705`](https://explorer-studio.genlayer.com/address/0xFC7593432D4e8A2ceda911497807E4aCC7c7B705) | `0x029460eceeeff13d0f261c1b32a28532988836da8e23b85880b2b23f1bc4538e` | `d5598c5e118d8411e87ef03f637950dc147799c94167ab8b0a70dd19c2215c8a` | ACCEPTED | MAJORITY_AGREE |
| **ClaimsBoard** (Consumer v1.2.0) | [`0x057fA33Ed3508AAe0051d72e81dD6B0Ba52009aD`](https://explorer-studio.genlayer.com/address/0x057fA33Ed3508AAe0051d72e81dD6B0Ba52009aD) | `0x085aa3015eb90eac0e1c10aa65424616ee96c2b85ed6992ee296b50b21d61398` | `4ee7d485bcaf7505514377abfea8f05eb3286447c13752df2847a3de7d0e8569` | ACCEPTED | MAJORITY_AGREE |

**Cross-Contract Linking (`set_ledger`):**
- Tx Hash: `0x696ade939bedb59784b8254af52c527c5082ba2c4c713f08f788b2e2edf67eba`
- Status: `ACCEPTED`
- Configured Ledger on Consumer: `0xFC7593432D4e8A2ceda911497807E4aCC7c7B705`

### On-Chain Execution Scenarios & Evidence

| Scenario | Citation ID / Target | Registration Tx | Audit / Action Tx | Validator Agreement | Outcome Class | Final Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Scenario 1: UNCHANGED Revision Audit** (Alan Turing) | `bbee352df865`<br>oldid 1380390650 | `0x4480823e8b6299c1aa9105e59231f4b4e12be10b102966e493a48f9101619268` | `0x3db12b8799b4291a00d72b66966bdb3f6397168606af4c987c5eae492afe1a53` | Register: 3/5<br>Audit: 3/5 | `UNCHANGED` | `HEALTHY` |
| **Scenario 2: LIVE Page Audit & Multi-Audit History** | `bbee352df865`<br>/wiki/Alan_Turing | (inherited from S1) | `0xc7d06524a9096bfcdf0f75c691f1a2c2cfe8861548f85e91f707cb8d2a90eefc` | Audit: 3/5 | `UNCHANGED` (Live Consensus Verified) | `HEALTHY` (2 Audits in History) |
| **Scenario 3: COSMETIC Drift Audit** (Computing Wording) | `4f3305759701`<br>oldid 1380219262 | `0x72de77de0257790c6a7b7cb8fcf5c62df70b542aa1e433057519ec5c2ca695ec` | `0xada45043809d4aec8ef6fe70cd5df6435e823c191d851bc9886b840a6e229460` | Register: 3/5<br>Audit: 3/5 | `COSMETIC` (Model Decided: REPHRASED) | `HEALTHY` |
| **Scenario 4: MATERIAL Drift Audit** (Python Foundation) | `59a2e370301f`<br>oldid 1379380903 | `0xdd6d078e80d98affc5435d5ca941e0ee50f842107f4aff679c0522f6829bcbdf` | `0xed419e9b817c4e0b034f613957224a12c2b790055e2e139b245961b03adcfc39` | Register: 3/5<br>Audit: 3/5 | `MATERIAL` (Model Decided: CHANGED) | `DRIFTED` |
| **Scenario 5: REMOVED Drift Audit (Attempted on-chain, reverted)** | `4339810e1be9`<br>oldid 1378652484 | `0xa6dab9f59c5702b5d46daf7670e1637142ccaeabe2f1bf05a9b08d42ecd659e4` | `0x67971b146bbb501339da8b8017b7daf596e517c30e0ac5dc14d43af7a84825b4` | Register: 3/5<br>Audit: 3/5 | (Attempted on-chain, reverted: `invalid model output`) | `UNAUDITED` |
| **Scenario 6: ClaimsBoard Badge Transition** | Claim: `56d9663a46e2`<br>Citation: `a68c69aa9a4d` | Publish: `0x4cdb8f24b802873744cb9f170963d55975e83cf70133a11cbda8974df852ced3` | Refresh: `0x4aef43f12493bfeadb60a14f265db5ed74883ac5262b6d354443c11117b40c5f` | Publish: 3/5<br>Refresh: 4/5 | Initial: `VERIFIED`<br>Refreshed: `DRIFTED` | History: `[VERIFIED, DRIFTED]` |

**Transaction Finality Measurement (Scenario 7):**
- Measured Transaction: `0xf730a365f584bc2d46aa33ce78fa9bd8f1061e5fecb0f548222259e1eb4a9835`
- Real-Time Elapsed: Transitioned to `FINALIZED` in 79.82s (11 polls from local submit timestamp)

### Attempted On-Chain, Reverted (REMOVED Audits)

A reverted audit is not evidence that REMOVED state transition works on-chain. On GenLayer Studionet, when an element is completely absent from presented passages, live validator LLM policies (`prd-minimax`, `openai/gpt-5.4`, `prd-mistral`) produce formatting variations or non-bare JSON that fail the contract's strict schema validator, triggering `invalid model output`. Under Issue 2 failure verification, validators probe their model and accept the leader's failure, causing the transaction to revert. While the leader receipt logs token counts, raw output tokens are not exposed on-chain. Therefore, **REMOVED state transition success is unit-tested only**.

| Target Scenario | Citation ID / Target | Audit Transaction Hash | Status | Consensus | Agreement | Decoded Revert Payload |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Charles Babbage Death Detail** | `4339810e1be9`<br>oldid 1378652484 | `0x67971b146bbb501339da8b8017b7daf596e517c30e0ac5dc14d43af7a84825b4` | ACCEPTED | MAJORITY_AGREE | 3/5 | `invalid model output` |
| **Albert Einstein Israeli Address Detail** | `a68c69aa9a4d`<br>oldid 1362681578 | `0x99a0d74bed90753464a2db90f52d25beb100e52e7a9f8dd185fce7d1de180c42` | ACCEPTED | MAJORITY_AGREE | 4/5 | `target title must match baseline title` |
| **Scratch Platform Introduction** | `5b0443a8f7bf`<br>oldid 1376243974 | `0xcf187edb60e269dd405e3b254eec9d8c42f6a342849db9e29db01c5954788381` | ACCEPTED | MAJORITY_AGREE | 3/5 | `invalid model output` |
| **Software Creation Landscape Claim** | `2497410551e9`<br>oldid 1374736226 | `0xb346021fc54d9ea5976095688f3b6c23ae57656f74526d3de5d6d3963c5c74ee` | ACCEPTED | MAJORITY_AGREE | 3/5 | `invalid model output` |

### Explicit Classification: On-Chain vs. Unit-Tested Only

In strict compliance with the Honesty Rules, behavior is partitioned by where evidence was obtained:

#### Verified On-Chain (GenLayer Studionet Preview)
- **UNCHANGED Deterministic Path**: Fully verified on-chain (Alan Turing revision 1380390650, Tx `0x3db12b8799b4291a00d72b66966bdb3f6397168606af4c987c5eae492afe1a53`, status `ACCEPTED`, consensus `MAJORITY_AGREE`, 3/5 votes). Both leader and validators matched quote verbatim without invoking model.
- **LIVE Article Consensus Payload**: Fully verified on-chain (/wiki/Alan_Turing, Tx `0xc7d06524a9096bfcdf0f75c691f1a2c2cfe8861548f85e91f707cb8d2a90eefc`, status `ACCEPTED`, consensus `MAJORITY_AGREE`, 3/5 votes). Excluding live fingerprint and character counts from consensus payload resolved consensus disagreement.
- **COSMETIC Drift (Independent Model Consensus)**: Fully verified on-chain (Computing revision 1380219262, Tx `0xada45043809d4aec8ef6fe70cd5df6435e823c191d851bc9886b840a6e229460`, status `ACCEPTED`, consensus `MAJORITY_AGREE`, 3/5 votes). Validators independently executed model classification within `gl.vm.spawn_sandbox` and achieved consensus on status `REPHRASED`.
- **MATERIAL Drift (Independent Model Consensus)**: Fully verified on-chain (Python Foundation revision 1379380903, Tx `0xed419e9b817c4e0b034f613957224a12c2b790055e2e139b245961b03adcfc39`, status `ACCEPTED`, consensus `MAJORITY_AGREE`, 3/5 votes). Real prose sentence fact change independently classified as status `CHANGED` across validators.
- **ClaimsBoard Cross-Contract Badge Transition**: Fully verified on-chain (Claim `56d9663a46e2`, Publish Tx `0x4cdb8f24b802873744cb9f170963d55975e83cf70133a11cbda8974df852ced3`, Refresh Tx `0x4aef43f12493bfeadb60a14f265db5ed74883ac5262b6d354443c11117b40c5f`). Claim initialized with badge `VERIFIED`, citation drifted to `MATERIAL`, and `refresh_claim` transitioned badge to `DRIFTED`, recording `badge_history: ["VERIFIED", "DRIFTED"]`.
- **13 Negative Revert Scenarios**: All 13 negative test transactions reverted on-chain with exact decoded error payloads accepted by validators.

#### Unit-Tested Only (Not On-Chain)
- **REMOVED Drift Successful State Transition**: Verified in 29 passing offline unit tests (`test_audit_citation_removed_drift`) where simulated LLM returns valid bare JSON for absent elements. On-chain audits reverted with `invalid model output`.
- **Empirical Absence Threshold Evaluation & Controls**: Evaluated across 8 real deleted-sentence pairs, 5 unrelated controls, and 8 reworded pairs (including changed-but-similar sentences) via offline script `scripts/tools/calibrate_absence.py` yielding empirical separation margin between 0.3147 (max real deleted) and 0.4776 (min reworded) around threshold 0.45.
- **Bounded Leader Retry Mock Fallback**: Unit-tested in `test_layer3_consensus.py` verifying behavior when simulated LLM outputs invalid JSON before returning valid payload on retry.

### On-Chain Negative Tests & Revert Payloads (13 Tests)

All negative tests were submitted directly to the GenLayer Studionet RPC and evaluated by validator consensus. Revert messages below were decoded from the on-chain leader receipts:

| Test Case | Invoked Function | Transaction Hash | Status | Consensus | Agreement | Decoded Revert Payload |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Quote Not Verbatim in Baseline** | `register_citation` | `0xeef181b6657198d2ef7c35e19fca31c34c6fe01b47cba66155ad1c84b8311842` | ACCEPTED | MAJORITY_AGREE | 3/5 | `quote not found verbatim in baseline` |
| **Non-Permalink Baseline URL** | `register_citation` | `0xb4db739bb1d25df2148430e1a19050d8d4f2749adfac5fde06f1c79bc8d3f938` | ACCEPTED | MAJORITY_AGREE | 3/5 | `baseline must be an immutable revision permalink` |
| **Target Revision Older or Equal to Baseline** | `audit_citation` | `0x16c1d917940065ded2a91e50b447eef5d6af6d35742604e177322f3f84fc4ea6` | ACCEPTED | MAJORITY_AGREE | 4/5 | `target revision must be later than baseline` |
| **Cross-Page Target URL Mismatch** | `audit_citation` | `0x7e87ffd64b0a88aa56cc3366ee59633f83ef184107d8cd6cf126ca28b19fe356` | ACCEPTED | MAJORITY_AGREE | 4/5 | `target title must match baseline title` |
| **Cross-Host Target URL Mismatch** | `audit_citation` | `0xb341d5f8a89eea597be1587561df018a33149fef645ad0c81e9732a5968b90ac` | ACCEPTED | MAJORITY_AGREE | 3/5 | `target URL host must match baseline host` |
| **Non-Allowlisted Domain** | `register_citation` | `0x65efa4541979eac1db27595735aa70a2aa72b098f1736ba6dea421f8cef0bd66` | ACCEPTED | MAJORITY_AGREE | 3/5 | `source URL must be a wikipedia.org language domain` |
| **Userinfo URL Spoof** | `register_citation` | `0xa4edf5cfaaa75968b67000d72fbff08768bb28c7799a3fb6f205db4e2d06d299` | ACCEPTED | MAJORITY_AGREE | 3/5 | `source URL cannot contain userinfo` |
| **Fragment URL Spoof in Baseline** | `register_citation` | `0xa7e172225d98d08c7b9eac3e73d3e863cc7302488b99f5ef0b7034b5d737afc6` | ACCEPTED | MAJORITY_AGREE | 3/5 | `baseline URL cannot contain fragment` |
| **Duplicate Citation Registration** | `register_citation` | `0xf297d7e12c7b8c32d1f69153da46c6af899d693ef4b9b4e3a0967fe99e346a18` | ACCEPTED | MAJORITY_AGREE | 4/5 | `already registered` |
| **Repeated Target Revision Audit** | `audit_citation` | `0x3720892f79c707f17ca7faea1a1e78bd1149bf985dd99f7101f3906b8adfe7da` | ACCEPTED | MAJORITY_AGREE | 3/5 | `target already audited` |
| **Audit Nonexistent Citation** | `audit_citation` | `0x32888491e7174b193b51a876de8d02e2adae9daa6308fa6f083ca0a6cd46eb81` | ACCEPTED | MAJORITY_AGREE | 3/5 | `citation not found` |
| **Look-Alike Domain Spoof (en.wikipedia.org.evil.com)** | `register_citation` | `0x974fb283b46aadf608c25c9965d1bc33f8d7457e0d0188281ffa134bf24a1b71` | ACCEPTED | MAJORITY_AGREE | 4/5 | `source URL must be a wikipedia.org language domain` |
| **LIVE Audit Cooldown Violation (<300s)** | `audit_citation` | `0x05c4de3ec1dacd6a8b108bab9d022b096c85b1a1982bd0ba8f86e583aae4f427` | ACCEPTED | MAJORITY_AGREE | 3/5 | `live audit cooldown active` |


### Method of Source Verification
- Exact RPC call used: `eth_getTransactionByHash` with deployment transaction hash parameter.
- Payload field inspected: `result.data.contract_code`, base64-decoded into contract source text.
- SHA-256 fingerprint matching: On-chain source hash exactly matches repository file hashes.
