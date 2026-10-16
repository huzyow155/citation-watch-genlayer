import urllib.request
import json
import re
import html

headers = {'User-Agent': 'CitationWatchResearch/1.0'}
url = 'https://en.wikipedia.org/w/api.php?action=compare&fromrev=1369080338&torev=1370247723&format=json'
req = urllib.request.Request(url, headers=headers)
with urllib.request.urlopen(req) as resp:
    d = json.loads(resp.read().decode('utf-8'))
    h = d['compare']['*']
    pattern = r'<td class="diff-deletedline diff-side-deleted"><div>(.*?)</div></td>\s*<td[^>]*>.*?</td>\s*<td class="diff-addedline diff-side-added"><div>(.*?)</div></td>'
    for m in re.finditer(pattern, h, re.DOTALL):
        print('OLD:', html.unescape(re.sub(r'<[^>]+>', '', m.group(1))).strip()[:140].encode('ascii', 'replace').decode('ascii'))
        print('NEW:', html.unescape(re.sub(r'<[^>]+>', '', m.group(2))).strip()[:140].encode('ascii', 'replace').decode('ascii'))
