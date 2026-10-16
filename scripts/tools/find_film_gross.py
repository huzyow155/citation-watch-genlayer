import urllib.request
import json
import re
import html

url = 'https://en.wikipedia.org/w/api.php?action=compare&fromrev=1379757258&torev=1380478466&format=json'
req = urllib.request.Request(url, headers={'User-Agent': 'CitationWatchResearch/1.0'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    h = data['compare']['*']
    pattern = r'<td class="diff-deletedline diff-side-deleted"><div>(.*?)</div></td>\s*<td[^>]*>.*?</td>\s*<td class="diff-addedline diff-side-added"><div>(.*?)</div></td>'
    for m in re.finditer(pattern, h, re.DOTALL):
        del_text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        add_text = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if any(c.isdigit() for c in del_text):
            print('OLD:', del_text[:120].encode('ascii', 'replace').decode('ascii'))
            print('NEW:', add_text[:120].encode('ascii', 'replace').decode('ascii'))
            print('---')
