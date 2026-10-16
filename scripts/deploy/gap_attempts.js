const dns = require('dns');
dns.setDefaultResultOrder('ipv4first');

const { createClient, chains, createAccount } = require('genlayer-js');
const fs = require('fs');
const path = require('path');

async function main() {
  const deployments = JSON.parse(
    fs.readFileSync(path.join(__dirname, 'deployments.json'), 'utf8')
  );
  const ledgerAddress = deployments.ledger.contractAddress;
  const client = createClient({
    chain: chains.studionet,
    account: createAccount(),
  });

  console.log("Retrying Userinfo Spoof on-chain...");
  const turingQuotesJson = JSON.stringify(["In the 1940s, Turing became worried about losing his savings in the event of a German invasion."]);
  try {
    const hash = await client.writeContract({
      address: ledgerAddress,
      functionName: 'register_citation',
      args: ["Userinfo Spoof Retry", "https://user:pass@en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1379625434", turingQuotesJson],
    });
    console.log("Tx sent:", hash);
    const receipt = await client.waitForTransactionReceipt({ hash, retries: 120, interval: 3000 });
    console.log("Receipt status:", receipt.status_name, "Result:", receipt.result_name);

    const res = await fetch(deployments.rpc, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: 1,
        method: 'eth_getTransactionByHash',
        params: [hash],
      }),
    });
    const tx = (await res.json()).result;
    const votes = tx?.consensus_data?.votes || {};
    const agreeCount = Object.values(votes).filter(v => v === 'agree').length;
    const totalVotes = Object.values(votes).length;

    let revertPayload = null;
    const leaderReceipts = tx?.consensus_data?.leader_receipt || [];
    for (const lr of leaderReceipts) {
      if (typeof lr.result === 'string') {
        revertPayload = Buffer.from(lr.result, 'base64').slice(1).toString('utf8');
        break;
      }
    }

    console.log(`Agree: ${agreeCount}/${totalVotes}, Revert: "${revertPayload}"`);

    // Update live_evidence.json
    const evPath = path.join(__dirname, 'live_evidence.json');
    const ev = JSON.parse(fs.readFileSync(evPath, 'utf8'));
    ev.negativeTests.neg_userinfo_spoof = {
      name: "Userinfo URL Spoof",
      fn: "register_citation",
      args: ["Userinfo Spoof Retry", "https://user:pass@en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1379625434", turingQuotesJson],
      txHash: hash,
      status: receipt.status_name,
      result: receipt.result_name,
      agreeCount: `${agreeCount}/${totalVotes}`,
      revertPayload: revertPayload,
      expectedRevert: "source URL cannot contain userinfo",
    };
    fs.writeFileSync(evPath, JSON.stringify(ev, null, 2));
    console.log("Updated live_evidence.json with userinfo spoof transaction.");
  } catch (e) {
    console.log("Retry error:", e.message);
  }
}

main().catch(console.error);
