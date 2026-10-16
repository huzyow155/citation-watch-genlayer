# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
import re
import html as html_lib
import hashlib
import ipaddress
import urllib.parse
from datetime import datetime, timezone
from genlayer import *

SCHEMA_VERSION = "1.2.0"
MIN_QUOTE_CHARS = 30
MAX_QUOTE_CHARS = 240
MAX_ELEMENTS = 4
MAX_LABEL_CHARS = 120
MAX_PAGE_CHARS = 300000
INSPECTION_BUDGET_CHARS = 12000
WINDOW_SIZE_CHARS = 3000
WINDOW_OVERLAP_CHARS = 500
LIVE_AUDIT_COOLDOWN_SECONDS = 300
MAX_FULL_AUDITS = 5
MAX_AUDIT_SUMMARIES = 20
RELEVANCE_THRESHOLD = 0.45

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


def _parse_iso8601_utc(dt_str: str) -> tuple[int, str]:
    """
    Parse ISO-8601 datetime with support for UTC 'Z', fractional seconds,
    and timezone offsets (+07:00, -05:00).
    Normalizes to UTC datetime.
    Returns: (timestamp_int, utc_iso_str)
    """
    if not isinstance(dt_str, str):
        raise gl.vm.UserError("datetime must be string")
    clean_dt = dt_str.strip()
    if not clean_dt:
        raise gl.vm.UserError("empty datetime")

    try:
        iso_clean = clean_dt[:-1] + "+00:00" if clean_dt.endswith("Z") else clean_dt
        dt = datetime.fromisoformat(iso_clean)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        ts_int = int(dt.timestamp())
        utc_iso = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        return (ts_int, utc_iso)
    except Exception:
        raise gl.vm.UserError("invalid ISO-8601 datetime format")


def _get_current_timestamp() -> tuple[int, str]:
    """Retrieve deterministic datetime from GenVM message_raw as (utc_seconds_int, utc_iso_str)."""
    if hasattr(gl, "message_raw") and isinstance(gl.message_raw, dict):
        raw_dt = gl.message_raw.get("datetime")
        if raw_dt:
            return _parse_iso8601_utc(str(raw_dt))
    raise gl.vm.UserError("clock unavailable")


def _clean_html(raw_html: str) -> str:
    """
    Deterministic HTML normalizer:
    1. Strips <script>, <style>, <noscript>, <nav>, <header>, <footer> blocks.
    2. Strips all HTML tags.
    3. Normalizes typographic quotes, dashes to ASCII.
    4. Unescapes HTML entities.
    5. Collapses whitespace.
    """
    if not raw_html:
        return ""
    s = str(raw_html)
    s = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", s)
    s = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", s)
    s = re.sub(r"(?is)<noscript[^>]*>.*?</noscript>", " ", s)
    s = re.sub(r"(?is)<nav[^>]*>.*?</nav>", " ", s)
    s = re.sub(r"(?is)<header[^>]*>.*?</header>", " ", s)
    s = re.sub(r"(?is)<footer[^>]*>.*?</footer>", " ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("\u2018", "'").replace("\u2019", "'").replace("\u201a", "'").replace("\u201b", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u201e", '"').replace("\u201f", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    s = s.replace("\u00a0", " ").replace("\u202f", " ").replace("\u200b", "").replace("\ufeff", "")
    s = html_lib.unescape(s)
    return " ".join(s.split())


def _normalize_text(s: str) -> str:
    """
    ONE shared normalization function used for quotes, baseline text, and target text:
    - casefold
    - unify typographic quotes, dashes, non-breaking spaces
    - strip Wikipedia citation markers (e.g. [1], [12], [citation needed])
    - unescape HTML entities
    - collapse whitespace
    """
    if not s:
        return ""
    text = str(s).lower()
    text = text.replace("\u2018", "'").replace("\u2019", "'").replace("\u201a", "'").replace("\u201b", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"').replace("\u201e", '"').replace("\u201f", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    text = text.replace("\u00a0", " ").replace("\u202f", " ").replace("\u200b", "").replace("\ufeff", "")
    text = re.sub(r"\[(?:\d+|citation needed|clarification needed|page needed|note \d+)\]", " ", text)
    text = html_lib.unescape(text)
    return " ".join(text.split())


def _normalize_title(raw_title: str) -> str:
    """
    Normalize Wikipedia page title:
    percent-decode, replace underscores with spaces, collapse whitespace,
    capitalize the initial letter (standard MediaWiki page title behavior).
    """
    decoded = urllib.parse.unquote(raw_title)
    spaced = decoded.replace("_", " ")
    collapsed = " ".join(spaced.split())
    if not collapsed:
        return ""
    return collapsed[0].upper() + collapsed[1:]


def _validate_host_and_scheme(parsed: urllib.parse.SplitResult) -> str:
    """Strict host, scheme, port, userinfo, IP checks."""
    if parsed.scheme.lower() != "https":
        raise gl.vm.UserError("source URL scheme must be https")

    if not parsed.hostname:
        raise gl.vm.UserError("source URL hostname is missing")

    if parsed.username is not None or parsed.password is not None:
        raise gl.vm.UserError("source URL cannot contain userinfo")

    if parsed.port is not None and parsed.port != 443:
        raise gl.vm.UserError("source URL port must be 443 or omitted")

    raw_host = parsed.hostname
    try:
        raw_host.encode("ascii")
    except UnicodeEncodeError:
        raise gl.vm.UserError("source URL hostname must be pure ASCII")

    if "xn--" in raw_host.lower():
        raise gl.vm.UserError("source URL hostname cannot be punycode")

    if raw_host.endswith("."):
        raise gl.vm.UserError("source URL hostname cannot end with a dot")

    host_norm = raw_host.lower()

    try:
        ipaddress.ip_address(host_norm)
        raise gl.vm.UserError("source URL hostname cannot be an IP address")
    except ValueError:
        pass

    if host_norm == "localhost" or host_norm.endswith(".localhost"):
        raise gl.vm.UserError("source URL hostname cannot be localhost")

    parts = host_norm.split(".")
    if len(parts) != 3 or parts[1] != "wikipedia" or parts[2] != "org" or not re.match(r"^[a-z0-9\-]+$", parts[0]):
        raise gl.vm.UserError("source URL must be a wikipedia.org language domain")

    return host_norm


def _validate_baseline_url(url: str) -> tuple[str, str, str, str]:
    """
    Validate baseline URL against strict revision permalink rules:
    https://<lang>.wikipedia.org/w/index.php?title=<T>&oldid=<N>
    Returns: (canonical_url, host, normalized_title, oldid_str)
    """
    if not isinstance(url, str):
        raise gl.vm.UserError("baseline URL must be string")
    clean_url = url.strip()
    if not clean_url:
        raise gl.vm.UserError("empty baseline URL")
    if any(c in clean_url for c in (" ", "\t", "\r", "\n")):
        raise gl.vm.UserError("baseline URL cannot contain whitespace")
    if "\\" in clean_url:
        raise gl.vm.UserError("baseline URL cannot contain backslashes")

    parsed = urllib.parse.urlsplit(clean_url)

    if parsed.fragment:
        raise gl.vm.UserError("baseline URL cannot contain fragment")

    host_norm = _validate_host_and_scheme(parsed)

    if parsed.path != "/w/index.php":
        raise gl.vm.UserError("baseline must be an immutable revision permalink")

    qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    if "title" not in qs or "oldid" not in qs:
        raise gl.vm.UserError("baseline must be an immutable revision permalink")

    raw_title = qs["title"][0]
    raw_oldid = qs["oldid"][0]

    if not re.match(r"^\d+$", raw_oldid):
        raise gl.vm.UserError("baseline must be an immutable revision permalink")

    norm_title = _normalize_title(raw_title)
    if not norm_title:
        raise gl.vm.UserError("baseline URL title cannot be empty")

    canonical_url = f"https://{host_norm}/w/index.php?title={urllib.parse.quote(norm_title.replace(' ', '_'))}&oldid={raw_oldid}"
    return (canonical_url, host_norm, norm_title, raw_oldid)


def _validate_target_url(
    target_url: str,
    baseline_host: str,
    baseline_title: str,
    baseline_oldid: str
) -> tuple[str, str, str | None]:
    """
    Validate target URL against page identity binding and revision ordering rules.
    Returns: (canonical_target_url, target_kind: 'REVISION'|'LIVE', target_oldid: str|None)
    """
    if not isinstance(target_url, str):
        raise gl.vm.UserError("target URL must be string")
    clean_url = target_url.strip()
    if not clean_url:
        raise gl.vm.UserError("empty target URL")
    if any(c in clean_url for c in (" ", "\t", "\r", "\n")):
        raise gl.vm.UserError("target URL cannot contain whitespace")
    if "\\" in clean_url:
        raise gl.vm.UserError("target URL cannot contain backslashes")

    parsed = urllib.parse.urlsplit(clean_url)
    if parsed.fragment:
        raise gl.vm.UserError("target URL cannot contain fragment")

    target_host = _validate_host_and_scheme(parsed)
    if target_host != baseline_host:
        raise gl.vm.UserError("target URL host must match baseline host")

    if parsed.path == "/w/index.php":
        qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        if "title" not in qs or "oldid" not in qs:
            raise gl.vm.UserError("target revision URL must contain title and oldid")

        raw_title = qs["title"][0]
        raw_oldid = qs["oldid"][0]

        if not re.match(r"^\d+$", raw_oldid):
            raise gl.vm.UserError("target oldid must be digits only")

        norm_title = _normalize_title(raw_title)
        if norm_title != baseline_title:
            raise gl.vm.UserError("target title must match baseline title")

        if int(raw_oldid) <= int(baseline_oldid):
            raise gl.vm.UserError("target revision must be later than baseline")

        canonical_url = f"https://{target_host}/w/index.php?title={urllib.parse.quote(norm_title.replace(' ', '_'))}&oldid={raw_oldid}"
        return (canonical_url, "REVISION", raw_oldid)

    elif parsed.path.startswith("/wiki/"):
        if parsed.query:
            raise gl.vm.UserError("live target URL cannot contain query parameters")

        raw_title = parsed.path[len("/wiki/"):]
        norm_title = _normalize_title(raw_title)
        if not norm_title or norm_title != baseline_title:
            raise gl.vm.UserError("target title must match baseline title")

        canonical_url = f"https://{target_host}/wiki/{urllib.parse.quote(norm_title.replace(' ', '_'))}"
        return (canonical_url, "LIVE", None)

    else:
        raise gl.vm.UserError("target URL path must be /w/index.php or /wiki/<Title>")


def _extract_salient_tokens(raw_quote: str) -> set[str]:
    """
    Deterministic extraction of salient entities, numbers, and proper nouns:
    1. Tokens containing digits (numbers, dates, amounts).
    2. Capitalized words (names, titles, proper nouns).
    3. Content words length >= 5 not in STOP_WORDS.
    """
    numbers = set(re.findall(r"\b\d[\d,\.]*\b", raw_quote))
    words = re.findall(r"\b[A-Z][a-zA-Z0-9\-]+\b", raw_quote)
    proper_nouns = set(w.lower() for w in words if w.lower() not in STOP_WORDS)
    content = set(w.lower() for w in re.findall(r"[a-z0-9]{5,}", raw_quote.lower()) if w.lower() not in STOP_WORDS)
    salient = numbers | proper_nouns | content
    if not salient:
        salient = set(w.lower() for w in re.findall(r"[a-z0-9]{3,}", raw_quote.lower()) if w.lower() not in STOP_WORDS)
    return salient


def _extract_word_bigrams(text: str) -> set[tuple[str, str]]:
    """Deterministic extraction of word bigrams excluding stop words."""
    words = [w.lower() for w in re.findall(r"[a-z0-9]+", text.lower()) if w.lower() not in STOP_WORDS]
    if len(words) < 2:
        return set()
    return set(zip(words[:-1], words[1:]))


def _compute_relevance_score(raw_quote: str, window_text: str) -> float:
    """
    Calibrated strict relevance score:
    Combines:
    1. Salient entity & number recall (weight 0.6)
    2. Word bigram overlap ratio (weight 0.4)
    Empirically calibrated against Wikipedia diffs:
    - Truly deleted/absent sentences score <= 0.20
    - Rephrased/present sentences score >= 0.70
    Threshold = 0.45.
    """
    salient = _extract_salient_tokens(raw_quote)
    w_norm = window_text.lower()
    w_words = set(re.findall(r"[a-z0-9]+", w_norm))
    matched_salient = set(s for s in salient if s in w_norm or s in w_words)
    salient_ratio = len(matched_salient) / len(salient) if salient else 0.0

    q_bigrams = _extract_word_bigrams(raw_quote)
    if q_bigrams:
        w_bigrams = _extract_word_bigrams(window_text)
        bigram_ratio = len(q_bigrams & w_bigrams) / len(q_bigrams)
    else:
        bigram_ratio = salient_ratio

    return 0.6 * salient_ratio + 0.4 * bigram_ratio


_compute_lexical_overlap = _compute_relevance_score


def _select_windows_for_quotes(
    full_text: str,
    quotes_raw: list[str]
) -> tuple[str, list[dict], str, int, int, bool]:
    """
    Deterministic window selection based on calibrated relevance score with unresolved quotes.
    Strictly accounts for separator length so len(inspected_text) <= INSPECTION_BUDGET_CHARS.
    Returns: (inspected_text, selected_windows, coverage, source_chars_total, source_chars_inspected, truncated_at)
    """
    source_chars_total = len(full_text)
    truncated_at = source_chars_total > MAX_PAGE_CHARS
    text_to_inspect = full_text[:MAX_PAGE_CHARS]

    if len(text_to_inspect) <= INSPECTION_BUDGET_CHARS:
        return (text_to_inspect, [{"idx": 0, "start": 0, "end": len(text_to_inspect), "chunk": text_to_inspect}], "FULL", source_chars_total, len(text_to_inspect), truncated_at)

    step = WINDOW_SIZE_CHARS - WINDOW_OVERLAP_CHARS
    windows = []
    start = 0
    idx = 0
    while start < len(text_to_inspect):
        end = min(start + WINDOW_SIZE_CHARS, len(text_to_inspect))
        chunk = text_to_inspect[start:end]
        max_score = 0.0
        for q in quotes_raw:
            score = _compute_relevance_score(q, chunk)
            if score > max_score:
                max_score = score
        windows.append({
            "idx": idx,
            "start": start,
            "end": end,
            "chunk": chunk,
            "score": max_score,
        })
        idx += 1
        if end >= len(text_to_inspect):
            break
        start += step

    windows_by_score = sorted(windows, key=lambda w: (w["score"], -w["idx"]), reverse=True)

    separator = "\n[...]\n"
    sep_len = len(separator)

    selected_windows = []
    accum_chars = 0
    for w in windows_by_score:
        additional = len(w["chunk"]) if len(selected_windows) == 0 else len(w["chunk"]) + sep_len
        if accum_chars + additional > INSPECTION_BUDGET_CHARS:
            if len(selected_windows) > 0:
                continue
            w["chunk"] = w["chunk"][:INSPECTION_BUDGET_CHARS]
            additional = len(w["chunk"])
        selected_windows.append(w)
        accum_chars += additional
        if accum_chars >= INSPECTION_BUDGET_CHARS:
            break

    selected_ordered = sorted(selected_windows, key=lambda w: w["start"])
    inspected_text = separator.join(w["chunk"] for w in selected_ordered)
    if len(inspected_text) > INSPECTION_BUDGET_CHARS:
        inspected_text = inspected_text[:INSPECTION_BUDGET_CHARS]

    return (inspected_text, selected_ordered, "SELECTED_WINDOWS", source_chars_total, len(inspected_text), truncated_at)


def _segment_passages(inspected_text: str) -> list[dict]:
    """
    Deterministic sentence-level segmentation of inspected text into numbered passages.
    Returns: list of {"id": "p1".."pN", "text": str, "sha256": str}
    """
    normalized = re.sub(r"[\r\n\t]+", " ", inspected_text).strip()
    raw_sentences = re.split(r"(?<=[.!?])\s+", normalized)

    passages = []
    pid = 1
    for s in raw_sentences:
        clean_s = s.strip()
        if len(clean_s) >= 20:
            truncated_s = clean_s[:MAX_QUOTE_CHARS].strip()
            h = hashlib.sha256(truncated_s.encode("utf-8")).hexdigest()
            passages.append({
                "id": f"p{pid}",
                "text": truncated_s,
                "sha256": h,
            })
            pid += 1

    if not passages and len(normalized) >= 20:
        truncated_s = normalized[:MAX_QUOTE_CHARS].strip()
        h = hashlib.sha256(truncated_s.encode("utf-8")).hexdigest()
        passages.append({
            "id": "p1",
            "text": truncated_s,
            "sha256": h,
        })

    return passages


def _map_element_statuses_to_class(element_statuses: list[str]) -> str:
    """
    Deterministic drift class from element statuses per specification:
    - any CHANGED -> MATERIAL
    - else any ABSENT -> REMOVED
    - else any REPHRASED -> COSMETIC
    - else (all SAME) -> UNCHANGED
    """
    if not element_statuses:
        raise gl.vm.UserError("no elements to classify")

    if any(st == "CHANGED" for st in element_statuses):
        return "MATERIAL"
    if any(st == "ABSENT" for st in element_statuses):
        return "REMOVED"
    if any(st == "REPHRASED" for st in element_statuses):
        return "COSMETIC"
    if all(st == "SAME" for st in element_statuses):
        return "UNCHANGED"

    raise gl.vm.UserError(f"invalid element statuses: {element_statuses}")


def _map_class_to_status(drift_class: str) -> str:
    """
    Derive citation status from latest audit class:
    - UNCHANGED or COSMETIC -> HEALTHY
    - MATERIAL -> DRIFTED
    - REMOVED -> REMOVED
    """
    if drift_class in ("UNCHANGED", "COSMETIC"):
        return "HEALTHY"
    if drift_class == "MATERIAL":
        return "DRIFTED"
    if drift_class == "REMOVED":
        return "REMOVED"
    raise gl.vm.UserError(f"unknown audit class: {drift_class}")


def _fetch_page_text(target_url: str) -> tuple[str, str]:
    """Deterministic web fetch with render text mode and HTTP GET fallback."""
    fetched_text = ""
    fetch_method = "web.render"
    try:
        render_res = gl.nondet.web.render(target_url, mode="text")
        fetched_text = str(render_res) if render_res is not None else ""
    except Exception:
        fetched_text = ""

    if not fetched_text or not fetched_text.strip():
        fetch_method = "web.get"
        try:
            resp = gl.nondet.web.get(target_url)
            if int(resp.status) == 200 and resp.body is not None:
                b = resp.body
                fetched_text = b.decode("utf-8", errors="replace") if isinstance(b, (bytes, bytearray)) else str(b)
        except Exception:
            fetched_text = ""

    clean_full = _clean_html(fetched_text) if fetched_text else ""
    return (clean_full, fetch_method)


def _classify_unresolved_elements(
    passages: list[dict],
    unresolved_ids: list[str],
    raw_quotes_map: dict[str, str],
    norm_full: str,
) -> tuple[str, dict[str, dict]]:
    """
    Executes model classification on unresolved quotes against presented passages:
    - Bounded retry (initial attempt + up to 2 corrective retries requesting strict JSON).
    - Validates strict JSON output and required schema without code fences or regex repair.
    - Runs absence discipline check (relevance threshold < 0.45 across all windows).
    - Verifies cited quotes are verbatim substrings in the specified passage.
    Returns: (status_code, element_results_dict)
    where status_code is 'OK' or 'FAIL|...'
    """
    if not unresolved_ids:
        return ("OK", {})

    passages_block = "\n".join(f"[{p['id']}] {p['text']}" for p in passages)
    elements_to_classify = [{"id": eid, "quote": raw_quotes_map[eid]} for eid in unresolved_ids]
    passages_by_id = {p["id"]: p for p in passages}

    base_prompt = (
        "You are a strict citation drift classifier.\n"
        "Evaluate each tracked quote against the presented passages from the target document.\n"
        "For each element, decide its status:\n"
        "- REPHRASED: the target asserts the exact same assertion, facts, numbers, and entities using different wording.\n"
        "- CHANGED: the target asserts something that conflicts (different number, entity, outcome, or polarity).\n"
        "- ABSENT: the presented passages do not address this assertion at all.\n\n"
        "Rules:\n"
        "1. For REPHRASED and CHANGED, you MUST provide 'passage_id' (e.g. \"p1\") and 'cited_quote' copied verbatim from that passage.\n"
        "2. For ABSENT, 'passage_id' must be null and 'cited_quote' must be null.\n"
        "3. Return strictly a JSON object with key 'elements'. No extra keys, no markdown code blocks.\n\n"
        "PRESENTED PASSAGES:\n"
        f"{passages_block}\n\n"
        "ELEMENTS TO CLASSIFY:\n"
        f"{json.dumps(elements_to_classify, indent=2)}\n\n"
        "Required JSON format:\n"
        "{\"elements\": [{\"id\": \"e1\", \"status\": \"REPHRASED\"|\"CHANGED\"|\"ABSENT\", \"passage_id\": \"p1\"|null, \"cited_quote\": \"...\"|null}]}"
    )

    current_prompt = base_prompt
    parsed_model = None

    for attempt in range(3):
        raw_model_res = gl.nondet.exec_prompt(current_prompt, response_format="json")
        candidate = None
        if isinstance(raw_model_res, dict):
            candidate = raw_model_res
        elif isinstance(raw_model_res, str):
            try:
                candidate = json.loads(raw_model_res)
            except Exception:
                candidate = None

        if (
            isinstance(candidate, dict)
            and set(candidate.keys()) == {"elements"}
            and isinstance(candidate.get("elements"), list)
            and len(candidate["elements"]) == len(unresolved_ids)
        ):
            valid_schema = True
            seen_ids = set()
            for me in candidate["elements"]:
                if (
                    not isinstance(me, dict)
                    or set(me.keys()) != {"id", "status", "passage_id", "cited_quote"}
                    or me.get("id") not in unresolved_ids
                    or me.get("id") in seen_ids
                    or me.get("status") not in ("REPHRASED", "CHANGED", "ABSENT")
                ):
                    valid_schema = False
                    break
                seen_ids.add(me.get("id"))
                st = me.get("status")
                pid = me.get("passage_id")
                cq = me.get("cited_quote")
                if st == "ABSENT":
                    if pid is not None or cq is not None:
                        valid_schema = False
                        break
                else:
                    if not isinstance(pid, str) or pid not in passages_by_id:
                        valid_schema = False
                        break
                    if not isinstance(cq, str) or len(cq.strip()) < 10:
                        valid_schema = False
                        break
            if valid_schema:
                parsed_model = candidate
                break

        if attempt < 2:
            current_prompt = (
                f"{base_prompt}\n\n"
                "IMPORTANT: Your previous output was invalid JSON or did not match the exact required schema. "
                "Return strictly a single valid JSON object with key 'elements'. "
                "Do NOT wrap with markdown code fences (```json or ```). "
                "Do NOT include any backticks or commentary. "
                "Ensure every element has 'id', 'status', 'passage_id', and 'cited_quote'."
            )

    if parsed_model is None:
        return ("FAIL|INVALID_MODEL_OUTPUT", {})

    element_results = {}
    for me in parsed_model["elements"]:
        eid = me["id"]
        st = me["status"]
        pid = me["passage_id"]
        cq = me["cited_quote"]

        if st == "ABSENT":
            raw_q = raw_quotes_map[eid]
            step = WINDOW_SIZE_CHARS - WINDOW_OVERLAP_CHARS
            for w_start in range(0, len(norm_full), step):
                w_chunk = norm_full[w_start:w_start + WINDOW_SIZE_CHARS]
                score = _compute_relevance_score(raw_q, w_chunk)
                if score >= RELEVANCE_THRESHOLD:
                    return ("FAIL|ABSENCE_UNSUPPORTED", {})
            element_results[eid] = {
                "id": eid,
                "status": "ABSENT",
                "decided_by": "MODEL",
                "passage_id": None,
                "cited_quote": None,
            }
        else:
            norm_cq = _normalize_text(cq)
            passage_norm = _normalize_text(passages_by_id[pid]["text"])
            if norm_cq not in passage_norm:
                return ("FAIL|CITED_QUOTE_NOT_VERBATIM", {})
            element_results[eid] = {
                "id": eid,
                "status": st,
                "decided_by": "MODEL",
                "passage_id": pid,
                "cited_quote": cq.strip(),
            }

    return ("OK", element_results)


class SourceDriftLedger(gl.Contract):
    citations: TreeMap[str, str]
    audited_revisions: TreeMap[str, str]
    citation_ids: TreeMap[str, str]
    registrations: TreeMap[str, str]
    meta: TreeMap[str, str]

    def __init__(self):
        # Do not assign TreeMap in __init__ per GenLayer runtime rules
        pass

    def _ensure_meta_init(self) -> None:
        if "nonce" not in self.meta:
            self.meta["nonce"] = "0"
        if "citations_total" not in self.meta:
            self.meta["citations_total"] = "0"

    @gl.public.view
    def get_citation(self, citation_id: str) -> str:
        cid = str(citation_id).strip()
        if cid not in self.citations:
            raise gl.vm.UserError("citation not found")
        return self.citations[cid]

    @gl.public.view
    def get_audit_history(self, citation_id: str) -> str:
        cid = str(citation_id).strip()
        if cid not in self.citations:
            raise gl.vm.UserError("citation not found")
        record = json.loads(self.citations[cid])
        return json.dumps(record.get("audits", []))

    @gl.public.view
    def get_status(self, citation_id: str) -> str:
        cid = str(citation_id).strip()
        if cid not in self.citations:
            raise gl.vm.UserError("citation not found")
        record = json.loads(self.citations[cid])
        status = record.get("status", "UNAUDITED")
        audits_total = record.get("audits_total", 0)
        latest_audit_index = record.get("latest_audit_index", -1)
        audits = record.get("audits", [])
        if latest_audit_index >= 0 and latest_audit_index < len(audits):
            latest_audit = audits[latest_audit_index]
            latest_class = latest_audit.get("class", "NONE")
            latest_at = latest_audit.get("audited_at", "NONE")
        else:
            latest_class = "NONE"
            latest_at = "NONE"
        return f"{status}|{latest_class}|{audits_total}|{latest_at}"

    @gl.public.view
    def list_citation_ids(self, offset: int, limit: int) -> str:
        total = int(self.meta.get("citations_total", "0"))
        all_ids = [self.citation_ids[str(i)] for i in range(total)]
        off = max(0, int(offset))
        lim = max(0, int(limit))
        reversed_ids = list(reversed(all_ids))
        sliced = reversed_ids[off:off + lim] if lim > 0 else reversed_ids[off:]
        return json.dumps(sliced)

    @gl.public.view
    def get_meta(self) -> str:
        total = int(self.meta.get("citations_total", "0"))
        return json.dumps({
            "schema_version": SCHEMA_VERSION,
            "citations_total": total,
            "nonce": int(self.meta.get("nonce", "0")),
        })

    @gl.public.write
    def register_citation(self, label: str, baseline_url: str, quotes_json: str) -> None:
        """
        Validate EVERYTHING first before touching storage.
        Verifies 1..4 verbatim quotes in the baseline Wikipedia revision permalink text deterministically.
        """
        if not isinstance(label, str):
            raise gl.vm.UserError("label must be string")
        clean_label = label.strip()
        if len(clean_label) > MAX_LABEL_CHARS:
            raise gl.vm.UserError(f"label exceeds maximum length of {MAX_LABEL_CHARS} characters")

        canonical_url, host_norm, norm_title, oldid_str = _validate_baseline_url(baseline_url)

        if not isinstance(quotes_json, str):
            raise gl.vm.UserError("quotes_json must be JSON string")

        try:
            parsed_quotes = json.loads(quotes_json)
        except Exception:
            raise gl.vm.UserError("quotes_json must be valid JSON")

        if not isinstance(parsed_quotes, list) or len(parsed_quotes) < 1 or len(parsed_quotes) > MAX_ELEMENTS:
            raise gl.vm.UserError(f"quotes must be a list of 1 to {MAX_ELEMENTS} items")

        validated_quotes = []
        seen_normalized_quotes = set()
        for idx, q in enumerate(parsed_quotes):
            if not isinstance(q, str):
                raise gl.vm.UserError(f"quote {idx + 1} must be string")
            clean_q = " ".join(q.split())
            if len(clean_q) < MIN_QUOTE_CHARS or len(clean_q) > MAX_QUOTE_CHARS:
                raise gl.vm.UserError(f"quote {idx + 1} length must be between {MIN_QUOTE_CHARS} and {MAX_QUOTE_CHARS} characters")
            norm_q = _normalize_text(clean_q)
            if not norm_q:
                raise gl.vm.UserError(f"quote {idx + 1} cannot be empty")
            if norm_q in seen_normalized_quotes:
                raise gl.vm.UserError("duplicate quote")
            seen_normalized_quotes.add(norm_q)
            validated_quotes.append({
                "id": f"e{idx + 1}",
                "quote": clean_q,
                "quote_sha256": hashlib.sha256(clean_q.encode("utf-8")).hexdigest(),
                "norm_quote": norm_q,
            })

        sorted_norm_preimage = f"{host_norm}|{oldid_str}|" + "|".join(sorted(seen_normalized_quotes))
        reg_fingerprint = hashlib.sha256(sorted_norm_preimage.encode("utf-8")).hexdigest()

        if reg_fingerprint in self.registrations:
            raise gl.vm.UserError("already registered")

        sender = gl.message.sender_address.as_hex
        current_ts, now_str = _get_current_timestamp()

        def leader_reg_eval() -> str:
            clean_text, fetch_method = _fetch_page_text(canonical_url)
            if not clean_text or not clean_text.strip():
                return "FAIL|SOURCE_UNAVAILABLE"

            norm_text = _normalize_text(clean_text)

            for item in validated_quotes:
                if item["norm_quote"] not in norm_text:
                    return f"FAIL|QUOTE_NOT_FOUND|{item['id']}"

            base_sha256 = hashlib.sha256(norm_text.encode("utf-8")).hexdigest()
            meta_data = {"base_chars_total": len(clean_text), "fetch_method": fetch_method}
            return f"OK|{base_sha256}\n---\n{json.dumps(meta_data)}"

        def validator_reg_eval(leaders_res: gl.vm.Result) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            raw_leader = leaders_res.calldata
            if not isinstance(raw_leader, str):
                return False

            if raw_leader.startswith("FAIL|"):
                if raw_leader == "FAIL|SOURCE_UNAVAILABLE":
                    def val_fail_fetch() -> tuple[str, str]:
                        return _fetch_page_text(canonical_url)
                    sand_res = gl.vm.spawn_sandbox(val_fail_fetch)
                    if not isinstance(sand_res, gl.vm.Return):
                        return True
                    val_clean, _ = sand_res.calldata
                    return not val_clean or not val_clean.strip()

                if raw_leader.startswith("FAIL|QUOTE_NOT_FOUND"):
                    def val_q_fetch() -> tuple[str, str]:
                        return _fetch_page_text(canonical_url)
                    sand_res = gl.vm.spawn_sandbox(val_q_fetch)
                    if not isinstance(sand_res, gl.vm.Return):
                        return False
                    val_clean, _ = sand_res.calldata
                    if not val_clean or not val_clean.strip():
                        return False
                    val_norm = _normalize_text(val_clean)
                    qid = raw_leader.split("|")[2] if len(raw_leader.split("|")) > 2 else ""
                    for item in validated_quotes:
                        if item["id"] == qid:
                            return item["norm_quote"] not in val_norm
                    return False
                return False

            if not raw_leader.startswith("OK|") or "\n---\n" not in raw_leader:
                return False

            header, raw_meta = raw_leader.split("\n---\n", 1)
            leader_base_sha256 = header[len("OK|"):]

            def val_fetch_fn() -> tuple[str, str]:
                return _fetch_page_text(canonical_url)

            sand_res = gl.vm.spawn_sandbox(val_fetch_fn)
            if not isinstance(sand_res, gl.vm.Return):
                return False

            val_clean, _ = sand_res.calldata
            if not val_clean or not val_clean.strip():
                return False

            val_norm = _normalize_text(val_clean)
            for item in validated_quotes:
                if item["norm_quote"] not in val_norm:
                    return False

            val_base_sha256 = hashlib.sha256(val_norm.encode("utf-8")).hexdigest()
            return val_base_sha256 == leader_base_sha256

        consensus_res = gl.vm.run_nondet_unsafe(leader_reg_eval, validator_reg_eval)
        if not consensus_res or not consensus_res.startswith("OK|"):
            if consensus_res.startswith("FAIL|SOURCE_UNAVAILABLE"):
                raise gl.vm.UserError("source unavailable")
            if consensus_res.startswith("FAIL|QUOTE_NOT_FOUND"):
                raise gl.vm.UserError("quote not found verbatim in baseline")
            raise gl.vm.UserError("baseline verification failed")

        header, raw_meta = consensus_res.split("\n---\n", 1)
        base_sha256 = header[len("OK|"):]
        meta_dict = json.loads(raw_meta)
        base_chars_total = int(meta_dict["base_chars_total"])
        fetch_method = meta_dict["fetch_method"]

        self._ensure_meta_init()
        current_nonce = int(self.meta.get("nonce", "0")) + 1
        self.meta["nonce"] = str(current_nonce)
        total_citations = int(self.meta.get("citations_total", "0"))

        cid_preimage = f"{sender}|{canonical_url}|{reg_fingerprint}|{current_nonce}".encode("utf-8")
        citation_id = hashlib.sha256(cid_preimage).hexdigest()[:12]

        record_elements = [
            {"id": item["id"], "quote": item["quote"], "quote_sha256": item["quote_sha256"]}
            for item in validated_quotes
        ]

        record = {
            "schema_version": SCHEMA_VERSION,
            "citation_id": citation_id,
            "label": clean_label,
            "registrant": sender,
            "registered_at": now_str,
            "registered_at_ts": current_ts,
            "baseline_url": canonical_url,
            "baseline_host": host_norm,
            "baseline_title": norm_title,
            "baseline_oldid": oldid_str,
            "elements": record_elements,
            "baseline_text_sha256": base_sha256,
            "baseline_chars_total": base_chars_total,
            "fetch_method": fetch_method,
            "latest_audit_index": -1,
            "status": "UNAUDITED",
            "audits_total": 0,
            "audits": [],
        }

        self.citations[citation_id] = json.dumps(record)
        self.citation_ids[str(total_citations)] = citation_id
        self.registrations[reg_fingerprint] = citation_id
        self.meta["citations_total"] = str(total_citations + 1)

    @gl.public.write
    def audit_citation(self, citation_id: str, target_url: str) -> None:
        """
        Audit a registered citation against a target URL:
        - target can be a later REVISION (oldid > baseline_oldid) or the LIVE page (/wiki/<Title>)
        - persistent TreeMap audited_revisions prevents repeated audits even after history compaction
        - deterministic layer runs first (verbatim presence -> SAME)
        - model layer runs only for unresolved elements
        - custom leader/validator consensus compares canonical enumerations, excludes LIVE fingerprint,
          and verifies cited quotes as substrings without passage ID dependence.
        """
        cid = str(citation_id).strip()
        if cid not in self.citations:
            raise gl.vm.UserError("citation not found")

        record = json.loads(self.citations[cid])
        baseline_host = record["baseline_host"]
        baseline_title = record["baseline_title"]
        baseline_oldid = record["baseline_oldid"]
        elements = record["elements"]
        audits = record.get("audits", [])

        canonical_target_url, target_kind, target_oldid = _validate_target_url(
            target_url, baseline_host, baseline_title, baseline_oldid
        )

        current_ts, now_str = _get_current_timestamp()

        # Defect 5: Check already audited via persistent TreeMap
        if target_kind == "REVISION":
            audit_key = f"{cid}:{target_oldid}"
            if audit_key in self.audited_revisions:
                raise gl.vm.UserError("target already audited")

        # Check cooldown for LIVE targets
        if target_kind == "LIVE":
            for prev in reversed(audits):
                if prev.get("target_kind") == "LIVE":
                    prev_ts = int(prev.get("audited_at_ts", 0))
                    if current_ts - prev_ts < LIVE_AUDIT_COOLDOWN_SECONDS:
                        raise gl.vm.UserError("live audit cooldown active")
                    break

        sender = gl.message.sender_address.as_hex
        norm_quotes_map = {e["id"]: _normalize_text(e["quote"]) for e in elements}
        raw_quotes_map = {e["id"]: e["quote"] for e in elements}

        def leader_audit_eval() -> str:
            clean_full, fetch_method = _fetch_page_text(canonical_target_url)
            if not clean_full or not clean_full.strip():
                return "FAIL|SOURCE_UNAVAILABLE"

            norm_full = _normalize_text(clean_full)
            target_fingerprint = hashlib.sha256(norm_full.encode("utf-8")).hexdigest()

            # 1. Deterministic Layer
            element_results = {}
            unresolved_ids = []
            for e in elements:
                eid = e["id"]
                nq = norm_quotes_map[eid]
                if nq in norm_full:
                    element_results[eid] = {
                        "id": eid,
                        "status": "SAME",
                        "decided_by": "DETERMINISTIC",
                        "passage_id": None,
                        "cited_quote": e["quote"],
                    }
                else:
                    unresolved_ids.append(eid)

            if not unresolved_ids:
                coverage = "DETERMINISTIC_ONLY"
                presented_passages = []
                presented_segment_ids = []
                presented_segments_count = 0
                budget_chars_used = 0
                source_chars_total = len(clean_full)
                source_chars_inspected = 0
                chars_scanned = len(clean_full)
                truncated_at = False
            else:
                unresolved_raw_quotes = [raw_quotes_map[eid] for eid in unresolved_ids]
                (
                    inspected_text,
                    selected_windows,
                    coverage,
                    source_chars_total,
                    source_chars_inspected,
                    truncated_at,
                ) = _select_windows_for_quotes(clean_full, unresolved_raw_quotes)
                budget_chars_used = len(inspected_text)
                chars_scanned = len(clean_full)

                presented_passages = _segment_passages(inspected_text)
                presented_segment_ids = [p["id"] for p in presented_passages]
                presented_segments_count = len(presented_passages)

                model_code, model_res = _classify_unresolved_elements(
                    presented_passages, unresolved_ids, raw_quotes_map, norm_full
                )
                if model_code != "OK":
                    return model_code
                element_results.update(model_res)

            ordered_statuses = [element_results[e["id"]]["status"] for e in elements]
            audit_class = _map_element_statuses_to_class(ordered_statuses)

            fp_for_consensus = target_fingerprint if target_kind == "REVISION" else "NONE"
            elem_summary = "|".join(f"{e['id']}:{element_results[e['id']]['status']}" for e in elements)
            canonical_summary = f"{audit_class}|{fp_for_consensus}|{elem_summary}"

            audit_data = {
                "class": audit_class,
                "target_text_sha256": target_fingerprint,
                "elements": [element_results[e["id"]] for e in elements],
                "passages": presented_passages,
                "presented_segment_ids": presented_segment_ids,
                "presented_segments_count": presented_segments_count,
                "source_chars_total": source_chars_total,
                "source_chars_inspected": source_chars_inspected,
                "chars_scanned": chars_scanned,
                "budget_chars_used": budget_chars_used,
                "truncated_at": truncated_at,
                "coverage": coverage,
                "fetch_method": fetch_method,
                "fingerprint_in_consensus": (target_kind == "REVISION"),
            }

            return f"OK|{canonical_summary}\n---\n{json.dumps(audit_data)}"

        def validator_audit_eval(leaders_res: gl.vm.Result) -> bool:
            """
            Validator consensus check (v1.2.0):
            1. Verifies leader returned a valid OK payload with header and JSON.
            2. Re-evaluates leader failures:
               - FAIL|SOURCE_UNAVAILABLE: confirms on own fetch.
               - FAIL|ABSENCE_UNSUPPORTED: recomputed on validator's own text.
               - FAIL|INVALID_MODEL_OUTPUT / FAIL|CITED_QUOTE_NOT_VERBATIM: runs own classification
                 once in sandbox; accepts failure ONLY if validator run also fails; rejects otherwise.
            3. Validator independently fetches target document from the same URL.
            4. For REVISION targets, verifies target fingerprint matches leader's exactly.
            5. For deterministic elements, validator's SAME/not-SAME decision MUST equal leader's.
            6. For model elements, validator runs its OWN model classification in sandbox,
               and verifies element statuses equal leader's statuses.
            7. Verifies cited quote is verbatim substring of validator's re-derived passages.
            8. For ABSENT elements, validator confirms absence discipline holds on its own text.
            9. Verifies canonical enumeration summary matches validator's expected canonical string.
            """
            if not isinstance(leaders_res, gl.vm.Return):
                return False

            raw_leader = leaders_res.calldata
            if not isinstance(raw_leader, str):
                return False

            if raw_leader.startswith("FAIL|"):
                if raw_leader == "FAIL|SOURCE_UNAVAILABLE":
                    def val_fail_fetch() -> tuple[str, str]:
                        return _fetch_page_text(canonical_target_url)
                    sand_res = gl.vm.spawn_sandbox(val_fail_fetch)
                    if not isinstance(sand_res, gl.vm.Return):
                        return True
                    val_clean_full, _ = sand_res.calldata
                    return not val_clean_full or not val_clean_full.strip()

                if raw_leader == "FAIL|ABSENCE_UNSUPPORTED":
                    def val_absence_fetch() -> tuple[str, str]:
                        return _fetch_page_text(canonical_target_url)
                    sand_res = gl.vm.spawn_sandbox(val_absence_fetch)
                    if not isinstance(sand_res, gl.vm.Return):
                        return False
                    val_clean_full, _ = sand_res.calldata
                    if not val_clean_full or not val_clean_full.strip():
                        return False
                    val_norm_full = _normalize_text(val_clean_full)
                    step = WINDOW_SIZE_CHARS - WINDOW_OVERLAP_CHARS
                    for e in elements:
                        nq = norm_quotes_map[e["id"]]
                        if nq not in val_norm_full:
                            raw_q = raw_quotes_map[e["id"]]
                            for w_start in range(0, len(val_norm_full), step):
                                w_chunk = val_norm_full[w_start:w_start + WINDOW_SIZE_CHARS]
                                score = _compute_relevance_score(raw_q, w_chunk)
                                if score >= RELEVANCE_THRESHOLD:
                                    return True
                    return False

                if raw_leader in ("FAIL|INVALID_MODEL_OUTPUT", "FAIL|CITED_QUOTE_NOT_VERBATIM"):
                    def val_test_fail() -> tuple[str, str]:
                        return _fetch_page_text(canonical_target_url)
                    sand_res = gl.vm.spawn_sandbox(val_test_fail)
                    if not isinstance(sand_res, gl.vm.Return):
                        return True
                    val_clean_full, _ = sand_res.calldata
                    if not val_clean_full or not val_clean_full.strip():
                        return True
                    val_norm_full = _normalize_text(val_clean_full)
                    val_unres = [e["id"] for e in elements if norm_quotes_map[e["id"]] not in val_norm_full]
                    if not val_unres:
                        return False
                    val_unres_raw = [raw_quotes_map[eid] for eid in val_unres]
                    val_inspected, _, _, _, _, _ = _select_windows_for_quotes(val_clean_full, val_unres_raw)
                    val_passages = _segment_passages(val_inspected)

                    def val_model_probe() -> tuple[str, dict]:
                        return _classify_unresolved_elements(val_passages, val_unres, raw_quotes_map, val_norm_full)
                    probe_res = gl.vm.spawn_sandbox(val_model_probe)
                    if not isinstance(probe_res, gl.vm.Return):
                        return True
                    probe_code, _ = probe_res.calldata
                    return probe_code != "OK"

                return False

            if not raw_leader.startswith("OK|") or "\n---\n" not in raw_leader:
                return False

            leader_header, raw_payload = raw_leader.split("\n---\n", 1)
            leader_canonical = leader_header[len("OK|"):]

            try:
                leader_data = json.loads(raw_payload)
            except Exception:
                return False

            def val_fetch_fn() -> tuple[str, str]:
                return _fetch_page_text(canonical_target_url)

            sand_res = gl.vm.spawn_sandbox(val_fetch_fn)
            if not isinstance(sand_res, gl.vm.Return):
                return False

            val_clean_full, _ = sand_res.calldata
            if not val_clean_full or not val_clean_full.strip():
                return False

            val_norm_full = _normalize_text(val_clean_full)
            val_fingerprint = hashlib.sha256(val_norm_full.encode("utf-8")).hexdigest()

            if target_kind == "REVISION":
                if val_fingerprint != leader_data.get("target_text_sha256"):
                    return False

            leader_elements = leader_data.get("elements", [])
            leader_elems_by_id = {le["id"]: le for le in leader_elements if isinstance(le, dict) and "id" in le}
            if len(leader_elems_by_id) != len(elements):
                return False

            val_unresolved_ids = []
            for e in elements:
                eid = e["id"]
                if eid not in leader_elems_by_id:
                    return False
                le = leader_elems_by_id[eid]
                val_is_same = norm_quotes_map[eid] in val_norm_full
                leader_is_same = (le.get("status") == "SAME")

                if val_is_same != leader_is_same:
                    return False
                if val_is_same and le.get("decided_by") != "DETERMINISTIC":
                    return False

                if not val_is_same:
                    val_unresolved_ids.append(eid)

            leader_class = leader_data.get("class")
            statuses = [leader_elems_by_id[e["id"]].get("status") for e in elements]
            try:
                expected_class = _map_element_statuses_to_class(statuses)
            except Exception:
                return False

            if expected_class != leader_class:
                return False

            expected_fp = val_fingerprint if target_kind == "REVISION" else "NONE"
            expected_summary = "|".join(f"{e['id']}:{leader_elems_by_id[e['id']].get('status')}" for e in elements)
            expected_canonical = f"{expected_class}|{expected_fp}|{expected_summary}"

            if leader_canonical != expected_canonical:
                return False

            if val_unresolved_ids:
                val_unresolved_raw = [raw_quotes_map[eid] for eid in val_unresolved_ids]
                val_inspected, _, _, _, _, _ = _select_windows_for_quotes(val_clean_full, val_unresolved_raw)
                val_passages = _segment_passages(val_inspected)
                val_norm_passages = [_normalize_text(p["text"]) for p in val_passages]

                def val_classify_fn() -> tuple[str, dict]:
                    return _classify_unresolved_elements(
                        val_passages,
                        val_unresolved_ids,
                        raw_quotes_map,
                        val_norm_full,
                    )

                sand_model_res = gl.vm.spawn_sandbox(val_classify_fn)
                if not isinstance(sand_model_res, gl.vm.Return):
                    return False

                val_code, val_model_results = sand_model_res.calldata
                if val_code != "OK":
                    return False

                for eid in val_unresolved_ids:
                    le = leader_elems_by_id[eid]
                    leader_st = le.get("status")
                    val_elem = val_model_results.get(eid)
                    if not val_elem or val_elem.get("status") != leader_st:
                        return False

                    if leader_st in ("REPHRASED", "CHANGED"):
                        cq = le.get("cited_quote")
                        if not cq or not isinstance(cq, str) or len(cq.strip()) < 10:
                            return False
                        norm_cq = _normalize_text(cq)
                        if not any(norm_cq in vp for vp in val_norm_passages):
                            return False

                    elif leader_st == "ABSENT":
                        if le.get("cited_quote") is not None or le.get("passage_id") is not None:
                            return False
                        raw_q = raw_quotes_map[eid]
                        step = WINDOW_SIZE_CHARS - WINDOW_OVERLAP_CHARS
                        for w_start in range(0, len(val_norm_full), step):
                            w_chunk = val_norm_full[w_start:w_start + WINDOW_SIZE_CHARS]
                            score = _compute_relevance_score(raw_q, w_chunk)
                            if score >= RELEVANCE_THRESHOLD:
                                return False
                    else:
                        return False

            return True

        consensus_res = gl.vm.run_nondet_unsafe(leader_audit_eval, validator_audit_eval)
        if not consensus_res or not consensus_res.startswith("OK|"):
            if consensus_res.startswith("FAIL|SOURCE_UNAVAILABLE"):
                raise gl.vm.UserError("source unavailable")
            if consensus_res.startswith("FAIL|ABSENCE_UNSUPPORTED"):
                raise gl.vm.UserError("coverage insufficient to conclude absence")
            if consensus_res.startswith("FAIL|CITED_QUOTE_NOT_VERBATIM"):
                raise gl.vm.UserError("cited quote not found verbatim in presented passage")
            if consensus_res.startswith("FAIL|INVALID_MODEL_OUTPUT"):
                raise gl.vm.UserError("invalid model output")
            raise gl.vm.UserError("audit evaluation failed")

        if "\n---\n" not in consensus_res:
            raise gl.vm.UserError("audit evaluation payload missing")

        header, raw_audit_data = consensus_res.split("\n---\n", 1)
        canonical_summary = header[len("OK|"):]
        audit_payload = json.loads(raw_audit_data)

        audit_number = len(audits) + 1
        audit_class = audit_payload["class"]

        audit_entry = {
            "n": audit_number,
            "auditor": sender,
            "audited_at": now_str,
            "audited_at_ts": current_ts,
            "target_url": canonical_target_url,
            "target_kind": target_kind,
            "target_oldid": target_oldid,
            "class": audit_class,
            "elements": audit_payload["elements"],
            "passages": audit_payload["passages"],
            "target_text_sha256": audit_payload["target_text_sha256"],
            "presented_segment_ids": audit_payload["presented_segment_ids"],
            "presented_segments_count": audit_payload["presented_segments_count"],
            "source_chars_total": audit_payload["source_chars_total"],
            "source_chars_inspected": audit_payload["source_chars_inspected"],
            "chars_scanned": audit_payload["chars_scanned"],
            "budget_chars_used": audit_payload["budget_chars_used"],
            "truncated_at": audit_payload["truncated_at"],
            "coverage": audit_payload["coverage"],
            "fetch_method": audit_payload["fetch_method"],
            "fingerprint_in_consensus": audit_payload["fingerprint_in_consensus"],
        }

        updated_audits = list(audits)
        updated_audits.append(audit_entry)

        final_audits = []
        total_count = len(updated_audits)
        for idx, a in enumerate(updated_audits):
            if idx < total_count - MAX_FULL_AUDITS:
                compact = {
                    "n": a["n"],
                    "auditor": a["auditor"],
                    "audited_at": a["audited_at"],
                    "audited_at_ts": a["audited_at_ts"],
                    "target_url": a["target_url"],
                    "target_kind": a["target_kind"],
                    "target_oldid": a["target_oldid"],
                    "class": a["class"],
                    "summary_only": True,
                }
                final_audits.append(compact)
            else:
                final_audits.append(a)

        if len(final_audits) > MAX_AUDIT_SUMMARIES:
            final_audits = final_audits[-MAX_AUDIT_SUMMARIES:]

        record["audits"] = final_audits
        record["audits_total"] = record.get("audits_total", 0) + 1
        record["latest_audit_index"] = len(final_audits) - 1
        record["status"] = _map_class_to_status(audit_class)

        self.citations[cid] = json.dumps(record)

        if target_kind == "REVISION":
            self.audited_revisions[f"{cid}:{target_oldid}"] = audit_class
