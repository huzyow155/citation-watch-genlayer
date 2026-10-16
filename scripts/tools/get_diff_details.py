import urllib.request
import json
import re

headers = {'User-Agent': 'CitationWatch/1.0 (https://github.com/huzyow155/citation-watch-genlayer)'}

def inspect_diff(rev1, rev2):
    url = f"https://en.wikipedia.org/w/api.php?action=compare&fromrev={rev1}&torev={rev2}&format=json"
    req = urllib.request.Request(url, headers=headers)
    res = urllib.request.urlopen(req)
    data = json.loads(res.read())
    html = data.get("compare", {}).get("*", "")
    deleted = re.findall(r'<td class="diff-deletedline[^"]*"><div>(.*?)</div></td>', html)
    added = re.findall(r'<td class="diff-addedline[^"]*"><div>(.*?)</div></td>', html)
    print(f"Diff between {rev1} and {rev2}:")
    print(f"Deleted ({len(deleted)}):")
    for d in deleted:
        clean = re.sub(r'<[^>]+>', '', d).strip()
        if len(clean) > 20:
            print("  - DEL:", clean[:140])
    print(f"Added ({len(added)}):")
    for a in added:
        clean = re.sub(r'<[^>]+>', '', a).strip()
        if len(clean) > 20:
            print("  - ADD:", clean[:140])

if __name__ == "__main__":
    inspect_diff(1379817447, 1379820045)
