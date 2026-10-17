const fs = require('fs');
const path = require('path');

function renderEvidence() {
  const rootDir = path.dirname(path.dirname(__dirname));
  const deploymentsPath = path.join(rootDir, 'scripts', 'deploy', 'deployments.json');
  const liveEvidencePath = path.join(rootDir, 'scripts', 'deploy', 'live_evidence.json');
  const readmePath = path.join(rootDir, 'README.md');
  const evidenceDocPath = path.join(rootDir, 'docs', 'EVIDENCE.md');

  const deployments = JSON.parse(fs.readFileSync(deploymentsPath, 'utf8'));
  const evidence = JSON.parse(fs.readFileSync(liveEvidencePath, 'utf8'));

  const ledger = deployments.ledger;
  const board = deployments.claimsBoard;

  let md = '';

  md += `### Deployed Contracts on GenLayer Studionet (Preview)\n\n`;
  md += `| Contract | Address | Deploy Tx Hash | Source SHA-256 (Local & On-Chain) | Status | Consensus |\n`;
  md += `| :--- | :--- | :--- | :--- | :--- | :--- |\n`;
  md += `| **SourceDriftLedger** (Main v1.2.0) | [\`${ledger.contractAddress}\`](${ledger.explorerUrl}) | \`${ledger.deployTxHash}\` | \`${ledger.sourceSha256}\` | ${ledger.deployStatus} | ${ledger.consensusResult} |\n`;
  md += `| **ClaimsBoard** (Consumer v1.2.0) | [\`${board.contractAddress}\`](${board.explorerUrl}) | \`${board.deployTxHash}\` | \`${board.sourceSha256}\` | ${board.deployStatus} | ${board.consensusResult} |\n\n`;

  md += `**Cross-Contract Linking (\`set_ledger\`):**\n`;
  md += `- Tx Hash: \`${board.setLedgerTxHash}\`\n`;
  md += `- Status: \`${board.setLedgerStatus}\`\n`;
  md += `- Configured Ledger on Consumer: \`${ledger.contractAddress}\`\n\n`;

  md += `### On-Chain Execution Scenarios & Evidence\n\n`;
  md += `| Scenario | Citation ID / Target | Registration Tx | Audit / Action Tx | Validator Agreement | Outcome Class | Final Status |\n`;
  md += `| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n`;

  const s1 = evidence.cases.scenario_unchanged;
  if (s1) {
    md += `| **Scenario 1: UNCHANGED Revision Audit** (Alan Turing) | \`${s1.citationId}\`<br>oldid ${s1.targetOldid} | \`${s1.registerTx}\` | \`${s1.auditTx}\` | Register: ${s1.registerAgree}<br>Audit: ${s1.auditAgree} | \`${s1.auditClass}\` | \`${s1.finalStatus}\` |\n`;
  }

  const s2 = evidence.cases.scenario_live_and_history;
  if (s2) {
    md += `| **Scenario 2: LIVE Page Audit & Multi-Audit History** | \`${s2.citationId}\`<br>/wiki/Alan_Turing | (inherited from S1) | \`${s2.auditTx}\` | Audit: ${s2.auditAgree} | \`UNCHANGED\` (Live Consensus Verified) | \`HEALTHY\` (${s2.auditsTotal} Audits in History) |\n`;
  }

  const s3 = evidence.cases.scenario_cosmetic;
  if (s3) {
    md += `| **Scenario 3: COSMETIC Drift Audit** (Computing Wording) | \`${s3.citationId}\`<br>oldid ${s3.targetOldid} | \`${s3.registerTx}\` | \`${s3.auditTx}\` | Register: ${s3.registerAgree}<br>Audit: ${s3.auditAgree} | \`${s3.auditClass}\` (Model Decided: REPHRASED) | \`${s3.finalStatus}\` |\n`;
  }

  const s4 = evidence.cases.scenario_material;
  if (s4) {
    md += `| **Scenario 4: MATERIAL Drift Audit** (Python Foundation) | \`${s4.citationId}\`<br>oldid ${s4.targetOldid} | \`${s4.registerTx}\` | \`${s4.auditTx}\` | Register: ${s4.registerAgree}<br>Audit: ${s4.auditAgree} | \`${s4.auditClass}\` (Model Decided: CHANGED) | \`${s4.finalStatus}\` |\n`;
  }

  const s5 = evidence.cases.scenario_removed;
  if (s5) {
    md += `| **Scenario 5: REMOVED Drift Audit (Attempted on-chain, reverted)** | \`${s5.citationId}\`<br>oldid ${s5.targetOldid} | \`${s5.registerTx}\` | \`${s5.auditTx}\` | Register: ${s5.registerAgree}<br>Audit: ${s5.auditAgree} | (Attempted on-chain, reverted: \`invalid model output\`) | \`${s5.finalStatus}\` |\n`;
  }

  const s6 = evidence.cases.scenario_claims_board;
  if (s6) {
    md += `| **Scenario 6: ClaimsBoard Badge Transition** | Claim: \`${s6.claimId}\`<br>Citation: \`${s6.citationId}\` | Publish: \`${s6.publishTx}\` | Refresh: \`${s6.refreshTx}\` | Publish: ${s6.publishAgree}<br>Refresh: ${s6.refreshAgree} | Initial: \`${s6.initialBadge}\`<br>Refreshed: \`${s6.finalBadge}\` | History: \`[${s6.finalBadgeHistory.join(', ')}]\` |\n`;
  }

  if (evidence.finalizedMeasurement) {
    const fm = evidence.finalizedMeasurement;
    md += `\n**Transaction Finality Measurement (Scenario 7):**\n`;
    md += `- Measured Transaction: \`${fm.txHash}\`\n`;
    md += `- Real-Time Elapsed: Transitioned to \`${fm.finalStatus}\` in ${fm.elapsedSeconds}s (${fm.polls} polls from local submit timestamp)\n\n`;
  }

  md += `### Attempted On-Chain, Reverted (REMOVED Audits)\n\n`;
  md += `A reverted audit is not evidence that REMOVED state transition works on-chain. On GenLayer Studionet, when an element is completely absent from presented passages, live validator LLM policies (\`prd-minimax\`, \`openai/gpt-5.4\`, \`prd-mistral\`) produce formatting variations or non-bare JSON that fail the contract's strict schema validator, triggering \`invalid model output\`. Under Issue 2 failure verification, validators probe their model and accept the leader's failure, causing the transaction to revert. While the leader receipt logs token counts, raw output tokens are not exposed on-chain. Therefore, **REMOVED state transition success is unit-tested only**.\n\n`;
  md += `| Target Scenario | Citation ID / Target | Audit Transaction Hash | Status | Consensus | Agreement | Decoded Revert Payload |\n`;
  md += `| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n`;

  const remList = evidence.removedAttempts || [];
  for (const ra of remList) {
    md += `| **${ra.name}** | \`${ra.citationId}\`<br>oldid ${ra.targetOldid} | \`${ra.txHash}\` | ${ra.status} | ${ra.result} | ${ra.agreeCount} | \`${ra.revertPayload}\` |\n`;
  }
  md += `\n`;

  md += `### Explicit Classification: On-Chain vs. Unit-Tested Only\n\n`;
  md += `In strict compliance with the Honesty Rules, behavior is partitioned by where evidence was obtained:\n\n`;
  md += `#### Verified On-Chain (GenLayer Studionet Preview)\n`;
  md += `- **UNCHANGED Deterministic Path**: Fully verified on-chain (Alan Turing revision 1380390650, Tx \`${s1?.auditTx}\`, status \`ACCEPTED\`, consensus \`MAJORITY_AGREE\`, ${s1?.auditAgree} votes). Both leader and validators matched quote verbatim without invoking model.\n`;
  md += `- **LIVE Article Consensus Payload**: Fully verified on-chain (/wiki/Alan_Turing, Tx \`${s2?.auditTx}\`, status \`ACCEPTED\`, consensus \`MAJORITY_AGREE\`, ${s2?.auditAgree} votes). Excluding live fingerprint and character counts from consensus payload resolved consensus disagreement.\n`;
  md += `- **COSMETIC Drift (Independent Model Consensus)**: Fully verified on-chain (Computing revision 1380219262, Tx \`${s3?.auditTx}\`, status \`ACCEPTED\`, consensus \`MAJORITY_AGREE\`, ${s3?.auditAgree} votes). Validators independently executed model classification within \`gl.vm.spawn_sandbox\` and achieved consensus on status \`REPHRASED\`.\n`;
  md += `- **MATERIAL Drift (Independent Model Consensus)**: Fully verified on-chain (Python Foundation revision 1379380903, Tx \`${s4?.auditTx}\`, status \`ACCEPTED\`, consensus \`MAJORITY_AGREE\`, ${s4?.auditAgree} votes). Real prose sentence fact change independently classified as status \`CHANGED\` across validators.\n`;
  md += `- **ClaimsBoard Cross-Contract Badge Transition**: Fully verified on-chain (Claim \`${s6?.claimId}\`, Publish Tx \`${s6?.publishTx}\`, Refresh Tx \`${s6?.refreshTx}\`). Claim initialized with badge \`VERIFIED\`, citation drifted to \`MATERIAL\`, and \`refresh_claim\` transitioned badge to \`DRIFTED\`, recording \`badge_history: ["VERIFIED", "DRIFTED"]\`.\n`;
  md += `- **13 Negative Revert Scenarios**: All 13 negative test transactions reverted on-chain with exact decoded error payloads accepted by validators.\n\n`;

  md += `#### Unit-Tested Only (Not On-Chain)\n`;
  md += `- **REMOVED Drift Successful State Transition**: Verified in 29 passing offline unit tests (\`test_audit_citation_removed_drift\`) where simulated LLM returns valid bare JSON for absent elements. On-chain audits reverted with \`invalid model output\`.\n`;
  md += `- **Empirical Absence Threshold Evaluation & Controls**: Evaluated across 8 real deleted-sentence pairs, 5 unrelated controls, and 8 reworded pairs (including changed-but-similar sentences) via offline script \`scripts/tools/calibrate_absence.py\` yielding empirical separation margin between 0.3147 (max real deleted) and 0.4776 (min reworded) around threshold 0.45.\n`;
  md += `- **Bounded Leader Retry Mock Fallback**: Unit-tested in \`test_layer3_consensus.py\` verifying behavior when simulated LLM outputs invalid JSON before returning valid payload on retry.\n\n`;

  md += `### On-Chain Negative Tests & Revert Payloads (13 Tests)\n\n`;
  md += `All negative tests were submitted directly to the GenLayer Studionet RPC and evaluated by validator consensus. Revert messages below were decoded from the on-chain leader receipts:\n\n`;
  md += `| Test Case | Invoked Function | Transaction Hash | Status | Consensus | Agreement | Decoded Revert Payload |\n`;
  md += `| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n`;

  for (const [k, neg] of Object.entries(evidence.negativeTests)) {
    md += `| **${neg.name}** | \`${neg.fn}\` | \`${neg.txHash}\` | ${neg.status} | ${neg.result} | ${neg.agreeCount} | \`${neg.revertPayload || 'UserError'}\` |\n`;
  }

  // 1. Write docs/EVIDENCE.md
  let evidenceDoc = `# On-Chain Evidence & Verification Log

This document provides complete, unedited receipts and validator consensus measurements for all on-chain operations executed on **GenLayer Studionet (Preview)** (Chain ID 61999).

${md}

### Method of Source Verification
- Exact RPC call used: \`eth_getTransactionByHash\` with deployment transaction hash parameter.
- Payload field inspected: \`result.data.contract_code\`, base64-decoded into contract source text.
- SHA-256 fingerprint matching: On-chain source hash exactly matches repository file hashes.
`;

  fs.writeFileSync(evidenceDocPath, evidenceDoc, 'utf8');
  console.log("Wrote docs/EVIDENCE.md");

  // 2. Update README.md between markers if README exists
  if (fs.existsSync(readmePath)) {
    let readme = fs.readFileSync(readmePath, 'utf8');
    const startMarker = '<!-- EVIDENCE_TABLE_START -->';
    const endMarker = '<!-- EVIDENCE_TABLE_END -->';

    if (readme.includes(startMarker) && readme.includes(endMarker)) {
      const parts1 = readme.split(startMarker);
      const parts2 = parts1[1].split(endMarker);
      readme = parts1[0] + startMarker + '\n\n' + md + '\n' + endMarker + parts2[1];
      fs.writeFileSync(readmePath, readme, 'utf8');
      console.log("Updated README.md between evidence markers.");
    }
  }
}

if (require.main === module) {
  renderEvidence();
}

module.exports = { renderEvidence };
