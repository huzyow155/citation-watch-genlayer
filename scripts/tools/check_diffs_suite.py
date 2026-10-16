import urllib.request
import json
import re

headers = {'User-Agent': 'CitationWatchResearch/1.0 (test@citationwatch.org)'}

def get_deleted_lines(from_rev, to_rev):
    url = f'https://en.wikipedia.org/w/api.php?action=compare&fromrev={from_rev}&torev={to_rev}&format=json'
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        raw = data['compare']['*']
        lines = []
        for td in re.findall(r'<td class="diff-deletedline"><div>(.*?)</div></td>', raw):
            clean = re.sub(r'<[^>]+>', '', td)
            lines.append(clean)
        return lines

# Let's check Charles Babbage 1378651841 -> 1378652484
print("=== Babbage ===")
for l in get_deleted_lines(1378651841, 1378652484):
    print("DEL:", l[:100].encode('ascii', 'replace').decode('ascii'))

# Let's check Computing 1373063033 -> 1375087113 ("rm plagiarism")
print("=== Computing ===")
for l in get_deleted_lines(1373063033, 1375087113):
    print("DEL:", l[:100].encode('ascii', 'replace').decode('ascii'))
