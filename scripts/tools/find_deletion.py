import urllib.request
import json
import re

headers = {'User-Agent': 'CitationWatch/1.0 (https://github.com/huzyow155/citation-watch-genlayer)'}

def search_deletions(title):
    url = f"https://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles={urllib.parse.quote(title)}&rvlimit=20&rvprop=ids|timestamp|comment&format=json"
    req = urllib.request.Request(url, headers=headers)
    res = urllib.request.urlopen(req)
    data = json.loads(res.read())
    pages = data.get("query", {}).get("pages", {})
    revs = []
    for pid, p in pages.items():
        revs = p.get("revisions", [])
        break

    for i in range(len(revs) - 1):
        r_new = revs[i]
        r_old = revs[i+1]
        c_url = f"https://en.wikipedia.org/w/api.php?action=compare&fromrev={r_old['revid']}&torev={r_new['revid']}&format=json"
        req = urllib.request.Request(c_url, headers=headers)
        try:
            res = urllib.request.urlopen(req)
            data = json.loads(res.read())
            html = data.get("compare", {}).get("*", "")
            deleted = re.findall(r'<td class="diff-deletedline[^"]*"><div>(.*?)</div></td>', html)
            for d in deleted:
                clean = re.sub(r'<[^>]+>', '', d).strip()
                if 40 <= len(clean) <= 220 and "{" not in clean and "[" not in clean:
                    print(f"\nFOUND DELETION in {title}:")
                    print(f"  Old rev (baseline): {r_old['revid']}")
                    print(f"  New rev (target):   {r_new['revid']}")
                    print(f"  Deleted sentence:   \"{clean}\" (len {len(clean)})")
                    return
        except Exception as e:
            pass

if __name__ == "__main__":
    search_deletions("Alan Turing")
    search_deletions("Ada Lovelace")
    search_deletions("Computing")
