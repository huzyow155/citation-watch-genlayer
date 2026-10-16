import urllib.request
import json
import re
import html

headers = {'User-Agent': 'Bot/1.0'}

def find_deleted(from_rev, to_rev):
    url = f'https://en.wikipedia.org/w/api.php?action=compare&fromrev={from_rev}&torev={to_rev}&format=json'
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        d = json.loads(resp.read().decode('utf-8'))
        h = d['compare']['*']
        res = []
        for m in re.finditer(r'<del[^>]*>(.*?)</del>', h):
            clean = re.sub(r'<[^>]+>', '', m.group(1))
            res.append(html.unescape(clean))
        return res

pairs = [
    ("Ada Lovelace", 1374881938, 1376338287),
    ("Alan Turing", 1379624216, 1379624982),
    ("Alan Turing 2", 1379624982, 1379625434),
    ("Claude Shannon", 1377743314, 1378873158),
    ("Charles Babbage", 1378651841, 1378652484),
    ("Computing", 1369864690, 1369865080),
]

for label, f, t in pairs:
    dels = find_deleted(f, t)
    print(f"=== {label} ({f} -> {t}) ===")
    for d in dels:
        if len(d.strip()) > 20:
            print("  DEL:", d[:120].encode('ascii', 'replace').decode('ascii'))
