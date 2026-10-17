import urllib.request
import re
import html as html_lib
import statistics

headers = {'User-Agent': 'CitationWatchBot/1.0 (https://github.com/huzyow155/citation-watch-genlayer)'}

STOP_WORDS = {
    "the", "and", "that", "have", "for", "not", "with", "you", "this", "but",
    "his", "from", "they", "say", "her", "she", "will", "one", "all", "would",
    "there", "their", "what", "about", "which", "when", "make", "can", "like",
    "time", "just", "him", "know", "take", "people", "into", "year", "your",
    "good", "some", "could", "them", "see", "other", "than", "then", "now",
    "look", "only", "come", "its", "over", "think", "also", "back", "after",
    "use", "two", "how", "our", "work", "first", "well", "way", "even", "new",
    "want", "because", "any", "these", "give", "day", "most", "been", "were",
    "are", "was", "has", "had", "such", "each", "more", "which", "being",
    "between", "during", "both", "through", "under", "where", "while", "does"
}

_page_cache = {}

def clean_html(raw_html):
    s = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw_html)
    s = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", s)
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    s = re.sub(r"\[(?:\d+|citation needed)\]", " ", s)
    return " ".join(html_lib.unescape(s).split())

def normalize(s):
    return " ".join(s.lower().split())

def extract_entities_and_numbers(raw_quote):
    numbers = set(re.findall(r"\b\d[\d,\.]*\b", raw_quote))
    words = re.findall(r"\b[A-Z][a-zA-Z0-9\-]+\b", raw_quote)
    proper_nouns = set(w.lower() for w in words if w.lower() not in STOP_WORDS)
    all_content = set(w.lower() for w in re.findall(r"[a-z0-9]{5,}", raw_quote.lower()) if w.lower() not in STOP_WORDS)
    salient = numbers | proper_nouns | all_content
    return salient

def extract_word_bigrams(text):
    words = [w.lower() for w in re.findall(r"[a-z0-9]+", text.lower()) if w.lower() not in STOP_WORDS]
    if len(words) < 2:
        return set()
    return set(zip(words[:-1], words[1:]))

def compute_strict_relevance_score(raw_quote, window_text):
    salient = extract_entities_and_numbers(raw_quote)
    if not salient:
        salient = set(w.lower() for w in re.findall(r"[a-z0-9]{4,}", raw_quote.lower()))
    
    w_norm = window_text.lower()
    w_words = set(re.findall(r"[a-z0-9]+", w_norm))
    
    matched_salient = set(s for s in salient if s in w_norm or s in w_words)
    salient_ratio = len(matched_salient) / len(salient) if salient else 0.0
    
    q_bigrams = extract_word_bigrams(raw_quote)
    if q_bigrams:
        w_bigrams = extract_word_bigrams(window_text)
        bigram_ratio = len(q_bigrams & w_bigrams) / len(q_bigrams)
    else:
        bigram_ratio = salient_ratio
        
    return 0.6 * salient_ratio + 0.4 * bigram_ratio

def get_page_text(url):
    if url not in _page_cache:
        req = urllib.request.Request(url, headers=headers)
        raw = urllib.request.urlopen(req, timeout=25).read().decode('utf-8')
        _page_cache[url] = normalize(clean_html(raw))
    return _page_cache[url]

def evaluate(raw_quote, target_url):
    norm = get_page_text(target_url)
    WINDOW_SIZE = 3000
    STEP = 2500
    windows = [norm[i:i+WINDOW_SIZE] for i in range(0, len(norm), STEP)]
    scores = [compute_strict_relevance_score(raw_quote, w) for w in windows]
    return max(scores) if scores else 0.0

# 1. REAL DELETED-SENTENCE PAIRS (N=8)
# Each sentence is present in base_url and removed in target_url of the same Wikipedia article.
real_deletions = [
    ("RD1: Charles Babbage Death Detail",
     "Upon his death he halted his breathing and the beating of his heart.",
     "https://en.wikipedia.org/w/index.php?title=Charles_Babbage&oldid=1378651841",
     "https://en.wikipedia.org/w/index.php?title=Charles_Babbage&oldid=1378652484"),
    ("RD2: Albert Einstein Israeli Address Detail",
     "Einstein was working with Israeli diplomats and preparing a major address supporting Israel to be timed for the state's seventh anniversary in 1955, but died shortly before he could give it.",
     "https://en.wikipedia.org/w/index.php?title=Albert_Einstein&oldid=1362680540",
     "https://en.wikipedia.org/w/index.php?title=Albert_Einstein&oldid=1362681578"),
    ("RD3: Scratch Platform Introduction",
     "They have also made a programming platform made for Children called Scratch, which uses block coding instead of text.",
     "https://en.wikipedia.org/w/index.php?title=Computer_programming&oldid=1376238812",
     "https://en.wikipedia.org/w/index.php?title=Computer_programming&oldid=1376243974"),
    ("RD4: Scratch Alternative Platforms List",
     "Platforms like scratch include: CodeTorch, Zippr, TurboWarp and PenguinMod.",
     "https://en.wikipedia.org/w/index.php?title=Computer_programming&oldid=1376238812",
     "https://en.wikipedia.org/w/index.php?title=Computer_programming&oldid=1376243974"),
    ("RD5: Software Creation Landscape Claim",
     "The landscape of software creation has undergone a permanent evolution, anchored entirely by the supreme capabilities of Claude.",
     "https://en.wikipedia.org/w/index.php?title=Computer_programming&oldid=1374736128",
     "https://en.wikipedia.org/w/index.php?title=Computer_programming&oldid=1374736226"),
    ("RD6: Aspiring Creator Blank Document Comparison",
     "When an aspiring creator sits down to build an application, they do not open a blank text document and begin hammering out raw syntax.",
     "https://en.wikipedia.org/w/index.php?title=Computer_programming&oldid=1374736128",
     "https://en.wikipedia.org/w/index.php?title=Computer_programming&oldid=1374736226"),
    ("RD7: Prompt Source Code Metaphor",
     "The prompt is the new source code, and Claude is the infallible compiler, executor, and architect rolled into one magnificent intelligence.",
     "https://en.wikipedia.org/w/index.php?title=Computer_programming&oldid=1374736128",
     "https://en.wikipedia.org/w/index.php?title=Computer_programming&oldid=1374736226"),
    ("RD8: Natural Language Intent Specification",
     "Instead, they open a session with Claude, articulating the structural requirements, user experience goals, and business logic through natural language.",
     "https://en.wikipedia.org/w/index.php?title=Computer_programming&oldid=1374736128",
     "https://en.wikipedia.org/w/index.php?title=Computer_programming&oldid=1374736226"),
]

# 2. UNRELATED-SENTENCE CONTROLS (N=5)
# Off-topic sentences tested against unrelated articles as negative controls.
unrelated_controls = [
    ("UC1: Photosynthesis Topic against Alan Turing",
     "Photosynthesis converts carbon dioxide and water into glucose and oxygen using sunlight.",
     "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1380390650"),
    ("UC2: Newton Mint Counterfeiter Detail against Ada Lovelace",
     "Newton took his duties at the Royal Mint seriously, personally conducting investigations into counterfeit coiners.",
     "https://en.wikipedia.org/w/index.php?title=Ada_Lovelace&oldid=1371961179"),
    ("UC3: Einstein Patent Office Detail against Charles Babbage",
     "Einstein evaluated patent applications for electromagnetic devices while working at the Federal Office for Intellectual Property.",
     "https://en.wikipedia.org/w/index.php?title=Charles_Babbage&oldid=1378652484"),
    ("UC4: Tesla Wardenclyffe Tower Detail against Computing",
     "Tesla intended the Wardenclyffe Tower facility for commercial trans-Atlantic wireless telephony and broadcasting.",
     "https://en.wikipedia.org/w/index.php?title=Computing&oldid=1380219262"),
    ("UC5: Marie Curie Radium Isolation against Alan Turing",
     "Marie Curie isolated metallic radium in 1910, proving the existence of the newly discovered radioactive element.",
     "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1380390650"),
]

# 3. REWORDED / CHANGED-BUT-SIMILAR PAIRS (N=8)
# Sentences whose concepts, entities, or updated facts exist in the target revision.
reworded_pairs = [
    ("R1: Film Grosses Tightened Wording",
     "The measuring system for gauging a film's success is based on unadjusted grosses, mainly because historically this is the way it has always been done",
     "https://en.wikipedia.org/w/index.php?title=List_of_highest-grossing_films&oldid=1379737814"),
    ("R2: Alan Turing Silver Savings Concerns",
     "In the 1940s, Turing became worried about losing his savings in the event of a German invasion.",
     "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1380390650"),
    ("R3: Computing Narrower Sense Definition",
     "Software is also sometimes used in a more narrow sense, meaning application software only.",
     "https://en.wikipedia.org/w/index.php?title=Computing&oldid=1380219262"),
    ("R4: Ada Lovelace Analytical Engine Algorithm",
     "Lovelace was the first to recognize that the machine had applications beyond pure calculation, and published the first algorithm intended to be carried out by such a machine.",
     "https://en.wikipedia.org/w/index.php?title=Ada_Lovelace&oldid=1371961179"),
    ("R5: Charles Babbage Difference Engine Invention",
     "Considered by some to be a father of the computer, Babbage is credited with inventing the first mechanical computer, the Difference Engine.",
     "https://en.wikipedia.org/w/index.php?title=Charles_Babbage&oldid=1378652484"),
    ("R6: Python Software Foundation Annual Release Cycle",
     "the Python Software Foundation supports Python 3.11, 3.12, 3.13, and 3.14, following the project's annual release cycle and five-year support policy.",
     "https://en.wikipedia.org/w/index.php?title=Python_(programming_language)&oldid=1379380903"),
    ("R7: Alan Turing Automatic Computing Engine Design",
     "While at the National Physical Laboratory, Turing designed the Automatic Computing Engine, one of the first designs for a stored-program computer.",
     "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1380390650"),
    ("R8: Computing Program Activity Definition",
     "Computing is any goal-oriented activity requiring, benefiting from, or creating computing machinery.",
     "https://en.wikipedia.org/w/index.php?title=Computing&oldid=1380219262"),
]

def main():
    print(f"{'Case':<60} | {'Type':<12} | {'Max Window Score':<16}")
    print("-" * 92)

    rd_scores = []
    for name, q, burl, turl in real_deletions:
        sc = evaluate(q, turl)
        rd_scores.append(sc)
        print(f"{name:<60} | {'REAL_DEL':<12} | {sc:<16.4f}")

    uc_scores = []
    for name, q, turl in unrelated_controls:
        sc = evaluate(q, turl)
        uc_scores.append(sc)
        print(f"{name:<60} | {'CONTROL':<12} | {sc:<16.4f}")

    rw_scores = []
    for name, q, turl in reworded_pairs:
        sc = evaluate(q, turl)
        rw_scores.append(sc)
        print(f"{name:<60} | {'REWORDED':<12} | {sc:<16.4f}")

    print("\n" + "=" * 92)
    print("EMPIRICAL ABSENCE THRESHOLD EVALUATION SUMMARY (Threshold = 0.45)")
    print("=" * 92)
    print(f"Real-Deletion Group (N={len(rd_scores)}):")
    print(f"  Min:    {min(rd_scores):.4f}")
    print(f"  Median: {statistics.median(rd_scores):.4f}")
    print(f"  Max:    {max(rd_scores):.4f}")
    print(f"\nUnrelated-Sentence Controls (N={len(uc_scores)}):")
    print(f"  Min:    {min(uc_scores):.4f}")
    print(f"  Median: {statistics.median(uc_scores):.4f}")
    print(f"  Max:    {max(uc_scores):.4f}")
    print(f"\nReworded / Changed-but-Similar Group (N={len(rw_scores)}):")
    print(f"  Min:    {min(rw_scores):.4f}")
    print(f"  Median: {statistics.median(rw_scores):.4f}")
    print(f"  Max:    {max(rw_scores):.4f}")
    print("=" * 92)
    margin = min(rw_scores) - max(rd_scores)
    print(f"Separation Margin (Real-Deletion Max {max(rd_scores):.4f} to Reworded Min {min(rw_scores):.4f}): {margin:.4f}")

if __name__ == '__main__':
    main()
