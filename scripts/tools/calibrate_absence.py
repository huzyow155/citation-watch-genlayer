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

def evaluate(raw_quote, target_url):
    if target_url not in _page_cache:
        req = urllib.request.Request(target_url, headers=headers)
        raw = urllib.request.urlopen(req, timeout=20).read().decode('utf-8')
        _page_cache[target_url] = normalize(clean_html(raw))
    
    norm = _page_cache[target_url]
    WINDOW_SIZE = 3000
    STEP = 2500
    windows = [norm[i:i+WINDOW_SIZE] for i in range(0, len(norm), STEP)]
    scores = [compute_strict_relevance_score(raw_quote, w) for w in windows]
    return max(scores) if scores else 0.0

def main():
    pairs = [
        # DELETED / ABSENT PAIRS (8 pairs from real Wikipedia revisions)
        ("D1: Turing Teddy Bear (deleted in rev 1379625434)", 
         "In 1945, Turing sewed an outfit for the bear as a Christmas surprise for his neice, Shuna Turing, then 5 years of age.",
         "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1379625434",
         "DELETED"),
        ("D2: Moon Lunar Deities Chariot Detail (deleted in rev 1380127737)",
         "Occasionally some lunar deities have been also depicted driving a chariot across the sky, such as the Hindu Chandra/Soma, the Greek Artemis, which is associated with Selene, or Luna, Selene's ancient Roman equivalent.",
         "https://en.wikipedia.org/w/index.php?title=Moon&oldid=1380127737",
         "DELETED"),
        ("D3: Charles Babbage Death Detail (deleted in rev 1378652484)",
         "Upon his death he halted his breathing and the beating of his heart.",
         "https://en.wikipedia.org/w/index.php?title=Charles_Babbage&oldid=1378652484",
         "DELETED"),
        ("D4: Photosynthesis Topic against Alan Turing article",
         "Photosynthesis converts carbon dioxide and water into glucose and oxygen using sunlight.",
         "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1380390650",
         "DELETED"),
        ("D5: Newton Mint Counterfeiter Detail against Ada Lovelace",
         "Newton took his duties at the Royal Mint seriously, personally conducting investigations into counterfeit coiners.",
         "https://en.wikipedia.org/w/index.php?title=Ada_Lovelace&oldid=1371961179",
         "DELETED"),
        ("D6: Einstein Patent Office Detail against Charles Babbage",
         "Einstein evaluated patent applications for electromagnetic devices while working at the Federal Office for Intellectual Property.",
         "https://en.wikipedia.org/w/index.php?title=Charles_Babbage&oldid=1378652484",
         "DELETED"),
        ("D7: Tesla Wardenclyffe Tower Detail against Computing",
         "Tesla intended the Wardenclyffe Tower facility for commercial trans-Atlantic wireless telephony and broadcasting.",
         "https://en.wikipedia.org/w/index.php?title=Computing&oldid=1380219262",
         "DELETED"),
        ("D8: Marie Curie Radium Isolation against Alan Turing",
         "Marie Curie isolated metallic radium in 1910, proving the existence of the newly discovered radioactive element.",
         "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1380390650",
         "DELETED"),

        # REWORDED / PRESENT PAIRS (8 pairs from real Wikipedia revisions)
        ("R1: Film Grosses Tightened Wording",
         "The measuring system for gauging a film's success is based on unadjusted grosses, mainly because historically this is the way it has always been done",
         "https://en.wikipedia.org/w/index.php?title=List_of_highest-grossing_films&oldid=1379737814",
         "REWORDED"),
        ("R2: Alan Turing Silver Savings Concerns",
         "In the 1940s, Turing became worried about losing his savings in the event of a German invasion.",
         "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1380390650",
         "REWORDED"),
        ("R3: Computing Narrower Sense Definition",
         "Software is also sometimes used in a more narrow sense, meaning application software only.",
         "https://en.wikipedia.org/w/index.php?title=Computing&oldid=1380219262",
         "REWORDED"),
        ("R4: Ada Lovelace Analytical Engine Algorithm",
         "Lovelace was the first to recognize that the machine had applications beyond pure calculation, and published the first algorithm intended to be carried out by such a machine.",
         "https://en.wikipedia.org/w/index.php?title=Ada_Lovelace&oldid=1371961179",
         "REWORDED"),
        ("R5: Charles Babbage Difference Engine Invention",
         "Considered by some to be a father of the computer, Babbage is credited with inventing the first mechanical computer, the Difference Engine.",
         "https://en.wikipedia.org/w/index.php?title=Charles_Babbage&oldid=1378652484",
         "REWORDED"),
        ("R6: Python Software Foundation Annual Release Cycle",
         "the Python Software Foundation supports Python 3.11, 3.12, 3.13, and 3.14, following the project's annual release cycle and five-year support policy.",
         "https://en.wikipedia.org/w/index.php?title=Python_(programming_language)&oldid=1379380903",
         "REWORDED"),
        ("R7: Alan Turing Automatic Computing Engine Design",
         "While at the National Physical Laboratory, Turing designed the Automatic Computing Engine, one of the first designs for a stored-program computer.",
         "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1380390650",
         "REWORDED"),
        ("R8: Computing Program Activity Definition",
         "Computing is any goal-oriented activity requiring, benefiting from, or creating computing machinery.",
         "https://en.wikipedia.org/w/index.php?title=Computing&oldid=1380219262",
         "REWORDED"),
    ]
    
    print(f"{'Case':<58} | {'Type':<8} | {'Max Window Score':<16}")
    print("-" * 88)
    
    deleted_scores = []
    reworded_scores = []
    
    for name, q, url, kind in pairs:
        score = evaluate(q, url)
        if kind == "DELETED":
            deleted_scores.append(score)
        else:
            reworded_scores.append(score)
        print(f"{name:<58} | {kind:<8} | {score:<16.4f}")
    
    print("\n" + "=" * 88)
    print("EMPIRICAL ABSENCE CALIBRATION SUMMARY (Threshold = 0.45)")
    print("=" * 88)
    print(f"Deleted / Absent Group (N={len(deleted_scores)}):")
    print(f"  Min:    {min(deleted_scores):.4f}")
    print(f"  Median: {statistics.median(deleted_scores):.4f}")
    print(f"  Max:    {max(deleted_scores):.4f}")
    print(f"\nReworded / Present Group (N={len(reworded_scores)}):")
    print(f"  Min:    {min(reworded_scores):.4f}")
    print(f"  Median: {statistics.median(reworded_scores):.4f}")
    print(f"  Max:    {max(reworded_scores):.4f}")
    print("=" * 88)

if __name__ == '__main__':
    main()
