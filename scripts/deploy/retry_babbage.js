const { createClient, createAccount } = require('genlayer-js');
const fs = require('fs');
const path = require('path');

async function main() {
  const rpcUrl = "https://studio.genlayer.com/api";
  const account = createAccount();
  const client = createClient({ endpoint: rpcUrl, account: account });

  const deployments = JSON.parse(fs.readFileSync(path.join(__dirname, 'deployments.json'), 'utf8'));
  const ledgerAddress = deployments.ledger.contractAddress;
  const babbageCid = "d81f10ae72a5";
  const babbageTargetRevUrl = "https://en.wikipedia.org/w/index.php?title=Charles_Babbage&oldid=1378652484";

  console.log("Sending Babbage audit Attempt 2...");
  const txHash = await client.writeContract({
    address: ledgerAddress,
    functionName: 'audit_citation',
    args: [babbageCid, babbageTargetRevUrl],
  });
  console.log("Tx sent:", txHash);

  let tx = null;
  for (let i = 0; i < 90; i++) {
    const res = await fetch(rpcUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: 1,
        method: 'eth_getTransactionByHash',
        params: [txHash],
      }),
    });
    const j = await res.json();
    tx = j.result;
    if (tx && (tx.status === 'ACCEPTED' || tx.status === 'FINALIZED' || tx.result_name === 'MAJORITY_DISAGREE')) {
      break;
    }
    await new Promise(r => setTimeout(r, 3000));
  }

  const votes = tx?.consensus_data?.votes || {};
  const agreeCount = Object.values(votes).filter(v => v === 'agree').length;
  const totalVotes = Object.values(votes).length;
  let leaderResult = null;
  const leaderReceipts = tx?.consensus_data?.leader_receipt || [];
  for (const lr of leaderReceipts) {
    if (typeof lr.result === 'string') {
      const buf = Buffer.from(lr.result, 'base64');
      leaderResult = buf.slice(1).toString('utf8');
      break;
    }
  }

  console.log("Status:", tx?.status || tx?.status_name);
  console.log("Result:", tx?.result_name);
  console.log(`Agree: ${agreeCount}/${totalVotes}`);
  console.log("Leader result:", leaderResult);

  // Update live_evidence.json
  const evidencePath = path.join(__dirname, 'live_evidence.json');
  const evidence = JSON.parse(fs.readFileSync(evidencePath, 'utf8'));
  evidence.attempts.push({
    desc: "Audit Charles Babbage Against Later Revision (REMOVED) - Attempt 2",
    fnName: "audit_citation",
    args: [babbageCid, babbageTargetRevUrl],
    txHash: txHash,
    status: tx?.status || tx?.status_name,
    result: tx?.result_name,
    agreeCount,
    totalVotes,
    votes,
    leaderResult,
    rawTx: tx,
    timestamp: new Date().toISOString(),
  });

  const babbageStatus = await client.readContract({
    address: ledgerAddress,
    functionName: 'get_status',
    args: [babbageCid],
  });
  console.log("Updated Babbage status string:", babbageStatus);

  if (leaderResult && !leaderResult.startsWith("FAIL") && !leaderResult.includes("Error") && !leaderResult.includes("invalid")) {
    const babbageRecord = JSON.parse(await client.readContract({
      address: ledgerAddress,
      functionName: 'get_citation',
      args: [babbageCid],
    }));
    evidence.cases.scenario_removed = {
      title: "Scenario 5: REMOVED Drift Audit (Deleted Statement Verified Absent)",
      citationId: babbageCid,
      registerTx: "0x99703fdadcef1140ee59103f9d6de1de0160282452462d4bf254be58ef8c2faa",
      registerAgree: "3/5",
      auditTx: txHash,
      auditAgree: `${agreeCount}/${totalVotes}`,
      baselineUrl: "https://en.wikipedia.org/w/index.php?title=Charles_Babbage&oldid=1378651841",
      targetUrl: babbageTargetRevUrl,
      targetKind: "REVISION",
      targetOldid: "1378652484",
      auditClass: babbageRecord.audits[0]?.class,
      coverage: babbageRecord.audits[0]?.coverage,
      finalStatus: babbageRecord.status,
      statusString: babbageStatus,
      record: babbageRecord,
    };
  }

  fs.writeFileSync(evidencePath, JSON.stringify(evidence, null, 2));
  console.log("Updated live_evidence.json with Attempt 2.");
}

main().catch(console.error);
