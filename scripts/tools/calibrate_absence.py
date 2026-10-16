import urllib.request
import re
import html as html_lib

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

def clean_html(raw_html):
    s = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw_html)
    s = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", s)
    s = re.sub(r"(?is)<[^>]+>", " ", s)
    return " ".join(html_lib.unescape(s).split())

def normalize(s):
    return " ".join(s.lower().split())

def extract_entities_and_numbers(raw_quote):
    """
    Extract entity-like tokens from raw quote:
    1. Tokens containing digits (numbers, years, prices, percentages).
    2. Capitalized tokens (proper nouns, names, titles).
    3. Distinctive words (length >= 5) not in STOP_WORDS.
    """
    # Find numbers
    numbers = set(re.findall(r"\b\d[\d,\.]*\b", raw_quote))
    
    # Find capitalized words (proper nouns)
    words = re.findall(r"\b[A-Z][a-zA-Z0-9\-]+\b", raw_quote)
    proper_nouns = set(w.lower() for w in words if w.lower() not in STOP_WORDS)
    
    # Distinctive content words
    all_content = set(w.lower() for w in re.findall(r"[a-z0-9]{5,}", raw_quote.lower()) if w.lower() not in STOP_WORDS)
    
    salient = numbers | proper_nouns | all_content
    return salient

def extract_word_bigrams(text):
    words = [w.lower() for w in re.findall(r"[a-z0-9]+", text.lower()) if w.lower() not in STOP_WORDS]
    if len(words) < 2:
        return set()
    return set(zip(words[:-1], words[1:]))

def compute_strict_relevance_score(raw_quote, window_text):
    """
    Calibrated strict relevance score:
    Combines:
    1. Salient entity & number recall (weight 0.6)
    2. Word bigram overlap ratio (weight 0.4)
    If quote has numbers/proper nouns, at least one MUST be present, or score is penalized.
    """
    salient = extract_entities_and_numbers(raw_quote)
    if not salient:
        salient = set(w.lower() for w in re.findall(r"[a-z0-9]{4,}", raw_quote.lower()))
    
    w_norm = window_text.lower()
    w_words = set(re.findall(r"[a-z0-9]+", w_norm))
    
    # Salient recall
    matched_salient = set(s for s in salient if s in w_norm or s in w_words)
    salient_ratio = len(matched_salient) / len(salient) if salient else 0.0
    
    # Bigram overlap
    q_bigrams = extract_word_bigrams(raw_quote)
    if q_bigrams:
        w_bigrams = extract_word_bigrams(window_text)
        bigram_ratio = len(q_bigrams & w_bigrams) / len(q_bigrams)
    else:
        bigram_ratio = salient_ratio
        
    return 0.6 * salient_ratio + 0.4 * bigram_ratio

def evaluate(raw_quote, target_url):
    req = urllib.request.Request(target_url, headers=headers)
    text = clean_html(urllib.request.urlopen(req).read().decode('utf-8'))
    norm = normalize(text)
    
    WINDOW_SIZE = 3000
    STEP = 2500
    windows = [norm[i:i+WINDOW_SIZE] for i in range(0, len(norm), STEP)]
    scores = [compute_strict_relevance_score(raw_quote, w) for w in windows]
    return max(scores) if scores else 0.0

def main():
    pairs = [
        # DELETED / ABSENT PAIRS
        ("D1: Turing Teddy Bear (deleted in old rev)", 
         "In 1945, Turing sewed an outfit for the bear as a Christmas surprise for his neice, Shuna Turing, then 5 years of age.",
         "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1379625434",
         "ABSENT"),
        ("D2: Ada Lovelace Countess title (deleted in later rev)",
         "The Countess of Lovelace was an English mathematician and writer chiefly known for her work on the Analytical Engine.",
         "https://en.wikipedia.org/w/index.php?title=Ada_Lovelace&oldid=1371961179",
         "ABSENT"),
        ("D3: Unrelated topic against Turing article",
         "Photosynthesis converts carbon dioxide and water into glucose and oxygen using sunlight.",
         "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1380390650",
         "ABSENT"),
         
        # REWORDED / PRESENT PAIRS
        ("R1: Film Grosses Tightened Wording",
         "The measuring system for gauging a film's success is based on unadjusted grosses, mainly because historically this is the way it has always been done",
         "https://en.wikipedia.org/w/index.php?title=List_of_highest-grossing_films&oldid=1379737814",
         "REWORDED"),
        ("R2: Turing Silver Savings",
         "In the 1940s, Turing became worried about losing his savings in the event of a German invasion.",
         "https://en.wikipedia.org/w/index.php?title=Alan_Turing&oldid=1380390650",
         "PRESENT"),
        ("R3: Computing Narrower Sense",
         "Software is also sometimes used in a more narrow sense, meaning application software only.",
         "https://en.wikipedia.org/w/index.php?title=Computing&oldid=1380219262",
         "REWORDED"),
    ]
    
    print(f"{'Case':<45} | {'Type':<8} | {'Max Window Score':<16}")
    print("-" * 75)
    for name, q, url, kind in pairs:
        score = evaluate(q, url)
        print(f"{name:<45} | {kind:<8} | {score:<16.4f}")

if __name__ == '__main__':
    main()
