import urllib.request
import json
import re
import html
import time

headers = {'User-Agent': 'CitationWatchResearch/1.0 (huzyow155@gmail.com)'}

def get_revs(title, limit=10):
    time.sleep(1.2)
    url = f'https://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles={title}&rvprop=ids|timestamp|comment&rvlimit={limit}&format=json'
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        d = json.loads(resp.read().decode('utf-8'))
        p = d['query']['pages']
        for k in p:
            return p[k].get('revisions', [])

def check_diff(from_rev, to_rev):
    time.sleep(1.2)
    url = f'https://en.wikipedia.org/w/api.php?action=compare&fromrev={from_rev}&torev={to_rev}&format=json'
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        d = json.loads(resp.read().decode('utf-8'))
        h = d['compare']['*']
        res = []
        for m in re.finditer(r'<del[^>]*>(.*?)</del>', h):
            clean = re.sub(r'<[^>]+>', '', m.group(1))
            res.append(html.unescape(clean).strip())
        return [r for r in res if len(r) > 25]

articles = [
    'John_von_Neumann',
    'List_of_highest-grossing_films'
]

for title in articles:
    revs = get_revs(title, 8)
    if not revs or len(revs) < 2:
        continue
    print(f"*** Checking {title} ***")
    for i in range(len(revs) - 1):
        r_later = revs[i]['revid']
        r_earlier = revs[i+1]['revid']
        dels = check_diff(r_earlier, r_later)
        if dels:
            print(f"  {r_earlier} -> {r_later}:")
            for d in dels[:2]:
                print("    -", d[:120].encode('ascii', 'replace').decode('ascii'))
