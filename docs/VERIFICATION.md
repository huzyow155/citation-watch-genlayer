# On-Chain Verification & Method of Receipt Inspection

## Verification Method

Every smart contract deployment and transaction reported in this project was independently verified against the **GenLayer Studionet (Preview)** RPC endpoint.

### 1. Contract Source Code Verification
- **RPC Call**: `eth_getTransactionByHash`
- **Parameter**: Deployment transaction hash
- **Field**: `result.data.contract_code` (base64-encoded Python contract source)
- **Local Verification Script**: `node scripts/verify_source.js`
- **Result**: The decoded on-chain source text matches the local repository source files byte-for-byte, producing identical SHA-256 fingerprints:
  - `SourceDriftLedger.py`: `e3b4bf9ce11e5f418126585820916f442bd22f23610bbfdb3a3de8065eeb3bd8`
  - `ClaimsBoard.py`: `3fc42682eebb7522edb5d0039969fea0232456596a37eda9f1ce698639ee3a10`

### 2. Leader Execution & Revert Payload Decoding
For both accepted and reverted transactions on GenLayer Studionet:
- **Receipt Field**: `result.consensus_data.leader_receipt[0].result`
- **Encoding**: Base64-encoded buffer.
- **Decoding**: Byte 0 indicates the result code (`ResultCode.RETURN` or `ResultCode.USER_ERROR`), followed by UTF-8 bytes containing the user error message.
- Every negative test in the canonical suite was confirmed by decoding this exact buffer from the on-chain receipt.

### 3. Deployed Contract Addresses
- **SourceDriftLedger (Main)**:
  - Address: `0x0d24CC10b5396C718c019E239c90c7eE6b17BE57`
  - Deploy Transaction: `0x8058288116cb78df58dd1c5dd1a84383ac8bc6ea3ca1b3bd06b81f2beb40d874`
  - Status: `ACCEPTED`, Consensus: `MAJORITY_AGREE` (3 agree / 5 nodes)
- **ClaimsBoard (Consumer)**:
  - Address: `0x76Ef8E906c8Fec113c4Db846e60196E58e6B818D`
  - Deploy Transaction: `0x4865176578ebf2b800c5fe61ca75a0bcafddf8f6464bb8ace32b2134824fc04c`
  - Status: `ACCEPTED`, Consensus: `MAJORITY_AGREE` (3 agree / 5 nodes)
- **Connection Transaction (`set_ledger`)**:
  - Tx Hash: `0x02f91c5c28318f6e330d27332181b7bc38bffd96a9fa2cdf2f882727e51cddcd`
  - Status: `ACCEPTED`, Consensus: `MAJORITY_AGREE`
