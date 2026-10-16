# On-Chain Verification & Method of Receipt Inspection (v1.1.0)

## Verification Method

Every smart contract deployment and transaction reported in this project was independently verified against the **GenLayer Studionet (Preview)** RPC endpoint (`https://studio.genlayer.com/api`).

### 1. Contract Source Code Verification
- **RPC Call**: `eth_getTransactionByHash`
- **Parameter**: Deployment transaction hash
- **Field**: `result.data.contract_code` (base64-encoded Python contract source)
- **Local Verification Script**: `node scripts/deploy/verify_source.js`
- **Result**: The decoded on-chain source text matches the local repository source files byte-for-byte, producing identical SHA-256 fingerprints:
  - `SourceDriftLedger.py` (v1.1.0): `130f8b11bfb3b609dbdcffa92b3b1cdbd8795ec5f2ed51618e47cfb005ef2866`
  - `ClaimsBoard.py` (v1.1.0): `4ee7d485bcaf7505514377abfea8f05eb3286447c13752df2847a3de7d0e8569`

### 2. Leader Execution & Revert Payload Decoding
For both accepted and reverted transactions on GenLayer Studionet:
- **Receipt Field**: `result.consensus_data.leader_receipt[0].result`
- **Encoding**: Base64-encoded buffer.
- **Decoding**: Byte 0 indicates the result code (`ResultCode.RETURN` or `ResultCode.USER_ERROR`), followed by UTF-8 bytes containing the user error message.
- Every negative test in the canonical suite was confirmed by decoding this exact buffer from the on-chain receipt.

### 3. Active Deployed Contract Addresses (v1.1.0)
- **SourceDriftLedger (Main v1.1.0)**:
  - Address: `0xc6a8Cfdbbb4CA98637053A0c8529686Ff4C41CaD`
  - Deploy Transaction: `0x25eecfa0238d344b520707aeca15aa3f30d21c7237e3ef52a1ad2e26915759a6`
  - Status: `ACCEPTED`, Consensus: `MAJORITY_AGREE` (3 agree / 5 nodes)
  - Source SHA-256: `130f8b11bfb3b609dbdcffa92b3b1cdbd8795ec5f2ed51618e47cfb005ef2866`
- **ClaimsBoard (Consumer v1.1.0)**:
  - Address: `0xfc454d601DC5300ECf8458610cB1580c9640bE32`
  - Deploy Transaction: `0x2856c22192ef04ad1f4384ee0957f56e18b9e08ed1c63a23254700c7aba1c210`
  - Status: `ACCEPTED`, Consensus: `MAJORITY_AGREE` (3 agree / 5 nodes)
  - Source SHA-256: `4ee7d485bcaf7505514377abfea8f05eb3286447c13752df2847a3de7d0e8569`
- **Connection Transaction (`set_ledger`)**:
  - Tx Hash: `0x85ad08735b5c7e2cdc857d2f6be3d7bf3fdae075983d1abf679fe1f1b3872a82`
  - Status: `ACCEPTED`, Consensus: `MAJORITY_AGREE` (3 agree / 5 nodes)
  - Configured Ledger: `0xc6a8Cfdbbb4CA98637053A0c8529686Ff4C41CaD`

### 4. Diagnostic Probes
- **Probe 1 (Initial API Signatures)**: `0x2eeF70885ff485D248A682443b4399A8A093F346` (Tx `0x493cb3f124f947f8ee32801082c2d2fe7f318af3dea4a063a0a69d637f386b3f`)
- **Probe 2 (`spawn_sandbox` inside Validator Context)**: `0x442863622d98F506c492C0484D187a9FeB487d77` (Deploy Tx `0x48a4789547ff56eaeb72e3a13783854ee7589d38f8fc87766f6ec6d9bc57ddcc`, Call Tx `0x386ef2d03232473837ce36542801acfeab232d72cd94fda4516ca1f987db29ea`)

