from __future__ import annotations

import re
from collections import Counter
from typing import Any

_IRREGULAR_LEMMAS: dict[str, str] = {
    "children": "child",
    "mice": "mouse",
    "men": "man",
    "women": "woman",
    "went": "go",
    "gone": "go",
    "better": "good",
    "best": "good",
    "worse": "bad",
    "worst": "bad",
}

_VERB_HINTS = {"is", "am", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did"}
_PRONOUNS = {"i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them", "my", "your", "our", "their"}
_DETERMINERS = {"a", "an", "the", "this", "that", "these", "those"}
_PREPOSITIONS = {"in", "on", "at", "to", "from", "for", "with", "by", "into", "over", "under", "about", "after", "before"}
_NER_TITLECASE_STOPWORDS = {
    "The",
    "A",
    "An",
    "And",
    "But",
    "Or",
    "If",
    "When",
    "After",
    "Before",
    "Then",
    "Today",
    "Yesterday",
    "Tomorrow",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
}


def sentence_segment(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def word_tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?|\d+|[^\w\s]", text)


def _lemma(token: str) -> str:
    t = token.lower()
    if t in _IRREGULAR_LEMMAS:
        return _IRREGULAR_LEMMAS[t]
    if len(t) > 4 and t.endswith("ies"):
        return t[:-3] + "y"
    if len(t) > 4 and t.endswith("ing"):
        return t[:-3]
    if len(t) > 3 and t.endswith("ed"):
        return t[:-2]
    if len(t) > 3 and t.endswith("s"):
        return t[:-1]
    return t


def _pos_tag(token: str) -> str:
    t = token.lower()
    if re.fullmatch(r"[.!?,:;'\"]", token):
        return "PUNCT"
    if t.isdigit():
        return "NUM"
    if t in _PRONOUNS:
        return "PRON"
    if t in _DETERMINERS:
        return "DET"
    if t in _PREPOSITIONS:
        return "ADP"
    if t in _VERB_HINTS or t.endswith("ing") or t.endswith("ed"):
        return "VERB"
    if t.endswith("ly"):
        return "ADV"
    if t.endswith(("ous", "ful", "able", "ive", "al")):
        return "ADJ"
    if token[:1].isupper():
        return "PROPN"
    return "NOUN"


def _detect_named_entities(text: str) -> list[dict[str, str]]:
    entities: list[dict[str, str]] = []
    date_ranges: list[tuple[int, int]] = []

    _skip_titlecase_entity = frozenset(
        {"She", "He", "They", "You", "We", "It", "Her", "His", "Their", "Our", "Your", "My"}
    )
    for m in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", text):
        name = m.group(1)
        if name in _NER_TITLECASE_STOPWORDS or name in _skip_titlecase_entity:
            continue
        entities.append({"text": name, "label": "PERSON_OR_TITLECASE"})
    for m in re.finditer(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", text):
        entities.append({"text": m.group(0), "label": "DATE"})
        date_ranges.append((m.start(), m.end()))
    for m in re.finditer(r"\b\d+(?:\.\d+)?\b", text):
        if any(start <= m.start() and m.end() <= end for start, end in date_ranges):
            continue
        entities.append({"text": m.group(0), "label": "NUMBER"})

    uniq: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for ent in entities:
        key = (ent["text"], ent["label"])
        if key not in seen:
            seen.add(key)
            uniq.append(ent)
        if len(uniq) >= 20:
            break
    return uniq


def analyse_linguistics(text: str) -> dict[str, Any]:
    """Return basic preprocessing artifacts for thesis-aligned outputs."""
    stripped = text.strip()
    if not stripped:
        return {
            "enabled": True,
            "unavailable": True,
            "error": "Empty text",
        }

    sentences = sentence_segment(stripped)
    tokens = word_tokenize(stripped)
    word_tokens = [t for t in tokens if re.fullmatch(r"[A-Za-z]+(?:'[A-Za-z]+)?", t)]

    lemmas = [_lemma(t) for t in word_tokens]
    pos_tags = [{"token": t, "pos": _pos_tag(t)} for t in word_tokens[:120]]
    pos_counts = dict(Counter(tag["pos"] for tag in pos_tags))

    return {
        "enabled": True,
        "unavailable": False,
        "sentence_count": len(sentences),
        "sentences_preview": sentences[:5],
        "token_count": len(tokens),
        "tokens_preview": tokens[:40],
        "lemmas_preview": lemmas[:40],
        "pos_counts": pos_counts,
        "pos_preview": pos_tags[:40],
        "named_entities": _detect_named_entities(stripped),
        "note": "Rule-based approximation for preprocessing/NER; suitable for educational feedback.",
    }
