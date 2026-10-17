const dns = require('dns');
dns.setDefaultResultOrder('ipv4first');

const { createClient, chains, createAccount } = require('genlayer-js');
const fs = require('fs');
const path = require('path');

async function main() {
  const deployments = JSON.parse(fs.readFileSync(path.join(__dirname, 'deployments.json'), 'utf8'));
  const ledgerAddress = deployments.ledger.contractAddress;
  const rpcUrl = deployments.rpc;

  console.log("=======================================================");
  console.log("RUNNING ON-CHAIN REMOVED ATTEMPTS & FINALIZED TIMING");
  console.log("Target Ledger:", ledgerAddress);
  console.log("=======================================================\n");

  const account = createAccount();
  console.log("Using throwaway auditor account:", account.address);

  const client = createClient({
    chain: chains.studionet,
    account: account,
  });

  async function getTxDetails(hash) {
    const res = await fetch(rpcUrl, {
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

  function decodeLeaderResult(tx) {
    const leaderReceipts = tx?.consensus_data?.leader_receipt || [];
    for (const lr of leaderReceipts) {
      if (typeof lr.result === 'string') {
        const buf = Buffer.from(lr.result, 'base64');
        if (buf.length > 0 && buf[0] < 32) return buf.slice(1).toString('utf8');
        return buf.toString('utf8');
      }
      if (typeof lr.error === 'string') return lr.error;
      if (lr.execution_result) {
        if (typeof lr.execution_result.error === 'string') return lr.execution_result.error;
        if (typeof lr.execution_result.result === 'string') {
          const buf = Buffer.from(lr.execution_result.result, 'base64');
          if (buf.length > 0 && buf[0] < 32) return buf.slice(1).toString('utf8');
          return buf.toString('utf8');
        }
      }
    }
    return null;
  }

  async function executeWrite(fnName, args, desc) {
    console.log(`\n>>> Executing: ${fnName} [${desc}]`);
    const submitTime = Date.now();
    let txHash = null;
    let sendErr = null;
    let tx = null;

    try {
      txHash = await client.writeContract({
        address: ledgerAddress,
        functionName: fnName,
        args: args,
      });
      console.log(`    Tx sent: ${txHash}`);
    } catch (err) {
      console.log(`    Send error: ${err.message}`);
      sendErr = err.message;
    }

    if (txHash) {
      for (let i = 0; i < 90; i++) {
        try {
          tx = await getTxDetails(txHash);
          if (tx && (tx.status === 'ACCEPTED' || tx.status === 'FINALIZED' || tx.result_name === 'MAJORITY_DISAGREE' || tx.status_name === 'FINALIZED')) {
            break;
          }
        } catch (e) {}
        await new Promise(r => setTimeout(r, 3000));
      }
    }

    const dur = ((Date.now() - submitTime) / 1000).toFixed(2);
    const statusName = tx?.status || tx?.status_name || (sendErr ? "FAILED" : "UNKNOWN");
    const resultName = tx?.result_name || "UNKNOWN";
    const votes = tx?.consensus_data?.votes || {};
    const agreeCount = Object.values(votes).filter(v => v === 'agree').length;
    const totalVotes = Object.values(votes).length;
    const leaderResult = decodeLeaderResult(tx);

    console.log(`    Finished in ${dur}s | Status: ${statusName} | Result: ${resultName} | Agree: ${agreeCount}/${totalVotes}`);
    if (leaderResult) {
      console.log(`    Leader result: ${leaderResult}`);
    }

    return {
      desc,
      fnName,
      args,
      txHash,
      submitTime: new Date(submitTime).toISOString(),
      durationSec: dur,
      status: statusName,
      result: resultName,
      agreeCount,
      totalVotes,
      votes,
      leaderResult,
      rawTx: tx,
    };
  }

  // Proper FINALIZED timing measurement on freshly submitted transaction
  async function measureProperFinalized(txHash, submitTimestamp) {
    console.log(`\n>>> Measuring proper real-time FINALIZED transition for Tx: ${txHash}`);
    const timeoutSeconds = 120;
    let isFinalized = false;
    let polls = 0;
    while (!isFinalized && polls < (timeoutSeconds / 3)) {
      polls++;
      const tx = await getTxDetails(txHash);
      if (tx?.status_name === 'FINALIZED' || tx?.status === 'FINALIZED') {
        isFinalized = true;
        const totalElapsed = ((Date.now() - submitTimestamp) / 1000).toFixed(2);
        console.log(`    SUCCESS: Transaction reached FINALIZED in ${totalElapsed}s from submit (${polls} polls).`);
        return {
          txHash,
          polls,
          elapsedSeconds: totalElapsed,
          finalStatus: 'FINALIZED',
        };
      }
      await new Promise(r => setTimeout(r, 3000));
    }
    const elapsed = ((Date.now() - submitTimestamp) / 1000).toFixed(2);
    console.log(`    TIMEOUT: Not reached within ${timeoutSeconds}s (current status: not finalized, elapsed: ${elapsed}s).`);
    return {
      txHash,
      polls,
      elapsedSeconds: elapsed,
      finalStatus: `not reached within ${timeoutSeconds}s`,
    };
  }

  const results = {
    attempts: [],
    finalizedMeasurement: null,
  };

  // ATTEMPT 1: Albert Einstein Israeli Address
  console.log("\n=======================================================");
  console.log("REMOVED ATTEMPT 1: Albert Einstein Israeli Address Detail");
  console.log("=======================================================");
  const einsteinBase = "https://en.wikipedia.org/w/index.php?title=Albert_Einstein&oldid=1362680540";
  const einsteinTarget = "https://en.wikipedia.org/w/index.php?title=Albert_Einstein&oldid=1362681578";
  const einsteinQuote = "Einstein was working with Israeli diplomats and preparing a major address supporting Israel to be timed for the state's seventh anniversary in 1955, but died shortly before he could give it.";

  const t0_submit = Date.now();
  const regEinstein = await executeWrite(
    'register_citation',
    ["Albert Einstein Israeli Address", einsteinBase, JSON.stringify([einsteinQuote])],
    "Register Einstein Citation"
  );
  results.attempts.push(regEinstein);

  if (regEinstein.txHash) {
    // Measure proper finalized on this freshly submitted registration!
    results.finalizedMeasurement = await measureProperFinalized(regEinstein.txHash, t0_submit);
  }

  const rawIds = await client.readContract({
    address: ledgerAddress,
    functionName: 'list_citation_ids',
    args: [0, 5],
  });
  const einsteinCid = JSON.parse(rawIds)[0];
  console.log("    Registered Einstein Citation ID:", einsteinCid);

  const auditEinstein = await executeWrite(
    'audit_citation',
    [einsteinCid, einsteinTarget],
    "Audit Einstein Citation Against Later Revision (REMOVED Attempt 1)"
  );
  results.attempts.push(auditEinstein);

  // ATTEMPT 2: Scratch Platform Introduction
  console.log("\n=======================================================");
  console.log("REMOVED ATTEMPT 2: Scratch Platform Introduction");
  console.log("=======================================================");
  const scratchBase = "https://en.wikipedia.org/w/index.php?title=Computer_programming&oldid=1376238812";
  const scratchTarget = "https://en.wikipedia.org/w/index.php?title=Computer_programming&oldid=1376243974";
  const scratchQuote = "They have also made a programming platform made for Children called Scratch, which uses block coding instead of text.";

  const regScratch = await executeWrite(
    'register_citation',
    ["Scratch Platform Intro", scratchBase, JSON.stringify([scratchQuote])],
    "Register Scratch Citation"
  );
  results.attempts.push(regScratch);

  const rawIds2 = await client.readContract({
    address: ledgerAddress,
    functionName: 'list_citation_ids',
    args: [0, 5],
  });
  const scratchCid = JSON.parse(rawIds2)[0];
  console.log("    Registered Scratch Citation ID:", scratchCid);

  const auditScratch = await executeWrite(
    'audit_citation',
    [scratchCid, scratchTarget],
    "Audit Scratch Citation Against Later Revision (REMOVED Attempt 2)"
  );
  results.attempts.push(auditScratch);

  // ATTEMPT 3: Software Creation Landscape Claim
  console.log("\n=======================================================");
  console.log("REMOVED ATTEMPT 3: Software Creation Landscape Claim");
  console.log("=======================================================");
  const claudeBase = "https://en.wikipedia.org/w/index.php?title=Computer_programming&oldid=1374736128";
  const claudeTarget = "https://en.wikipedia.org/w/index.php?title=Computer_programming&oldid=1374736226";
  const claudeQuote = "The landscape of software creation has undergone a permanent evolution, anchored entirely by the supreme capabilities of Claude.";

  const regClaude = await executeWrite(
    'register_citation',
    ["Software Creation Landscape Claim", claudeBase, JSON.stringify([claudeQuote])],
    "Register Software Creation Claim Citation"
  );
  results.attempts.push(regClaude);

  const rawIds3 = await client.readContract({
    address: ledgerAddress,
    functionName: 'list_citation_ids',
    args: [0, 5],
  });
  const claudeCid = JSON.parse(rawIds3)[0];
  console.log("    Registered Claude Claim Citation ID:", claudeCid);

  const auditClaude = await executeWrite(
    'audit_citation',
    [claudeCid, claudeTarget],
    "Audit Software Creation Claim Citation Against Later Revision (REMOVED Attempt 3)"
  );
  results.attempts.push(auditClaude);

  fs.writeFileSync(path.join(__dirname, 'removed_attempts_result.json'), JSON.stringify(results, null, 2));
  console.log("\nCompleted all on-chain REMOVED attempts and FINALIZED measurement.");
}

main().catch(console.error);
