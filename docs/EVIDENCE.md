# On-Chain Evidence & Verification Log

This document provides complete, unedited receipts and validator consensus measurements for all on-chain operations executed on **GenLayer Studionet (Preview)** (Chain ID 61999).

### Deployed Contracts on GenLayer Studionet (Preview)

| Contract | Address | Deploy Tx Hash | Source SHA-256 (Local & On-Chain) | Status | Consensus |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SourceDriftLedger** (Main v1.1.0) | [`0xc6a8Cfdbbb4CA98637053A0c8529686Ff4C41CaD`](https://explorer-studio.genlayer.com/address/0xc6a8Cfdbbb4CA98637053A0c8529686Ff4C41CaD) | `0x25eecfa0238d344b520707aeca15aa3f30d21c7237e3ef52a1ad2e26915759a6` | `130f8b11bfb3b609dbdcffa92b3b1cdbd8795ec5f2ed51618e47cfb005ef2866` | ACCEPTED | MAJORITY_AGREE |
| **ClaimsBoard** (Consumer v1.1.0) | [`0xfc454d601DC5300ECf8458610cB1580c9640bE32`](https://explorer-studio.genlayer.com/address/0xfc454d601DC5300ECf8458610cB1580c9640bE32) | `0x2856c22192ef04ad1f4384ee0957f56e18b9e08ed1c63a23254700c7aba1c210` | `4ee7d485bcaf7505514377abfea8f05eb3286447c13752df2847a3de7d0e8569` | ACCEPTED | MAJORITY_AGREE |

**Cross-Contract Linking (`set_ledger`):**
- Tx Hash: `0x85ad08735b5c7e2cdc857d2f6be3d7bf3fdae075983d1abf679fe1f1b3872a82`
- Status: `ACCEPTED`
- Configured Ledger on Consumer: `0xc6a8Cfdbbb4CA98637053A0c8529686Ff4C41CaD`

### On-Chain Execution Scenarios & Evidence

| Scenario | Citation ID / Target | Registration Tx | Audit / Action Tx | Validator Agreement | Outcome Class | Final Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Scenario 1: UNCHANGED Revision Audit** (Alan Turing) | `0b206b8b6a06`<br>oldid 1380390650 | `0x442b3ed690574b4a2df0201599f7f8c2832b0892be6bd3e84427efb6a15b8246` | `0x34db8077b8b6995d44977c07849841c7d9f1a130ade597b6f7ca233a8cab6f72` | Register: 3/5<br>Audit: 3/5 | `UNCHANGED` | `HEALTHY` |
| **Scenario 2: LIVE Page Audit & Multi-Audit History** | `0b206b8b6a06`<br>/wiki/Alan_Turing | (inherited from S1) | `0x01a8d6faa62a4cad2266d3d1689d4c51771ebbdb90cfcb2ca3afb6e287569ab6` | Audit: 3/5 | `UNCHANGED` (Live Consensus Verified) | `HEALTHY` (2 Audits in History) |
| **Scenario 3: COSMETIC Drift Audit** (Computing Wording) | `257ae938161c`<br>oldid 1380219262 | `0xf6cde7ac2f7fe2076a89ca5b7e33fb0db0c30ddcac640b09be1e64c05495da95` | `0xd90d91b9ce5b91061e0d0441b7bc25f1525bdba49600d8e11f8bc7f36d0bf18a` | Register: 3/5<br>Audit: 3/5 | `COSMETIC` (Model Decided: REPHRASED) | `HEALTHY` |
| **Scenario 4: MATERIAL Drift Audit** (Oscars Fact Correction) | Attempt 1: `257ae938161c`<br>oldid 1370247723 | `0x15d35b4c79dc04a056252f0df9907b70000e733827d0bbddb10fb291968a4931` | Reverted: `quote not found verbatim in baseline` | Register: 3/5 | (Registration Revert: quote not verbatim) | `UNAUDITED` |
| **Scenario 5: REMOVED Drift Audit** (Charles Babbage) | `d81f10ae72a5`<br>oldid 1378652484 | `0x99703fdadcef1140ee59103f9d6de1de0160282452462d4bf254be58ef8c2faa` | `0x16397681fe7ec114c07025f6b0c371bc3390af5c7f9d69992906f88fb2ab3bcf` | Register: 3/5<br>Audit: 3/5 | (Audit Revert: `invalid model output`) | `UNAUDITED` |
| **Scenario 6: ClaimsBoard Cross-Contract Integration** | Claim: `9d3772c0090d`<br>Citation: `0b206b8b6a06` | Publish: `0x8e88696d25c92faf0c85facd5a878f3eedf35a6c208c2194787b28244aa704e5` | Multi-Claim Tx: `0xe77981973346ee2120efcaec8c7fbf537245770b6173eec4862e9c77042af353` | Publish: 3/5 | Derived Badge: `VERIFIED` | Consumer Integration Verified |

### Explicit Classification: On-Chain vs. Unit-Tested Only

In strict compliance with the Honesty Rules, behavior is partitioned by where evidence was obtained:

#### Verified On-Chain (GenLayer Studionet Preview)
- **UNCHANGED Deterministic Path**: Fully verified on-chain (Alan Turing revision 1380390650, Tx `0x34db8077b8b6995d44977c07849841c7d9f1a130ade597b6f7ca233a8cab6f72`, status `ACCEPTED`, consensus `MAJORITY_AGREE`, 3/5 votes).
- **LIVE Article Consensus Payload**: Fully verified on-chain (/wiki/Alan_Turing, Tx `0x01a8d6faa62a4cad2266d3d1689d4c51771ebbdb90cfcb2ca3afb6e287569ab6`, status `ACCEPTED`, consensus `MAJORITY_AGREE`, 3/5 votes). Proved that excluding the live target fingerprint and character counts resolved the v1.0.0 consensus disagreement (which scored 2/5).
- **COSMETIC Drift & Model Layer**: Fully verified on-chain (Computing revision 1380219262, Tx `0xd90d91b9ce5b91061e0d0441b7bc25f1525bdba49600d8e11f8bc7f36d0bf18a`, status `ACCEPTED`, consensus `MAJORITY_AGREE`, 3/5 votes). The LLM model evaluated tightened prose ("more narrow sense" -> "narrower sense"), classified `REPHRASED`, extracted passage `p15`, and custom validator consensus confirmed the cited quote without passage ID dependence.
- **Cross-Contract Integration**: Fully verified on-chain (ClaimsBoard `0xfc454d601DC5300ECf8458610cB1580c9640bE32` -> SourceDriftLedger `0xc6a8Cfdbbb4CA98637053A0c8529686Ff4C41CaD`, Tx `0x8e88696d25c92faf0c85facd5a878f3eedf35a6c208c2194787b28244aa704e5`, status `ACCEPTED`, consensus `MAJORITY_AGREE`, 3/5 votes).
- **10 Negative Revert Scenarios**: All 10 negative test transactions reverted on-chain with exact decoded payloads accepted by validators (3/5 to 5/5 votes).

#### Unit-Tested Only (Not On-Chain)
- **MATERIAL Drift State Transition**: Verified in 25 passing offline unit tests (`test_audit_citation_material_drift`). On-chain Attempt 1 reverted with `quote not found verbatim in baseline` due to MediaWiki table whitespace normalization differences between raw source and rendered text.
- **REMOVED Absence State Transition**: Verified in 25 passing offline unit tests (`test_absence_calibration`, `test_audit_citation_removed_drift`). On-chain Attempts 1 & 2 on Charles Babbage (`0xe54a7671...` and `0x16397681...`) reverted with `invalid model output` because the GenVM leader LLM policy (`prd-kimi`) returned extra explanatory tokens/formatting when evaluating deleted assertions rather than bare JSON without explanation.

### On-Chain Negative Tests & Revert Payloads

All negative tests were submitted directly to the GenLayer Studionet RPC and evaluated by validator consensus. Revert messages below were decoded from the on-chain leader receipts:

| Test Case | Invoked Function | Transaction Hash | Status | Consensus | Agreement | Decoded Revert Payload |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Quote Not Verbatim in Baseline** | `register_citation` | `0x73c0baadbaef72420f4507dca80c65c3581cc9d4292b30c804681d1ba0d12a6d` | ACCEPTED | MAJORITY_AGREE | 3/5 | `quote not found verbatim in baseline` |
| **Non-Permalink Baseline URL** | `register_citation` | `0xb45a282d83b66cb30b2518f39d23c0be98b0058d209ef812e5ddea1fc7e635ca` | ACCEPTED | MAJORITY_AGREE | 3/5 | `baseline must be an immutable revision permalink` |
| **Target Revision Older or Equal to Baseline** | `audit_citation` | `0x2f5fdefc93fc8585be979e8594e2633a87aa3d25d73c13bb911758556f1f2bc5` | ACCEPTED | MAJORITY_AGREE | 3/5 | `target revision must be later than baseline` |
| **Cross-Page Target URL Mismatch** | `audit_citation` | `0x8a35487be250f0eeae90f5cd89251e1268e32f67a904f7d2bb4dd6c014a28811` | ACCEPTED | MAJORITY_AGREE | 3/5 | `target title must match baseline title` |
| **Cross-Host Target URL Mismatch** | `audit_citation` | `0x5519012f51b4a4aac3500333fcac03443359b5d7304bd4fccea7c2e06fac8fde` | ACCEPTED | MAJORITY_AGREE | 3/5 | `target URL host must match baseline host` |
| **Non-Allowlisted Domain** | `register_citation` | `0x121baeec46cb47925a85ee35dd6f90fff3ca97c6eac541f8cf3ffcaccf54bf1a` | ACCEPTED | MAJORITY_AGREE | 4/5 | `source URL must be a wikipedia.org language domain` |
| **Userinfo URL Spoof** | `register_citation` | `0x76941f4f450594de4b3a1307ff1ecf5a0f3b82b58c6b5f1795fcc727a43bd056` | ACCEPTED | MAJORITY_AGREE | 5/5 | `source URL cannot contain userinfo` |
| **Fragment URL Spoof in Baseline** | `register_citation` | `0x6e3305ed84a6d3e25bda826041e74ed67183a90b245009a4939eda590555312f` | ACCEPTED | MAJORITY_AGREE | 4/5 | `baseline URL cannot contain fragment` |
| **Duplicate Citation Registration** | `register_citation` | `0xcb6b27fe2236460a70f4bb182393f9661271710a78e7e9c0d925a0740bda185d` | ACCEPTED | MAJORITY_AGREE | 3/5 | `already registered` |
| **Repeated Target Revision Audit** | `audit_citation` | `0x14621aa92b9d16a6c9b6b3e3077ae5de1dd8d90a32200ddaf3f05daec2f719f7` | ACCEPTED | MAJORITY_AGREE | 3/5 | `target already audited` |
| **Audit Nonexistent Citation** | `audit_citation` | `0x6ec58db77e4ed49ee93394bee9661db60b5b345764b9dd39d6bf1ce667daf244` | ACCEPTED | MAJORITY_AGREE | 3/5 | `citation not found` |


### Method of Source Verification
- Exact RPC call used: `eth_getTransactionByHash` with deployment transaction hash parameter.
- Payload field inspected: `result.data.contract_code`, base64-decoded into contract source text.
- SHA-256 fingerprint matching: On-chain source hash exactly matches repository file hashes.
