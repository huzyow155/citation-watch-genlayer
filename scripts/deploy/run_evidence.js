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
  console.log("RUNNING CANONICAL EVIDENCE SUITE FOR CITATIONWATCH");
  console.log("Ledger Contract Address:", ledgerAddress);
  console.log("ClaimsBoard Address:    ", boardAddress);
  console.log("RPC:                    ", rpcUrl);
  console.log("=======================================================\n");

  const account = createAccount();
  const client = createClient({
    chain: chains.studionet,
    account: account,
  });

  const evidence = {
    network: "GenLayer Studionet (Preview)",
    chainId: 61999,
    rpc: rpcUrl,
    ledgerAddress: ledgerAddress,
    claimsBoardAddress: boardAddress,
    ledgerDeployTxHash: deployments.ledger.deployTxHash,
    claimsBoardDeployTxHash: deployments.claimsBoard.deployTxHash,
    setLedgerTxHash: deployments.claimsBoard.setLedgerTxHash,
    recordedAt: new Date().toISOString(),
    cases: {},
    negativeTests: {},
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
    let err = null;

    try {
      txHash = await client.writeContract({
        address: targetAddr,
        functionName: fnName,
        args: args,
      });
      console.log(`    Tx sent: ${txHash}`);
    } catch (sendErr) {
      console.log(`    Send error: ${sendErr.message}`);
      err = sendErr.message;
    }

    if (txHash) {
      try {
        receipt = await client.waitForTransactionReceipt({
          hash: txHash,
          retries: 120,
          interval: 3000,
        });
      } catch (waitErr) {
        console.log(`    Wait note: ${waitErr.message}`);
      }
    }

    const dur = ((Date.now() - t0) / 1000).toFixed(2);
    let tx = null;
    if (txHash) {
      tx = await getTxDetails(txHash);
    }

    const statusName = tx?.status_name || receipt?.status_name || (err ? "FAILED" : "UNKNOWN");
    const resultName = tx?.result_name || receipt?.result_name || "UNKNOWN";
    const votes = tx?.consensus_data?.votes || {};
    const agreeCount = Object.values(votes).filter(v => v === 'agree').length;
    const totalVotes = Object.values(votes).length;
    const leaderResult = decodeLeaderResult(tx);

    console.log(`    Finished in ${dur}s | Status: ${statusName} | Result: ${resultName} | Agree: ${agreeCount}/${totalVotes}`);
    if (leaderResult) console.log(`    Leader result: ${leaderResult}`);

    return {
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
    };
  }

  // =========================================================================
  // SCENARIO 1: UNCHANGED Revision Audit
  // =========================================================================
  console.log("\n=======================================================");
  console.log("SCENARIO 1: UNCHANGED Audit on Alan Turing Revision Pair");
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

  // Read registered citation ID
  const rawMeta = await client.readContract({
    address: ledgerAddress,
    functionName: 'list_citation_ids',
    args: [0, 10],
  });
  const allIds = JSON.parse(rawMeta);
  const turingCid = allIds[0];
  console.log("    Registered Citation ID:", turingCid);

  const turingTargetRevUrl = "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1380390650";
  const auditTuringUnchanged = await executeWrite(
    ledgerAddress,
    'audit_citation',
    [turingCid, turingTargetRevUrl],
    "Audit Alan Turing Against Later Revision (UNCHANGED)"
  );

  const turingRecordAfterRev = JSON.parse(await client.readContract({
    address: ledgerAddress,
    functionName: 'get_citation',
    args: [turingCid],
  }));
  const turingStatusAfterRev = await client.readContract({
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
    auditClass: turingRecordAfterRev.audits[0]?.class,
    finalStatus: turingRecordAfterRev.status,
    statusString: turingStatusAfterRev,
    record: turingRecordAfterRev,
  };

  // =========================================================================
  // SCENARIO 2: Multi-Audit History & LIVE Audit
  // =========================================================================
  console.log("\n=======================================================");
  console.log("SCENARIO 2: LIVE Audit & Multi-Audit History (Alan Turing)");
  console.log("=======================================================");
  const turingLiveUrl = "https://en.wikipedia.org/wiki/Alan_Turing";
  const auditTuringLive = await executeWrite(
    ledgerAddress,
    'audit_citation',
    [turingCid, turingLiveUrl],
    "Audit Alan Turing Against LIVE Article (/wiki/Alan_Turing)"
  );

  const turingRecordAfterLive = JSON.parse(await client.readContract({
    address: ledgerAddress,
    functionName: 'get_citation',
    args: [turingCid],
  }));
  const turingStatusAfterLive = await client.readContract({
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
    auditsTotal: turingRecordAfterLive.audits_total,
    latestAuditIndex: turingRecordAfterLive.latest_audit_index,
    statusString: turingStatusAfterLive,
    record: turingRecordAfterLive,
  };

  // =========================================================================
  // SCENARIO 3: ClaimsBoard Publish and Refresh with Badge
  // =========================================================================
  console.log("\n=======================================================");
  console.log("SCENARIO 3: ClaimsBoard Publish Claim & Badge Verification");
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
  const claimIds = JSON.parse(rawClaimIds);
  const claimId = claimIds[0];
  console.log("    Published Claim ID:", claimId);

  const claimRecordInitial = JSON.parse(await client.readContract({
    address: boardAddress,
    functionName: 'get_claim',
    args: [claimId],
  }));

  const refreshClaim = await executeWrite(
    boardAddress,
    'refresh_claim',
    [claimId],
    "Refresh Claim Status from Ledger"
  );

  const claimRecordRefreshed = JSON.parse(await client.readContract({
    address: boardAddress,
    functionName: 'get_claim',
    args: [claimId],
  }));

  evidence.cases.scenario_claims_board = {
    title: "Scenario 3: ClaimsBoard Cross-Contract Integration & Badge Derivation",
    claimId: claimId,
    citationId: turingCid,
    publishTx: publishClaim.txHash,
    publishAgree: `${publishClaim.agreeCount}/${publishClaim.totalVotes}`,
    refreshTx: refreshClaim.txHash,
    refreshAgree: `${refreshClaim.agreeCount}/${refreshClaim.totalVotes}`,
    initialBadge: claimRecordInitial.badge,
    refreshedBadge: claimRecordRefreshed.badge,
    badgeHistory: claimRecordRefreshed.badge_history,
    claimRecord: claimRecordRefreshed,
  };

  // =========================================================================
  // SCENARIO 4: COSMETIC Drift (Reworded wording on film grosses)
  // =========================================================================
  console.log("\n=======================================================");
  console.log("SCENARIO 4: COSMETIC Drift Audit (Film Grosses Rewording)");
  console.log("=======================================================");
  const baseFilmUrl = "https://en.wikipedia.org/w/index.php?title=List_of_highest-grossing_films&oldid=1379571136";
  const filmQuote = "The measuring system for gauging a film's success is based on unadjusted grosses, mainly because historically this is the way it has always been done";
  const filmQuotesJson = JSON.stringify([filmQuote]);

  const regFilm = await executeWrite(
    ledgerAddress,
    'register_citation',
    ["Unadjusted film gross metric", baseFilmUrl, filmQuotesJson],
    "Register Film Gross Metric Citation"
  );

  const allIdsAfterFilm = JSON.parse(await client.readContract({
    address: ledgerAddress,
    functionName: 'list_citation_ids',
    args: [0, 10],
  }));
  const filmCid = allIdsAfterFilm[0];
  console.log("    Registered Film Citation ID:", filmCid);

  const filmTargetRevUrl = "https://en.wikipedia.org/w/index.php?title=List_of_highest-grossing_films&oldid=1379737814";
  const auditFilmCosmetic = await executeWrite(
    ledgerAddress,
    'audit_citation',
    [filmCid, filmTargetRevUrl],
    "Audit Film Citation Against Later Revision (COSMETIC)"
  );

  const filmRecordAfterAudit = JSON.parse(await client.readContract({
    address: ledgerAddress,
    functionName: 'get_citation',
    args: [filmCid],
  }));
  const filmStatusAfterAudit = await client.readContract({
    address: ledgerAddress,
    functionName: 'get_status',
    args: [filmCid],
  });

  evidence.cases.scenario_cosmetic = {
    title: "Scenario 4: COSMETIC Drift Audit (Reworded phrasing, facts identical)",
    citationId: filmCid,
    registerTx: regFilm.txHash,
    registerAgree: `${regFilm.agreeCount}/${regFilm.totalVotes}`,
    auditTx: auditFilmCosmetic.txHash,
    auditAgree: `${auditFilmCosmetic.agreeCount}/${auditFilmCosmetic.totalVotes}`,
    baselineUrl: baseFilmUrl,
    targetUrl: filmTargetRevUrl,
    targetKind: "REVISION",
    targetOldid: "1379737814",
    auditClass: filmRecordAfterAudit.audits[0]?.class,
    finalStatus: filmRecordAfterAudit.status,
    statusString: filmStatusAfterAudit,
    record: filmRecordAfterAudit,
  };

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
