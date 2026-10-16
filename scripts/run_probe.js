const dns = require('dns');
dns.setDefaultResultOrder('ipv4first');

const { createClient, chains, createAccount } = require('genlayer-js');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

async function main() {
  const account = createAccount();
  console.log("Using throwaway account:", account.address);

  const client = createClient({
    chain: chains.studionet,
    account: account,
  });

  const probeCodePath = path.join(__dirname, '../contracts/Probe.py');
  const code = fs.readFileSync(probeCodePath, 'utf8');
  const codeSha256 = crypto.createHash('sha256').update(code, 'utf8').digest('hex');
  console.log("Probe contract SHA-256:", codeSha256);

  console.log("\n--- Deploying Probe Contract ---");
  const t0 = Date.now();
  const deployTxHash = await client.deployContract({
    code: code,
    args: [],
  });
  console.log("Deploy Tx Hash:", deployTxHash);

  const deployReceipt = await client.waitForTransactionReceipt({
    hash: deployTxHash,
    retries: 120,
    interval: 3000,
  });
  console.log(`Deployed in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  console.log("Status:", deployReceipt.status_name);
  console.log("Result:", deployReceipt.result_name);
  const contractAddress = deployReceipt.recipient;
  console.log("Probe Address:", contractAddress);

  if (!contractAddress) {
    throw new Error("Deploy failed, no contract address");
  }

  const results = {
    contractAddress,
    deployTxHash,
    deployReceipt: {
      status: deployReceipt.status_name,
      result: deployReceipt.result_name,
      consensus_data: deployReceipt.consensus_data,
    },
    tests: []
  };

  async function callWrite(methodName, args, desc) {
    console.log(`\n--- Running Write: ${methodName} (${desc}) ---`);
    const start = Date.now();
    const txHash = await client.writeContract({
      address: contractAddress,
      functionName: methodName,
      args: args,
    });
    console.log("Tx Hash:", txHash);
    const receipt = await client.waitForTransactionReceipt({
      hash: txHash,
      retries: 120,
      interval: 3000,
    });
    const dur = ((Date.now() - start) / 1000).toFixed(1);
    console.log(`Finished in ${dur}s. Status: ${receipt.status_name}, Result: ${receipt.result_name}`);

    let valView = null;
    try {
      valView = await client.readContract({
        address: contractAddress,
        functionName: 'get_result',
        args: [],
      });
      console.log("Contract last_probe_result:", valView);
    } catch (e) {
      console.log("Read error:", e.message);
    }

    const testEntry = {
      desc,
      method: methodName,
      args,
      txHash,
      durationSec: dur,
      status: receipt.status_name,
      result: receipt.result_name,
      consensus_data: receipt.consensus_data,
      viewResult: valView,
    };
    results.tests.push(testEntry);
    return testEntry;
  }

  // 1. Test strict_eq
  await callWrite('test_strict_eq', ['MATERIAL|e1:SAME|e2:CHANGED'], 'strict_eq test');

  // 2. Test comparative
  await callWrite('test_comparative', ['MATERIAL|e1:SAME|e2:CHANGED'], 'prompt_comparative test');

  // 3. Probe Wikipedia revision permalink
  await callWrite('probe_fetch', ['https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1380390650'], 'Wikipedia oldid permalink fetch');

  // 4. Probe Wikipedia live page
  await callWrite('probe_fetch', ['https://en.wikipedia.org/wiki/Alan_Turing'], 'Wikipedia live page fetch');

  const outPath = path.join(__dirname, 'probe_results.json');
  fs.writeFileSync(outPath, JSON.stringify(results, null, 2));
  console.log(`\nProbe results written to ${outPath}`);
}

main().catch(err => {
  console.error("Probe error:", err);
  process.exit(1);
});
