const dns = require('dns');
dns.setDefaultResultOrder('ipv4first');

const { createClient, chains, createAccount } = require('genlayer-js');
const fs = require('fs');
const path = require('path');

const RPC_URL = "https://studio.genlayer.com/api";

async function waitReceipt(hash) {
  for (let i = 0; i < 60; i++) {
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
      const json = await res.json();
      const tx = json.result;
      if (tx && (tx.status === 'ACCEPTED' || tx.status === 'FINALIZED' || tx.result_name === 'MAJORITY_DISAGREE')) {
        return tx;
      }
    } catch (e) {}
    await new Promise(r => setTimeout(r, 3000));
  }
  throw new Error("Timeout waiting for receipt: " + hash);
}

async function main() {
  const account = createAccount();
  const client = createClient({
    chain: chains.studionet,
    account: account,
  });

  const codePath = path.join(__dirname, '../../contracts/Probe2.py');
  const code = fs.readFileSync(codePath, 'utf8');

  console.log("Deploying Probe2 contract to test validator exec_prompt on Studionet...");
  const txHash = await client.deployContract({ code: code, args: [] });
  console.log("Deploy Tx:", txHash);
  const tx = await waitReceipt(txHash);
  const addr = tx.recipient;
  console.log("Probe2 Deployed at:", addr, "Status:", tx.status, "Result:", tx.result_name);

  console.log("\nCalling test_validator_prompt on Probe2...");
  const writeTx = await client.writeContract({
    address: addr,
    functionName: 'test_validator_prompt',
    args: ["studionet_probe_hello"],
  });
  console.log("Write Tx:", writeTx);
  const writeReceipt = await waitReceipt(writeTx);
  console.log("Write Status:", writeReceipt.status, "Result:", writeReceipt.result_name);
  const votes = writeReceipt.consensus_data?.votes || {};
  console.log("Votes:", votes);

  const res = await client.readContract({
    address: addr,
    functionName: 'get_res',
    args: [],
  });
  console.log("Contract get_res result:", res);
}

main().catch(console.error);
