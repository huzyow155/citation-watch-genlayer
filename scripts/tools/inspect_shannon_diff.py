import urllib.request
import json
import re
import html

headers = {'User-Agent': 'CitationWatchResearch/1.0 (test@citationwatch.org)'}

def get_diff(title, from_rev, to_rev):
    url = f'https://en.wikipedia.org/w/api.php?action=compare&fromrev={from_rev}&torev={to_rev}&format=json'
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        diff_html = data['compare']['*']
        return diff_html

raw = get_diff('Claude_Shannon', 1377743314, 1378873158)
lines = re.findall(r'<del[^>]*>(.*?)</del>', raw)
for l in lines:
    clean = re.sub(r'<[^>]+>', '', l).encode('ascii', 'replace').decode('ascii')
    print('DEL:', clean)

# Also let's check what changed in that section
deleted_tds = re.findall(r'<td class="diff-deletedline"><div>(.*?)</div></td>', raw)
for td in deleted_tds:
    clean = re.sub(r'<[^>]+>', '', td).encode('ascii', 'replace').decode('ascii')
    print('DELETED LINE:', clean)
