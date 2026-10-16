# On-Chain Verification & Method of Receipt Inspection (v1.2.0)

## Verification Method

Every smart contract deployment and transaction reported in this project was independently verified against the **GenLayer Studionet (Preview)** RPC endpoint (`https://studio.genlayer.com/api`).

### 1. Contract Source Code Verification
- **RPC Call**: `eth_getTransactionByHash`
- **Parameter**: Deployment transaction hash
- **Field**: `result.data.contract_code` (base64-encoded Python contract source)
- **Local Verification Script**: `node scripts/verify_source.js`
- **Result**: The decoded on-chain source text matches the local repository source files byte-for-byte, producing identical SHA-256 fingerprints:
  - `SourceDriftLedger.py` (v1.2.0): `d5598c5e118d8411e87ef03f637950dc147799c94167ab8b0a70dd19c2215c8a`
  - `ClaimsBoard.py` (v1.2.0): `4ee7d485bcaf7505514377abfea8f05eb3286447c13752df2847a3de7d0e8569`

### 2. Leader Execution & Revert Payload Decoding
For both accepted and reverted transactions on GenLayer Studionet:
- **Receipt Field**: `result.consensus_data.leader_receipt[0].result`
- **Encoding**: Base64-encoded buffer.
- **Decoding**: Byte 0 indicates the result code (`ResultCode.RETURN` or `ResultCode.USER_ERROR`), followed by UTF-8 bytes containing the user error message.
- Every negative test in the canonical suite was confirmed by decoding this exact buffer from the on-chain receipt.

### 3. Active Deployed Contract Addresses (v1.2.0)
- **SourceDriftLedger (Main v1.2.0)**:
  - Address: `0xFC7593432D4e8A2ceda911497807E4aCC7c7B705`
  - Deploy Transaction: `0x029460eceeeff13d0f261c1b32a28532988836da8e23b85880b2b23f1bc4538e`
  - Status: `ACCEPTED`, Consensus: `MAJORITY_AGREE` (3 agree / 5 nodes)
  - Source SHA-256: `d5598c5e118d8411e87ef03f637950dc147799c94167ab8b0a70dd19c2215c8a`
- **ClaimsBoard (Consumer v1.2.0)**:
  - Address: `0x057fA33Ed3508AAe0051d72e81dD6B0Ba52009aD`
  - Deploy Transaction: `0x085aa3015eb90eac0e1c10aa65424616ee96c2b85ed6992ee296b50b21d61398`
  - Status: `ACCEPTED`, Consensus: `MAJORITY_AGREE` (3 agree / 5 nodes)
  - Source SHA-256: `4ee7d485bcaf7505514377abfea8f05eb3286447c13752df2847a3de7d0e8569`
- **Connection Transaction (`set_ledger`)**:
  - Tx Hash: `0x696ade939bedb59784b8254af52c527c5082ba2c4c713f08f788b2e2edf67eba`
  - Status: `ACCEPTED`, Consensus: `MAJORITY_AGREE` (3 agree / 5 nodes)
  - Configured Ledger: `0xFC7593432D4e8A2ceda911497807E4aCC7c7B705`

### 4. Diagnostic Probes
- **Probe 2 (`spawn_sandbox` & Model in Validator Context)**: `0x0615C044A8B5Cf78693ABB2B466b5985CfBE9789` (Tx `0xb366b5c3ff3505e04ba5901c5d01ec134372e50c4563a5ba8bbf43d0f074d001`)
