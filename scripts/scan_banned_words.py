import os
import re
import sys

# Comprehensive banned words list per GenLayer Studionet project rules:
# - 'cryptographic proof'
# - 'tamper-proof' / 'tamperproof'
# - 'bytecode'
# - 'testnet'
# - 'live network'
# - 'unanimous' / 'unanimously'
# - Exclusivity claims ('first contract', 'only contract', 'unique solution', 'no one else')
# - 'revolutionary'

BANNED_PATTERNS = [
    (r'\bcryptographic\s+proof\b', 'cryptographic proof'),
    (r'\btamper-?proof\b', 'tamper-proof'),
    (r'\bbytecode\b', 'bytecode'),
    (r'\btestnet\b', 'testnet'),
    (r'\blive\s+network\b', 'live network'),
    (r'\bunanimous(ly)?\b', 'unanimous'),
    (r'\brevolutionary\b', 'revolutionary'),
    (r'\b(the\s+first\s+(?:contract|platform|system|implementation|dapp)|the\s+only\s+(?:contract|platform|system|implementation|solution)|no\s+one\s+else)\b', 'exclusivity claim'),
]

IGNORE_DIRS = {'.git', 'node_modules', 'dist', '__pycache__', '.pytest_cache'}
ALLOWED_FILES = {'scan_banned_words.py'}

def scan():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    violations = []

    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if f in ALLOWED_FILES:
                continue
            if not f.endswith(('.ts', '.tsx', '.js', '.jsx', '.json', '.md', '.html', '.py', '.css', '.mjs')):
                continue
            path = os.path.join(r, f)
            rel_path = os.path.relpath(path, root).replace('\\', '/')

            with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                for line_idx, line in enumerate(fp, 1):
                    for pat, name in BANNED_PATTERNS:
                        m = re.search(pat, line, re.IGNORECASE)
                        if m:
                            violations.append((rel_path, line_idx, m.group(0), line.strip()))

    if violations:
        print(f"FAILED: Found {len(violations)} banned word violations:")
        for path, line_no, matched, text in violations:
            print(f"  {path}:{line_no} [{matched}] -> {text[:100]}")
        sys.exit(1)
    else:
        print("PASSED: Zero banned words detected across codebase and docs.")
        sys.exit(0)

if __name__ == '__main__':
    scan()
