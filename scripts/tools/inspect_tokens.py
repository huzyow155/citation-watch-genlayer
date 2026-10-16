import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import urllib.request
from scripts.tools.calibrate_absence import clean_html, normalize, get_bigrams, get_tokens

headers = {'User-Agent': 'Bot/1.0'}
q = 'Software is also sometimes used in a more narrow sense, meaning application software only.'
req = urllib.request.Request('https://en.wikipedia.org/w/index.php?title=Computing&oldid=1380219262', headers=headers)
text = normalize(clean_html(urllib.request.urlopen(req).read().decode('utf-8')))

q_words = [w for w in get_tokens(q)]
print("Tokens of q:", q_words)
# Words in quote: software, sometimes, narrow, sense, meaning, application, software

windows = [text[i:i+3000] for i in range(0, len(text), 2500)]
for idx, w in enumerate(windows):
    found = [word for word in q_words if word in w]
    ratio = len(set(found)) / len(set(q_words))
    if ratio > 0.6:
        print(f"Window {idx} found: {found} (ratio: {ratio:.2f})")
