import urllib.request
import json
import re
import html

headers = {'User-Agent': 'CitationWatchResearch/1.0 (test@citationwatch.org)'}

def get_recent_revs(title, limit=20):
    url = f'https://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles={title}&rvprop=ids|timestamp|comment&rvlimit={limit}&format=json'
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        pages = data['query']['pages']
        for pid in pages:
            return pages[pid].get('revisions', [])

for title in ['Alan_Turing', 'Ada_Lovelace', 'Claude_Shannon', 'Charles_Babbage', 'Computing']:
    revs = get_recent_revs(title, 10)
    print(f'=== {title} ===')
    for r in revs:
        revid = r.get("revid")
        ts = r.get("timestamp")
        comment = r.get("comment", "")
        print(f'  oldid={revid} ts={ts} comment={comment[:80]}')
