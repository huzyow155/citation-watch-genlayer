import urllib.request
import json
import re
import html
import sys

headers = {'User-Agent': 'CitationWatchBot/1.0 (https://github.com/huzyow155/citation-watch-genlayer)'}

def check_diff(from_rev, to_rev):
    url = f"https://en.wikipedia.org/w/api.php?action=compare&fromrev={from_rev}&torev={to_rev}&format=json"
    req = urllib.request.Request(url, headers=headers)
    data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
    diff_html = data['compare']['*']
    rows = re.findall(r'<tr>(.*?)</tr>', diff_html, re.DOTALL)
    for r in rows:
        if 'diff-deletedline' in r or 'diffchange' in r:
            # find deleted and added content
            del_text = " ".join(re.findall(r'<td[^>]*class="[^"]*deleted[^"]*"[^>]*>(.*?)</td>', r, re.DOTALL))
            add_text = " ".join(re.findall(r'<td[^>]*class="[^"]*added[^"]*"[^>]*>(.*?)</td>', r, re.DOTALL))
            del_clean = re.sub(r'<[^>]+>', '', del_text).strip()
            add_clean = re.sub(r'<[^>]+>', '', add_text).strip()
            if del_clean or add_clean:
                print("DEL:", del_clean.encode('ascii', errors='replace').decode('ascii'))
                print("ADD:", add_clean.encode('ascii', errors='replace').decode('ascii'))
                print("-" * 50)

def search_prose_changes(title):
    api_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles={title}&rvprop=ids|comment|timestamp&rvlimit=20&format=json"
    req = urllib.request.Request(api_url, headers=headers)
    data = json.loads(urllib.request.urlopen(req, timeout=10).read().decode('utf-8'))
    pages = data['query']['pages']
    revs = list(pages.values())[0].get('revisions', [])
    for i in range(len(revs)-1):
        cur = revs[i]
        prev = revs[i+1]
        comment = cur.get('comment', '').lower()
        if any(w in comment for w in ['update', 'population', 'increase', 'decrease', 'reword', 'change', 'number', 'revised', 'amend']):
            print(f"=== {title} {prev['revid']} -> {cur['revid']} : {comment} ===")
            check_diff(prev['revid'], cur['revid'])

if __name__ == '__main__':
    for t in ['Paris', 'Berlin', 'Tokyo', 'Chicago', 'Toronto', 'Python_(programming_language)', 'Linux']:
        search_prose_changes(t)
