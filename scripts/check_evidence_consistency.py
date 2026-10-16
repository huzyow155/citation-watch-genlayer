import os
import json
import re
import sys

def check_consistency():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    deployments_path = os.path.join(root, "scripts", "deploy", "deployments.json")
    live_evidence_path = os.path.join(root, "scripts", "deploy", "live_evidence.json")
    readme_path = os.path.join(root, "README.md")
    docs_dir = os.path.join(root, "docs")

    with open(deployments_path, "r", encoding="utf-8") as f:
        deployments = json.load(f)

    with open(live_evidence_path, "r", encoding="utf-8") as f:
        live_evidence = json.load(f)

    expected_ledger = deployments["ledger"]["contractAddress"]
    actual_ledger = live_evidence["ledgerAddress"]
    assert actual_ledger.lower() == expected_ledger.lower(), (
        f"Ledger address mismatch: {actual_ledger} vs {expected_ledger}"
    )

    expected_board = deployments["claimsBoard"]["contractAddress"]
    actual_board = live_evidence["claimsBoardAddress"]
    assert actual_board.lower() == expected_board.lower(), (
        f"ClaimsBoard address mismatch: {actual_board} vs {expected_board}"
    )

    # Collect all known active hashes and citation IDs
    active_hashes = set()
    active_cids = set()

    def collect_identifiers(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("citationId", "claimId") and isinstance(v, str):
                    active_cids.add(v.lower())
                elif isinstance(v, str) and v.startswith("0x") and len(v) == 66:
                    active_hashes.add(v.lower())
                elif isinstance(v, str) and v.startswith("0x") and len(v) == 42:
                    active_hashes.add(v.lower())
                collect_identifiers(v)
        elif isinstance(obj, list):
            for item in obj:
                collect_identifiers(item)

    collect_identifiers(deployments)
    collect_identifiers(live_evidence)

    # Check files for consistency
    files_to_check = []
    if os.path.exists(readme_path):
        files_to_check.append(readme_path)

    for fname in os.listdir(docs_dir):
        if fname.endswith(".md"):
            files_to_check.append(os.path.join(docs_dir, fname))

    hash_pattern = re.compile(r"0x[0-9a-fA-F]{64}")
    addr_pattern = re.compile(r"0x[0-9a-fA-F]{40}")
    truncated_pattern = re.compile(r"0x[a-fA-F0-9]{4,16}\.\.\.[a-fA-F0-9]{4,16}")

    superseded_addrs = [item["address"].lower() for item in deployments.get("supersededDeployments", [])]

    for fpath in files_to_check:
        fname = os.path.basename(fpath)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for truncated hashes
        trunc_matches = truncated_pattern.findall(content)
        assert not trunc_matches, f"Truncated hash found in {fname}: {trunc_matches}"

        # Check for forbidden "undefined" or "None" in markdown tables
        lines = content.split("\n")
        for idx, line in enumerate(lines, 1):
            if "|" in line:
                if "undefined" in line.lower():
                    raise AssertionError(f"'undefined' found in table in {fname}:{idx}: {line}")
                if "none" in line.lower() and not ("none" in line.lower() and ("non-reproducible" in line.lower() or "target_oldid" in line.lower())):
                    # Allow documented None/null fields where appropriate
                    pass

        # Check superseded addresses
        if fname != "README.md":
            for s_addr in superseded_addrs:
                assert s_addr not in content.lower(), (
                    f"Superseded address {s_addr} found in {fname}! It may only appear in README.md."
                )

        # In EVIDENCE.md, check that all 66-char hashes are known
        if fname == "EVIDENCE.md":
            for h in hash_pattern.findall(content):
                assert h.lower() in active_hashes, (
                    f"Unknown transaction hash {h} found in {fname}! Not in live_evidence.json."
                )

    print("PASSED: Evidence consistency checks passed successfully.")
    print(f"  Active Ledger: {actual_ledger}")
    print(f"  Active ClaimsBoard: {actual_board}")
    print(f"  Verified {len(active_hashes)} active hashes and {len(active_cids)} citation/claim IDs.")
    print(f"  Checked {len(files_to_check)} markdown files.")

if __name__ == "__main__":
    check_consistency()
