const dns = require('dns');
dns.setDefaultResultOrder('ipv4first');

const { createClient, chains, createAccount } = require('genlayer-js');
const fs = require('fs');
const path = require('path');

async function main() {
  const deploymentsPath = path.join(__dirname, 'deployments.json');
  const deployments = JSON.parse(fs.readFileSync(deploymentsPath, 'utf8'));

  const ledgerAddress = deployments.ledger.contractAddress;
  const boardAddress = deployments.claimsBoard.contractAddress;
  const rpcUrl = deployments.rpc;

  console.log("=======================================================");
  console.log("RUNNING CITATIONWATCH v1.1.0 ON-CHAIN EVIDENCE SUITE");
  console.log("Network:                 GenLayer Studionet (Preview)");
  console.log("Chain ID:                61999");
  console.log("SourceDriftLedger (Main):", ledgerAddress);
  console.log("ClaimsBoard (Consumer):  ", boardAddress);
  console.log("RPC Endpoint:            ", rpcUrl);
  console.log("=======================================================\n");

  const account = createAccount();
  console.log("Using throwaway auditor account:", account.address);

  const client = createClient({
    chain: chains.studionet,
    account: account,
  });

  const evidence = {
    network: "GenLayer Studionet (Preview)",
    chainId: 61999,
    rpc: rpcUrl,
    version: "1.1.0",
    ledgerAddress: ledgerAddress,
    claimsBoardAddress: boardAddress,
    ledgerDeployTxHash: deployments.ledger.deployTxHash,
    claimsBoardDeployTxHash: deployments.claimsBoard.deployTxHash,
    setLedgerTxHash: deployments.claimsBoard.setLedgerTxHash,
    recordedAt: new Date().toISOString(),
    attempts: [],
    cases: {},
    negativeTests: {},
    finalizedMeasurement: null,
  };

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
        return buf.slice(1).toString('utf8');
      }
    }
    return null;
  }

  async function executeWrite(targetAddr, fnName, args, desc) {
    console.log(`\n>>> Executing: ${fnName} [${desc}]`);
    const t0 = Date.now();
    let txHash = null;
    let receipt = null;
    let sendErr = null;

    try {
      txHash = await client.writeContract({
        address: targetAddr,
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
        } catch (e) {
          // ignore transient fetch error
        }
        await new Promise(r => setTimeout(r, 3000));
      }
    }

    const dur = ((Date.now() - t0) / 1000).toFixed(2);
    const statusName = tx?.status || tx?.status_name || (sendErr ? "FAILED" : "UNKNOWN");
    const resultName = tx?.result_name || "UNKNOWN";
    const votes = tx?.consensus_data?.votes || {};
    const agreeCount = Object.values(votes).filter(v => v === 'agree').length;
    const totalVotes = Object.values(votes).length;
    const leaderResult = decodeLeaderResult(tx);

    console.log(`    Finished in ${dur}s | Status: ${statusName} | Result: ${resultName} | Agree: ${agreeCount}/${totalVotes}`);
    if (leaderResult) {
      const displayLeader = leaderResult.length > 200 ? leaderResult.slice(0, 200) + '...' : leaderResult;
      console.log(`    Leader result: ${displayLeader}`);
    }

    const attemptRecord = {
      desc,
      fnName,
      args,
      txHash,
      durationSec: dur,
      status: statusName,
      result: resultName,
      agreeCount,
      totalVotes,
      votes,
      leaderResult,
      rawTx: tx,
      timestamp: new Date().toISOString(),
    };
    evidence.attempts.push(attemptRecord);

    return attemptRecord;
  }

  async function measureFinalized(txHash) {
    console.log(`\n>>> Measuring FINALIZED status for Tx: ${txHash}`);
    const t0 = Date.now();
    let isFinalized = false;
    let pollCount = 0;
    while (!isFinalized && pollCount < 60) {
      pollCount++;
      const tx = await getTxDetails(txHash);
      if (tx?.status_name === 'FINALIZED') {
        isFinalized = true;
        const elapsed = ((Date.now() - t0) / 1000).toFixed(2);
        console.log(`    Transaction transitioned to FINALIZED in ${elapsed}s (polls: ${pollCount})`);
        return {
          txHash,
          polls: pollCount,
          elapsedSeconds: elapsed,
          finalStatus: 'FINALIZED',
        };
      }
      await new Promise(r => setTimeout(r, 4000));
    }
    return {
      txHash,
      polls: pollCount,
      elapsedSeconds: ((Date.now() - t0) / 1000).toFixed(2),
      finalStatus: 'TIMEOUT_POLLING',
    };
  }

  // =========================================================================
  // SCENARIO 1: UNCHANGED Audit (Alan Turing)
  // =========================================================================
  console.log("\n=======================================================");
  console.log("SCENARIO 1: UNCHANGED Audit (Deterministic Verbatim Match)");
  console.log("=======================================================");
  const baseTuringUrl = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1379625434";
  const turingQuote = "In the 1940s, Turing became worried about losing his savings in the event of a German invasion.";
  const turingQuotesJson = JSON.stringify([turingQuote]);

  const regTuring = await executeWrite(
    ledgerAddress,
    'register_citation',
    ["Alan Turing Silver Savings", baseTuringUrl, turingQuotesJson],
    "Register Alan Turing Citation"
  );

  const rawMetaTuring = await client.readContract({
    address: ledgerAddress,
    functionName: 'list_citation_ids',
    args: [0, 10],
  });
  const turingCid = JSON.parse(rawMetaTuring)[0];
  console.log("    Registered Citation ID:", turingCid);

  const turingTargetRevUrl = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1380390650";
  const auditTuringUnchanged = await executeWrite(
    ledgerAddress,
    'audit_citation',
    [turingCid, turingTargetRevUrl],
    "Audit Alan Turing Against Later Revision (UNCHANGED)"
  );

  const turingRecordRev = JSON.parse(await client.readContract({
    address: ledgerAddress,
    functionName: 'get_citation',
    args: [turingCid],
  }));
  const turingStatusRev = await client.readContract({
    address: ledgerAddress,
    functionName: 'get_status',
    args: [turingCid],
  });

  evidence.cases.scenario_unchanged = {
    title: "Scenario 1: UNCHANGED Audit (Deterministic Verbatim Match)",
    citationId: turingCid,
    registerTx: regTuring.txHash,
    registerAgree: `${regTuring.agreeCount}/${regTuring.totalVotes}`,
    auditTx: auditTuringUnchanged.txHash,
    auditAgree: `${auditTuringUnchanged.agreeCount}/${auditTuringUnchanged.totalVotes}`,
    baselineUrl: baseTuringUrl,
    targetUrl: turingTargetRevUrl,
    targetKind: "REVISION",
    targetOldid: "1380390650",
    auditClass: turingRecordRev.audits[0]?.class,
    coverage: turingRecordRev.audits[0]?.coverage,
    budgetCharsUsed: turingRecordRev.audits[0]?.budget_chars_used,
    finalStatus: turingRecordRev.status,
    statusString: turingStatusRev,
    record: turingRecordRev,
  };

  // =========================================================================
  // SCENARIO 2: LIVE Audit & History (Alan Turing)
  // =========================================================================
  console.log("\n=======================================================");
  console.log("SCENARIO 2: LIVE Article Audit & Multi-Audit History (Alan Turing)");
  console.log("=======================================================");
  const turingLiveUrl = "https://en.wikipedia.org/wiki/Alan_Turing";
  const auditTuringLive = await executeWrite(
    ledgerAddress,
    'audit_citation',
    [turingCid, turingLiveUrl],
    "Audit Alan Turing Against LIVE Article (/wiki/Alan_Turing)"
  );

  const turingRecordLive = JSON.parse(await client.readContract({
    address: ledgerAddress,
    functionName: 'get_citation',
    args: [turingCid],
  }));
  const turingStatusLive = await client.readContract({
    address: ledgerAddress,
    functionName: 'get_status',
    args: [turingCid],
  });

  evidence.cases.scenario_live_and_history = {
    title: "Scenario 2: LIVE Page Audit & Multi-Audit History",
    citationId: turingCid,
    auditTx: auditTuringLive.txHash,
    auditAgree: `${auditTuringLive.agreeCount}/${auditTuringLive.totalVotes}`,
    targetUrl: turingLiveUrl,
    targetKind: "LIVE",
    auditsTotal: turingRecordLive.audits_total,
    latestAuditIndex: turingRecordLive.latest_audit_index,
    statusString: turingStatusLive,
    record: turingRecordLive,
  };

  // =========================================================================
  // SCENARIO 3: COSMETIC Drift (Computing Narrower Sense)
  // =========================================================================
  console.log("\n=======================================================");
  console.log("SCENARIO 3: COSMETIC Drift Audit (Computing Narrower Sense)");
  console.log("=======================================================");
  const baseComputingUrl = "https://en.wikipedia.org/w/index.php?title=Computing&oldid=1375087113";
  const computingQuote = "Software is also sometimes used in a more narrow sense, meaning application software only.";
  const computingQuotesJson = JSON.stringify([computingQuote]);

  const regComputing = await executeWrite(
    ledgerAddress,
    'register_citation',
    ["Computing Narrower Sense Definition", baseComputingUrl, computingQuotesJson],
    "Register Computing Citation"
  );

  const rawMetaComputing = await client.readContract({
    address: ledgerAddress,
    functionName: 'list_citation_ids',
    args: [0, 10],
  });
  const computingCid = JSON.parse(rawMetaComputing)[0];
  console.log("    Registered Computing Citation ID:", computingCid);

  const computingTargetRevUrl = "https://en.wikipedia.org/w/index.php?title=Computing&oldid=1380219262";
  const auditComputingCosmetic = await executeWrite(
    ledgerAddress,
    'audit_citation',
    [computingCid, computingTargetRevUrl],
    "Audit Computing Citation Against Later Revision (COSMETIC)"
  );

  const computingRecord = JSON.parse(await client.readContract({
    address: ledgerAddress,
    functionName: 'get_citation',
    args: [computingCid],
  }));
  const computingStatus = await client.readContract({
    address: ledgerAddress,
    functionName: 'get_status',
    args: [computingCid],
  });

  evidence.cases.scenario_cosmetic = {
    title: "Scenario 3: COSMETIC Drift Audit (Tightened Wording / Rephrased)",
    citationId: computingCid,
    registerTx: regComputing.txHash,
    registerAgree: `${regComputing.agreeCount}/${regComputing.totalVotes}`,
    auditTx: auditComputingCosmetic.txHash,
    auditAgree: `${auditComputingCosmetic.agreeCount}/${auditComputingCosmetic.totalVotes}`,
    baselineUrl: baseComputingUrl,
    targetUrl: computingTargetRevUrl,
    targetKind: "REVISION",
    targetOldid: "1380219262",
    auditClass: computingRecord.audits[0]?.class,
    coverage: computingRecord.audits[0]?.coverage,
    finalStatus: computingRecord.status,
    statusString: computingStatus,
    record: computingRecord,
  };

  // =========================================================================
  // SCENARIO 4: MATERIAL Drift (Best Picture 1967 Director/Producer)
  // =========================================================================
  console.log("\n=======================================================");
  console.log("SCENARIO 4: MATERIAL Drift Audit (Best Picture 1967 Correction)");
  console.log("=======================================================");
  const baseOscarsUrl = "https://en.wikipedia.org/w/index.php?title=Academy_Award_for_Best_Picture&oldid=1369080338";
  const oscarsQuote = "1967 In the Heat of the Night Walter Mirisch The Graduate Mike Nichols";
  const oscarsQuotesJson = JSON.stringify([oscarsQuote]);

  const regOscars = await executeWrite(
    ledgerAddress,
    'register_citation',
    ["Best Picture 1967 In the Heat of the Night", baseOscarsUrl, oscarsQuotesJson],
    "Register Oscars Citation"
  );

  const rawMetaOscars = await client.readContract({
    address: ledgerAddress,
    functionName: 'list_citation_ids',
    args: [0, 10],
  });
  const oscarsCid = JSON.parse(rawMetaOscars)[0];
  console.log("    Registered Oscars Citation ID:", oscarsCid);

  const oscarsTargetRevUrl = "https://en.wikipedia.org/w/index.php?title=Academy_Award_for_Best_Picture&oldid=1370247723";
  const auditOscarsMaterial = await executeWrite(
    ledgerAddress,
    'audit_citation',
    [oscarsCid, oscarsTargetRevUrl],
    "Audit Oscars Citation Against Later Revision (MATERIAL)"
  );

  const oscarsRecord = JSON.parse(await client.readContract({
    address: ledgerAddress,
    functionName: 'get_citation',
    args: [oscarsCid],
  }));
  const oscarsStatus = await client.readContract({
    address: ledgerAddress,
    functionName: 'get_status',
    args: [oscarsCid],
  });

  evidence.cases.scenario_material = {
    title: "Scenario 4: MATERIAL Drift Audit (Conflicting Fact / Entity Update)",
    citationId: oscarsCid,
    registerTx: regOscars.txHash,
    registerAgree: `${regOscars.agreeCount}/${regOscars.totalVotes}`,
    auditTx: auditOscarsMaterial.txHash,
    auditAgree: `${auditOscarsMaterial.agreeCount}/${auditOscarsMaterial.totalVotes}`,
    baselineUrl: baseOscarsUrl,
    targetUrl: oscarsTargetRevUrl,
    targetKind: "REVISION",
    targetOldid: "1370247723",
    auditClass: oscarsRecord.audits[0]?.class,
    coverage: oscarsRecord.audits[0]?.coverage,
    finalStatus: oscarsRecord.status,
    statusString: oscarsStatus,
    record: oscarsRecord,
  };

  // =========================================================================
  // SCENARIO 5: REMOVED (Charles Babbage Death Detail Deleted)
  // =========================================================================
  console.log("\n=======================================================");
  console.log("SCENARIO 5: REMOVED Audit (Charles Babbage Death Detail Deleted)");
  console.log("=======================================================");
  const baseBabbageUrl = "https://en.wikipedia.org/w/index.php?title=Charles_Babbage&oldid=1378651841";
  const babbageQuote = "Upon his death he halted his breathing and the beating of his heart.";
  const babbageQuotesJson = JSON.stringify([babbageQuote]);

  const regBabbage = await executeWrite(
    ledgerAddress,
    'register_citation',
    ["Charles Babbage Death Detail", baseBabbageUrl, babbageQuotesJson],
    "Register Charles Babbage Citation"
  );

  const rawMetaBabbage = await client.readContract({
    address: ledgerAddress,
    functionName: 'list_citation_ids',
    args: [0, 10],
  });
  const babbageCid = JSON.parse(rawMetaBabbage)[0];
  console.log("    Registered Charles Babbage Citation ID:", babbageCid);

  const babbageTargetRevUrl = "https://en.wikipedia.org/w/index.php?title=Charles_Babbage&oldid=1378652484";
  const auditBabbageRemoved = await executeWrite(
    ledgerAddress,
    'audit_citation',
    [babbageCid, babbageTargetRevUrl],
    "Audit Charles Babbage Against Later Revision (REMOVED)"
  );

  const babbageRecord = JSON.parse(await client.readContract({
    address: ledgerAddress,
    functionName: 'get_citation',
    args: [babbageCid],
  }));
  const babbageStatus = await client.readContract({
    address: ledgerAddress,
    functionName: 'get_status',
    args: [babbageCid],
  });

  evidence.cases.scenario_removed = {
    title: "Scenario 5: REMOVED Drift Audit (Deleted Statement Verified Absent)",
    citationId: babbageCid,
    registerTx: regBabbage.txHash,
    registerAgree: `${regBabbage.agreeCount}/${regBabbage.totalVotes}`,
    auditTx: auditBabbageRemoved.txHash,
    auditAgree: `${auditBabbageRemoved.agreeCount}/${auditBabbageRemoved.totalVotes}`,
    baselineUrl: baseBabbageUrl,
    targetUrl: babbageTargetRevUrl,
    targetKind: "REVISION",
    targetOldid: "1378652484",
    auditClass: babbageRecord.audits[0]?.class,
    coverage: babbageRecord.audits[0]?.coverage,
    finalStatus: babbageRecord.status,
    statusString: babbageStatus,
    record: babbageRecord,
  };

  // =========================================================================
  // SCENARIO 6: ClaimsBoard Publish and Refresh with Badge Update
  // =========================================================================
  console.log("\n=======================================================");
  console.log("SCENARIO 6: ClaimsBoard Cross-Contract Integration & Real Badge Transition");
  console.log("=======================================================");
  const publishClaim = await executeWrite(
    boardAddress,
    'publish_claim',
    [turingCid, "Turing silver savings confirmed on Wikipedia"],
    "Publish Claim on Alan Turing Citation"
  );

  const rawClaimIds = await client.readContract({
    address: boardAddress,
    functionName: 'list_claim_ids',
    args: [0, 10],
  });
  const claimId = JSON.parse(rawClaimIds)[0];
  console.log("    Published Claim ID:", claimId);

  const claimRecordInitial = JSON.parse(await client.readContract({
    address: boardAddress,
    functionName: 'get_claim',
    args: [claimId],
  }));

  // Also publish claim on MATERIAL citation (Oscars) to observe DRIFTED badge
  const publishOscarsClaim = await executeWrite(
    boardAddress,
    'publish_claim',
    [oscarsCid, "Oscars 1967 In the Heat of the Night Director"],
    "Publish Claim on Oscars Citation"
  );
  const rawClaimIds2 = await client.readContract({
    address: boardAddress,
    functionName: 'list_claim_ids',
    args: [0, 10],
  });
  const oscarsClaimId = JSON.parse(rawClaimIds2)[0];
  const oscarsClaimRecord = JSON.parse(await client.readContract({
    address: boardAddress,
    functionName: 'get_claim',
    args: [oscarsClaimId],
  }));

  evidence.cases.scenario_claims_board = {
    title: "Scenario 6: ClaimsBoard Cross-Contract Integration & Badge Derivation",
    claimId: claimId,
    citationId: turingCid,
    publishTx: publishClaim.txHash,
    publishAgree: `${publishClaim.agreeCount}/${publishClaim.totalVotes}`,
    initialBadge: claimRecordInitial.badge,
    badgeHistory: claimRecordInitial.badge_history,
    claimRecord: claimRecordInitial,
    driftedClaimId: oscarsClaimId,
    driftedBadge: oscarsClaimRecord.badge,
    driftedPublishTx: publishOscarsClaim.txHash,
  };

  // =========================================================================
  // SCENARIO 7: Measure FINALIZED Timing
  // =========================================================================
  console.log("\n=======================================================");
  console.log("SCENARIO 7: Measure FINALIZED Transition Timing");
  console.log("=======================================================");
  if (regTuring.txHash) {
    evidence.finalizedMeasurement = await measureFinalized(regTuring.txHash);
  }

  // =========================================================================
  // NEGATIVE TESTS SUITE
  // =========================================================================
  console.log("\n=======================================================");
  console.log("NEGATIVE TESTS SUITE: On-Chain Revert Payload Verification");
  console.log("=======================================================");

  const negDefs = [
    {
      key: "neg_quote_not_verbatim",
      name: "Quote Not Verbatim in Baseline",
      fn: 'register_citation',
      args: ["Invalid Quote Test", baseTuringUrl, JSON.stringify(["Albert Einstein formulated general relativity in 1915."])],
      expectedRevert: "quote not found verbatim in baseline",
    },
    {
      key: "neg_non_permalink_baseline",
      name: "Non-Permalink Baseline URL",
      fn: 'register_citation',
      args: ["Non-Permalink Test", "https://en.wikipedia.org/wiki/Alan_Turing", turingQuotesJson],
      expectedRevert: "baseline must be an immutable revision permalink",
    },
    {
      key: "neg_older_target_revision",
      name: "Target Revision Older or Equal to Baseline",
      fn: 'audit_citation',
      args: [turingCid, "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1379624982"],
      expectedRevert: "target revision must be later than baseline",
    },
    {
      key: "neg_cross_page_target",
      name: "Cross-Page Target URL Mismatch",
      fn: 'audit_citation',
      args: [turingCid, "https://en.wikipedia.org/w/index.php?title=Alonzo_Church&oldid=1380390650"],
      expectedRevert: "target title must match baseline title",
    },
    {
      key: "neg_cross_host_target",
      name: "Cross-Host Target URL Mismatch",
      fn: 'audit_citation',
      args: [turingCid, "https://de.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1380390650"],
      expectedRevert: "target URL host must match baseline host",
    },
    {
      key: "neg_non_allowlisted_domain",
      name: "Non-Allowlisted Domain",
      fn: 'register_citation',
      args: ["Evil Domain Test", "https://evil.com/w/index.php?title=Alan_Turing&oldid=1000", turingQuotesJson],
      expectedRevert: "source URL must be a wikipedia.org language domain",
    },
    {
      key: "neg_userinfo_spoof",
      name: "Userinfo URL Spoof",
      fn: 'register_citation',
      args: ["Userinfo Spoof", "https://admin:pass@en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1379625434", turingQuotesJson],
      expectedRevert: "source URL cannot contain userinfo",
    },
    {
      key: "neg_fragment_spoof",
      name: "Fragment URL Spoof in Baseline",
      fn: 'register_citation',
      args: ["Fragment Spoof", "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1379625434#Section", turingQuotesJson],
      expectedRevert: "baseline URL cannot contain fragment",
    },
    {
      key: "neg_duplicate_registration",
      name: "Duplicate Citation Registration",
      fn: 'register_citation',
      args: ["Duplicate Registration Attempt", baseTuringUrl, turingQuotesJson],
      expectedRevert: "already registered",
    },
    {
      key: "neg_repeated_target_audit",
      name: "Repeated Target Revision Audit",
      fn: 'audit_citation',
      args: [turingCid, turingTargetRevUrl],
      expectedRevert: "target already audited",
    },
    {
      key: "neg_nonexistent_citation",
      name: "Audit Nonexistent Citation",
      fn: 'audit_citation',
      args: ["000000000000", turingTargetRevUrl],
      expectedRevert: "citation not found",
    },
  ];

  for (const n of negDefs) {
    const res = await executeWrite(ledgerAddress, n.fn, n.args, n.name);
    evidence.negativeTests[n.key] = {
      name: n.name,
      fn: n.fn,
      args: n.args,
      txHash: res.txHash,
      status: res.status,
      result: res.result,
      agreeCount: `${res.agreeCount}/${res.totalVotes}`,
      revertPayload: res.leaderResult,
      expectedRevert: n.expectedRevert,
    };
  }

  const outPath = path.join(__dirname, 'live_evidence.json');
  fs.writeFileSync(outPath, JSON.stringify(evidence, null, 2));
  console.log(`\n=======================================================`);
  console.log(`CANONICAL EVIDENCE SUITE COMPLETE!`);
  console.log(`Saved results to ${outPath}`);
  console.log(`=======================================================`);
}

main().catch(err => {
  console.error("Evidence run failed:", err);
  process.exit(1);
});
