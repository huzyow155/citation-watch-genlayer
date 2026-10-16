const dns = require('dns');
dns.setDefaultResultOrder('ipv4first');

const { createClient, chains, createAccount } = require('genlayer-js');
const fs = require('fs');
const path = require('path');

async function main() {
  const account = createAccount();
  console.log("Auditor account:", account.address);

  const client = createClient({
    chain: chains.studionet,
    account: account,
  });

  const code = fs.readFileSync(path.join(__dirname, '../../contracts/Probe2.py'), 'utf8');
  console.log("Deploying Probe2...");
  const deployHash = await client.deployContract({ code, args: [] });
  console.log("Deploy hash:", deployHash);

  const receipt = await client.waitForTransactionReceipt({ hash: deployHash, retries: 40, interval: 3000 });
  console.log("Deployed address:", receipt.recipient, "Status:", receipt.status_name, "Result:", receipt.result_name);

  if (!receipt.recipient) return;

  console.log("Calling test_spawn_in_validator...");
  const callHash = await client.writeContract({
    address: receipt.recipient,
    functionName: 'test_spawn_in_validator',
    args: ['https://en.wikipedia.org/wiki/Alan_Turing'],
  });
  console.log("Call hash:", callHash);

  const callReceipt = await client.waitForTransactionReceipt({ hash: callHash, retries: 40, interval: 3000 });
  console.log("Call finished:", callReceipt.status_name, "Result:", callReceipt.result_name);

  const res = await client.readContract({
    address: receipt.recipient,
    functionName: 'get_res',
    args: [],
  });
  console.log("Result value:", res);
}

main().catch(console.error);
