const dns = require('dns');
dns.setDefaultResultOrder('ipv4first');

const { createClient, chains, createAccount } = require('genlayer-js');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const RPC_URL = "https://studio.genlayer.com/api";

async function waitReceiptWithRetry(hash, maxRetries = 60, intervalMs = 3000) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const res = await fetch(RPC_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jsonrpc: '2.0',
          id: 1,
          method: 'eth_getTransactionByHash',
          params: [hash],
        }),
      });
      const text = await res.text();
      try {
        const json = JSON.parse(text);
        const tx = json.result;
        if (tx && (tx.status === 'ACCEPTED' || tx.status === 'FINALIZED')) {
          return tx;
        }
      } catch (parseErr) {
        // HTML error (502/504), ignore and retry
      }
    } catch (e) {
      // network glitch, ignore and retry
    }
    await new Promise(r => setTimeout(r, intervalMs));
  }
  throw new Error(`Timeout waiting for tx receipt: ${hash}`);
}

async function main() {
  const account = createAccount();
  console.log("Using throwaway account for deployment:", account.address);

  const client = createClient({
    chain: chains.studionet,
    account: account,
  });

  const ledgerCodePath = path.join(__dirname, '../../contracts/SourceDriftLedger.py');
  const ledgerCode = fs.readFileSync(ledgerCodePath, 'utf8');
  const ledgerSha256 = crypto.createHash('sha256').update(ledgerCode, 'utf8').digest('hex');
  console.log("SourceDriftLedger source SHA-256:", ledgerSha256);

  const boardCodePath = path.join(__dirname, '../../contracts/ClaimsBoard.py');
  const boardCode = fs.readFileSync(boardCodePath, 'utf8');
  const boardSha256 = crypto.createHash('sha256').update(boardCode, 'utf8').digest('hex');
  console.log("ClaimsBoard source SHA-256:", boardSha256);

  // 1. Deploy SourceDriftLedger
  console.log("\n=======================================================");
  console.log("DEPLOYING SOURCEDRIFTLEDGER (MAIN) CONTRACT");
  console.log("=======================================================");
  const t0 = Date.now();
  const ledgerDeployTxHash = await client.deployContract({
    code: ledgerCode,
    args: [],
  });
  console.log("SourceDriftLedger Deploy Tx Hash:", ledgerDeployTxHash);

  const ledgerTx = await waitReceiptWithRetry(ledgerDeployTxHash);
  const ledgerElapsed = ((Date.now() - t0) / 1000).toFixed(2);
  console.log(`SourceDriftLedger deployed in ${ledgerElapsed}s`);
  console.log("Status:", ledgerTx.status, "Result:", ledgerTx.result_name);
  const ledgerAddress = ledgerTx.recipient;
  console.log("SourceDriftLedger Address:", ledgerAddress);

  if (!ledgerAddress) {
    throw new Error("No contract address returned for SourceDriftLedger");
  }

  // 2. Deploy ClaimsBoard
  console.log("\n=======================================================");
  console.log("DEPLOYING CLAIMSBOARD (CONSUMER) CONTRACT");
  console.log("=======================================================");
  const t1 = Date.now();
  const boardDeployTxHash = await client.deployContract({
    code: boardCode,
    args: [],
  });
  console.log("ClaimsBoard Deploy Tx Hash:", boardDeployTxHash);

  const boardTx = await waitReceiptWithRetry(boardDeployTxHash);
  const boardElapsed = ((Date.now() - t1) / 1000).toFixed(2);
  console.log(`ClaimsBoard deployed in ${boardElapsed}s`);
  console.log("Status:", boardTx.status, "Result:", boardTx.result_name);
  const boardAddress = boardTx.recipient;
  console.log("ClaimsBoard Address:", boardAddress);

  if (!boardAddress) {
    throw new Error("No contract address returned for ClaimsBoard");
  }

  // 3. Connect ClaimsBoard to SourceDriftLedger
  console.log("\n=======================================================");
  console.log("CONNECTING CLAIMSBOARD TO SOURCEDRIFTLEDGER (SET_LEDGER)");
  console.log("=======================================================");
  const setLedgerTxHash = await client.writeContract({
    address: boardAddress,
    functionName: 'set_ledger',
    args: [ledgerAddress],
  });
  console.log("set_ledger Tx Hash:", setLedgerTxHash);

  const setLedgerTx = await waitReceiptWithRetry(setLedgerTxHash);
  console.log("set_ledger Status:", setLedgerTx.status, "Result:", setLedgerTx.result_name);

  // Read back configured ledger address from ClaimsBoard
  const configuredLedger = await client.readContract({
    address: boardAddress,
    functionName: 'get_ledger_address',
    args: [],
  });
  console.log("Verified configured ledger on ClaimsBoard:", configuredLedger);

  const outDir = path.join(__dirname);
  const outPath = path.join(outDir, 'deployments.json');
  let superseded = [];
  if (fs.existsSync(outPath)) {
    try {
      const prev = JSON.parse(fs.readFileSync(outPath, 'utf8'));
      superseded = prev.supersededDeployments || [];
      if (prev.ledger && prev.claimsBoard) {
        superseded.push({
          archivedAt: new Date().toISOString(),
          version: prev.ledger.contractAddress === "0x0d24CC10b5396C718c019E239c90c7eE6b17BE57" ? "1.0.0" : "1.1.0-pre",
          reason: "Superseded by v1.1.0 (consensus payload, model-layer evidence, and spawn_sandbox fixes)",
          ledger: prev.ledger,
          claimsBoard: prev.claimsBoard,
        });
      }
    } catch (e) {
      console.warn("Could not read previous deployments.json:", e);
    }
  }

  const deployments = {
    network: "GenLayer Studionet (Preview)",
    chainId: 61999,
    rpc: RPC_URL,
    explorerBase: "https://explorer-studio.genlayer.com",
    deployerAddress: account.address,
    ledger: {
      contractAddress: ledgerAddress,
      deployTxHash: ledgerDeployTxHash,
      deployStatus: ledgerTx.status,
      consensusResult: ledgerTx.result_name,
      sourceFile: "contracts/SourceDriftLedger.py",
      sourceSha256: ledgerSha256,
      explorerUrl: `https://explorer-studio.genlayer.com/address/${ledgerAddress}`,
      consensus_data: ledgerTx.consensus_data,
    },
    claimsBoard: {
      contractAddress: boardAddress,
      deployTxHash: boardDeployTxHash,
      deployStatus: boardTx.status,
      consensusResult: boardTx.result_name,
      sourceFile: "contracts/ClaimsBoard.py",
      sourceSha256: boardSha256,
      explorerUrl: `https://explorer-studio.genlayer.com/address/${boardAddress}`,
      setLedgerTxHash: setLedgerTxHash,
      setLedgerStatus: setLedgerTx.status,
      consensus_data: boardTx.consensus_data,
    },
    supersededDeployments: superseded,
  };

  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }
  fs.writeFileSync(outPath, JSON.stringify(deployments, null, 2));
  console.log(`\nDeployment records saved to ${outPath}`);
}

main().catch(err => {
  console.error("Deploy failed:", err);
  process.exit(1);
});
