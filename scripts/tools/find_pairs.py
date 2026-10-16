import urllib.request
import json
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "tests"))
from contracts.SourceDriftLedger import _clean_html, _normalize_text

headers = {'User-Agent': 'CitationWatchBot/1.0'}

def get_revisions(title, limit=15):
    url = f"https://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles={urllib.parse.quote(title)}&rvlimit={limit}&rvprop=ids|timestamp|comment&format=json"
    req = urllib.request.Request(url, headers=headers)
    res = urllib.request.urlopen(req)
    data = json.loads(res.read())
    pages = data.get("query", {}).get("pages", {})
    for pid, p in pages.items():
        return p.get("revisions", [])
    return []

def get_diff(from_rev, to_rev):
    url = f"https://en.wikipedia.org/w/api.php?action=compare&fromrev={from_rev}&torev={to_rev}&format=json"
    req = urllib.request.Request(url, headers=headers)
    res = urllib.request.urlopen(req)
    data = json.loads(res.read())
    html = data.get("compare", {}).get("*", "")
    deleted = re.findall(r'<td class="diff-deletedline[^"]*"><div>(.*?)</div></td>', html)
    added = re.findall(r'<td class="diff-addedline[^"]*"><div>(.*?)</div></td>', html)
    return {
        "deleted": [re.sub(r'<[^>]+>', '', d).strip() for d in deleted],
        "added": [re.sub(r'<[^>]+>', '', a).strip() for a in added],
    }

def main():
    title = sys.argv[1] if len(sys.argv) > 1 else "List of highest-grossing films"
    print(f"Finding revision diffs for: {title}")
    revs = get_revisions(title, limit=10)
    for i in range(len(revs) - 1):
        r_new = revs[i]
        r_old = revs[i+1]
        print(f"\nComparing oldid {r_old['revid']} -> {r_new['revid']} (comment: {r_new.get('comment','')})")
        diff = get_diff(r_old['revid'], r_new['revid'])
        for d in diff['deleted'][:3]:
            if len(d) > 30:
                print("  DELETED:", d[:120])
        for a in diff['added'][:3]:
            if len(a) > 30:
                print("  ADDED:  ", a[:120])

if __name__ == "__main__":
    main()
