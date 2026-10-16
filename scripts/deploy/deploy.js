const dns = require('dns');
dns.setDefaultResultOrder('ipv4first');

const { createClient, chains, createAccount } = require('genlayer-js');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

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

  const ledgerReceipt = await client.waitForTransactionReceipt({
    hash: ledgerDeployTxHash,
    retries: 120,
    interval: 3000,
  });
  const ledgerElapsed = ((Date.now() - t0) / 1000).toFixed(2);
  console.log(`SourceDriftLedger deployed in ${ledgerElapsed}s`);
  console.log("Status:", ledgerReceipt.status_name, "Result:", ledgerReceipt.result_name);
  const ledgerAddress = ledgerReceipt.recipient;
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

  const boardReceipt = await client.waitForTransactionReceipt({
    hash: boardDeployTxHash,
    retries: 120,
    interval: 3000,
  });
  const boardElapsed = ((Date.now() - t1) / 1000).toFixed(2);
  console.log(`ClaimsBoard deployed in ${boardElapsed}s`);
  console.log("Status:", boardReceipt.status_name, "Result:", boardReceipt.result_name);
  const boardAddress = boardReceipt.recipient;
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

  const setLedgerReceipt = await client.waitForTransactionReceipt({
    hash: setLedgerTxHash,
    retries: 120,
    interval: 3000,
  });
  console.log("set_ledger Status:", setLedgerReceipt.status_name, "Result:", setLedgerReceipt.result_name);

  // Read back configured ledger address from ClaimsBoard
  const configuredLedger = await client.readContract({
    address: boardAddress,
    functionName: 'get_ledger_address',
    args: [],
  });
  console.log("Verified configured ledger on ClaimsBoard:", configuredLedger);

  const deployments = {
    network: "GenLayer Studionet (Preview)",
    chainId: 61999,
    rpc: "https://studio.genlayer.com/api",
    explorerBase: "https://explorer-studio.genlayer.com",
    deployerAddress: account.address,
    ledger: {
      contractAddress: ledgerAddress,
      deployTxHash: ledgerDeployTxHash,
      deployStatus: ledgerReceipt.status_name,
      consensusResult: ledgerReceipt.result_name,
      sourceFile: "contracts/SourceDriftLedger.py",
      sourceSha256: ledgerSha256,
      explorerUrl: `https://explorer-studio.genlayer.com/address/${ledgerAddress}`,
      consensus_data: ledgerReceipt.consensus_data,
    },
    claimsBoard: {
      contractAddress: boardAddress,
      deployTxHash: boardDeployTxHash,
      deployStatus: boardReceipt.status_name,
      consensusResult: boardReceipt.result_name,
      sourceFile: "contracts/ClaimsBoard.py",
      sourceSha256: boardSha256,
      explorerUrl: `https://explorer-studio.genlayer.com/address/${boardAddress}`,
      setLedgerTxHash: setLedgerTxHash,
      setLedgerStatus: setLedgerReceipt.status_name,
      consensus_data: boardReceipt.consensus_data,
    },
    supersededDeployments: []
  };

  const outDir = path.join(__dirname);
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir, { recursive: true });
  }
  const outPath = path.join(outDir, 'deployments.json');
  fs.writeFileSync(outPath, JSON.stringify(deployments, null, 2));
  console.log(`\nDeployment records saved to ${outPath}`);
}

main().catch(err => {
  console.error("Deploy failed:", err);
  process.exit(1);
});
