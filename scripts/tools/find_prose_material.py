import urllib.request
import json
import re
import html
import difflib

headers = {'User-Agent': 'CitationWatchBot/1.0 (https://github.com/huzyow155/citation-watch-genlayer)'}

def get_page_text(title, oldid):
    url = f"https://en.wikipedia.org/w/index.php?title={title}&oldid={oldid}"
    req = urllib.request.Request(url, headers=headers)
    raw = urllib.request.urlopen(req).read().decode('utf-8')
    s = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw)
    s = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", s)
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    s = re.sub(r"\[(?:\d+|citation needed)\]", " ", s)
    return " ".join(html.unescape(s).split())

def check_article(title):
    api_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=revisions&titles={title}&rvprop=ids|comment|timestamp&rvlimit=15&format=json"
    req = urllib.request.Request(api_url, headers=headers)
    data = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
    pages = data['query']['pages']
    revs = list(pages.values())[0].get('revisions', [])
    for i in range(len(revs)-1):
        cur = revs[i]
        prev = revs[i+1]
        comment = cur.get('comment', '').lower()
        print(f"{title}: {prev['revid']} -> {cur['revid']} | {comment}")

if __name__ == '__main__':
    for t in ['Voyager_1', 'James_Webb_Space_Telescope', 'Hubble_Space_Telescope', 'Earth', 'Moon', 'Solar_System', 'ISS']:
        check_article(t)
