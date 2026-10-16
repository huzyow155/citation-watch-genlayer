const dns = require('dns');
dns.setDefaultResultOrder('ipv4first');

const { createClient, chains, createAccount } = require('genlayer-js');
const fs = require('fs');
const path = require('path');

const RPC_URL = "https://studio.genlayer.com/api";

async function getTxDetails(hash) {
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
  return json.result;
}

async function waitTx(client, hash) {
  for (let i = 0; i < 90; i++) {
    try {
      const tx = await getTxDetails(hash);
      if (tx && (tx.status === 'ACCEPTED' || tx.status === 'FINALIZED' || tx.result_name === 'MAJORITY_DISAGREE')) {
        return tx;
      }
    } catch (e) {}
    await new Promise(r => setTimeout(r, 3000));
  }
  throw new Error("Timeout waiting for tx: " + hash);
}

async function executeTx(client, targetAddr, fnName, args, label) {
  const t0 = Date.now();
  console.log(`\n>>> [${label}] Calling ${fnName}...`);
  const txHash = await client.writeContract({
    address: targetAddr,
    functionName: fnName,
    args: args,
  });
  console.log(`    Tx sent: ${txHash}`);
  const tx = await waitTx(client, txHash);
  const dur = ((Date.now() - t0) / 1000).toFixed(2);
  const votes = tx.consensus_data?.votes || {};
  const agree = Object.values(votes).filter(v => v === 'agree').length;
  const total = Object.values(votes).length;
  console.log(`    Done in ${dur}s | Status: ${tx.status} | Result: ${tx.result_name} | Agree: ${agree}/${total}`);
  return {
    txHash,
    durationSec: parseFloat(dur),
    status: tx.status,
    result: tx.result_name,
    agree,
    total,
    votes,
    rawTx: tx,
  };
}

async function main() {
  const deployments = JSON.parse(fs.readFileSync(path.join(__dirname, 'deployments.json'), 'utf8'));
  const statusEqualityAddr = deployments.ledger.contractAddress; // v1.2.0
  const groundingOnlyAddr = "0xc6a8Cfdbbb4CA98637053A0c8529686Ff4C41CaD"; // v1.1.0

  console.log("==================================================================");
  console.log("RUNNING VALIDATOR-SIDE CLASSIFICATION BENCHMARK ON STUDIONET");
  console.log("Validator A (Status-Equality, v1.2.0):", statusEqualityAddr);
  console.log("Validator B (Grounding-Only, v1.1.0):  ", groundingOnlyAddr);
  console.log("==================================================================");

  const account = createAccount();
  const client = createClient({
    chain: chains.studionet,
    account: account,
  });

  const cosmeticBaseUrl = "https://en.wikipedia.org/w/index.php?title=Computing&oldid=1375087113";
  const cosmeticQuote = "Software is also sometimes used in a more narrow sense, meaning application software only.";
  const cosmeticTargetUrl = "https://en.wikipedia.org/w/index.php?title=Computing&oldid=1380219262";

  const materialBaseUrl = "https://en.wikipedia.org/w/index.php?title=Python_(programming_language)&oldid=1378728329";
  const materialQuote = "the Python Software Foundation supports Python 3.11, 3.12, 3.13, and 3.14, following the project's annual release cycle and five-year support policy.";
  const materialTargetUrl = "https://en.wikipedia.org/w/index.php?title=Python_(programming_language)&oldid=1379380903";

  const results = {
    recordedAt: new Date().toISOString(),
    statusEqualityAddress: statusEqualityAddr,
    groundingOnlyAddress: groundingOnlyAddr,
    cosmetic: { statusEquality: [], groundingOnly: [] },
    material: { statusEquality: [], groundingOnly: [] },
  };

  // Helper to run 3 runs of a scenario on a given contract
  async function runScenario(contractAddr, validatorType, scenarioType, labelPrefix, baseUrl, quote, targetUrl, targetArray) {
    for (let run = 1; run <= 3; run++) {
      const regLabel = `${labelPrefix} ${validatorType} R${run} ${Date.now().toString().slice(-4)}`;
      const regRes = await executeTx(
        client,
        contractAddr,
        'register_citation',
        [regLabel, baseUrl, JSON.stringify([quote])],
        `Reg ${regLabel}`
      );

      const rawCids = await client.readContract({
        address: contractAddr,
        functionName: 'list_citation_ids',
        args: [0, 10],
      });
      const cid = JSON.parse(rawCids)[0];

      const auditRes = await executeTx(
        client,
        contractAddr,
        'audit_citation',
        [cid, targetUrl],
        `Audit ${regLabel}`
      );

      const record = JSON.parse(await client.readContract({
        address: contractAddr,
        functionName: 'get_citation',
        args: [cid],
      }));

      const auditClass = record.audits[0]?.class || "UNKNOWN";
      console.log(`    Class decided: ${auditClass}`);

      targetArray.push({
        run,
        citationId: cid,
        registerTx: regRes.txHash,
        auditTx: auditRes.txHash,
        durationSec: auditRes.durationSec,
        status: auditRes.status,
        result: auditRes.result,
        agreeCount: auditRes.agree,
        totalVotes: auditRes.total,
        auditClass,
      });
    }
  }

  // 1. Run Status-Equality Validator (v1.2.0)
  console.log("\n=======================================================");
  console.log("BENCHMARK 1: Status-Equality Validator (COSMETIC 3x)");
  console.log("=======================================================");
  await runScenario(statusEqualityAddr, "Status-Equality", "COSMETIC", "BenchCosmetic", cosmeticBaseUrl, cosmeticQuote, cosmeticTargetUrl, results.cosmetic.statusEquality);

  console.log("\n=======================================================");
  console.log("BENCHMARK 2: Status-Equality Validator (MATERIAL 3x)");
  console.log("=======================================================");
  await runScenario(statusEqualityAddr, "Status-Equality", "MATERIAL", "BenchMaterial", materialBaseUrl, materialQuote, materialTargetUrl, results.material.statusEquality);

  // 2. Run Grounding-Only Validator (v1.1.0)
  console.log("\n=======================================================");
  console.log("BENCHMARK 3: Grounding-Only Validator (COSMETIC 3x)");
  console.log("=======================================================");
  await runScenario(groundingOnlyAddr, "Grounding-Only", "COSMETIC", "BenchCosmeticGO", cosmeticBaseUrl, cosmeticQuote, cosmeticTargetUrl, results.cosmetic.groundingOnly);

  console.log("\n=======================================================");
  console.log("BENCHMARK 4: Grounding-Only Validator (MATERIAL 3x)");
  console.log("=======================================================");
  await runScenario(groundingOnlyAddr, "Grounding-Only", "MATERIAL", "BenchMaterialGO", materialBaseUrl, materialQuote, materialTargetUrl, results.material.groundingOnly);

  const outPath = path.join(__dirname, 'benchmark_results.json');
  fs.writeFileSync(outPath, JSON.stringify(results, null, 2));
  console.log(`\n=======================================================`);
  console.log(`BENCHMARK COMPLETE! Saved to ${outPath}`);
  console.log(`=======================================================`);
}

main().catch(err => {
  console.error("Benchmark failed:", err);
  process.exit(1);
});
