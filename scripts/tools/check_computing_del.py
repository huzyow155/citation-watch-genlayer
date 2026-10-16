import urllib.request
import json
import re
import html

url = 'https://en.wikipedia.org/w/api.php?action=compare&fromrev=1373063033&torev=1375087113&format=json'
req = urllib.request.Request(url, headers={'User-Agent': 'CitationWatchResearch/1.0'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    h = data['compare']['*']
    for m in re.finditer(r'<td class="diff-deletedline"><div>(.*?)</div></td>', h):
        clean = re.sub(r'<[^>]+>', '', m.group(1))
        text = html.unescape(clean).strip()
        if len(text) > 25:
            print('DEL LINE:', text[:120].encode('ascii', 'replace').decode('ascii'))
