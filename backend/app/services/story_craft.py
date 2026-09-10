from __future__ import annotations

import os
import re
from collections import Counter
from typing import Any

_STOP_CAPITALISED: frozenset[str] = frozenset(
    {
        "The",
        "A",
        "An",
        "And",
        "But",
        "Or",
        "If",
        "When",
        "While",
        "After",
        "Before",
        "Then",
        "She",
        "He",
        "They",
        "We",
        "It",
        "I",
        "You",
        "His",
        "Her",
        "Their",
        "My",
        "Your",
        "Our",
        "This",
        "That",
        "There",
        "Here",
        "What",
        "Who",
        "How",
        "Why",
        "One",
        "Two",
        "Some",
        "Every",
        "Each",
        "All",
        "No",
        "Not",
        "So",
        "As",
        "In",
        "On",
        "At",
        "To",
        "From",
        "With",
        "For",
        "Of",
        "By",
        "Into",
        "Over",
        "Under",
        "Again",
        "Still",
        "Just",
        "Even",
        "Only",
        "Very",
        "Now",
        "Today",
        "Tomorrow",
        "Yesterday",
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
        "Mr",
        "Mrs",
        "Ms",
        "Dr",
        "Did",
        "Do",
        "Does",
        "Done",
        "Be",
        "Been",
        "Being",
        "Was",
        "Were",
        "Is",
        "Are",
        "Am",
        "Had",
        "Have",
        "Has",
        "Having",
        "Can",
        "Could",
        "Would",
        "Should",
        "May",
        "Might",
        "Must",
        "Shall",
        "Will",
        "O",
        "Professor",
        "Prof",
        "Sir",
        "Lady",
        "Lord",
        "Madam",
        "Miss",
        "Master",
        "Captain",
        "Capt",
        "Colonel",
        "Col",
        "General",
        "Gen",
        "Lieutenant",
        "Lt",
        "Sergeant",
        "Sgt",
        "Officer",
        "Judge",
        "President",
        "King",
        "Queen",
        "Prince",
        "Princess",
        "Duke",
        "Duchess",
        "Suddenly",
        "Meanwhile",
        "However",
        "Therefore",
        "Moreover",
        "Nevertheless",
        "Finally",
        "Later",
        "Earlier",
        "Eventually",
        "Perhaps",
        "Maybe",
        "Indeed",
        "Someone",
        "Anyone",
        "Everyone",
        "Nobody",
        "Nothing",
        "Something",
        "Everything",
        "Grandmother",
        "Grandfather",
        "Grandma",
        "Grandpa",
        "Aunt",
        "Uncle",
        "Cousin"
    }
)

_NAME_RE = re.compile(r"\b([A-Z][a-z]{2,})\b")

_FEMALE_FIRST: frozenset[str] = frozenset(
    {
        "maya", "emma", "olivia", "sophia", "ava", "isabella", "mia", "charlotte",
        "amelia", "harper", "evelyn", "abigail", "ella", "lily", "grace", "chloe",
        "victoria", "aria", "luna", "hannah", "sarah", "rachel", "leah", "clara",
        "nora", "ivy", "zoe", "zoey", "ruby", "alice", "anna", "beth", "claire",
        "diana", "elena", "fiona", "gina", "helen", "iris", "jane", "julia", "kate",
        "laura", "lisa", "maria", "mary", "nina", "olga", "petra", "rosa", "sara",
        "tessa", "vera", "willa", "yara", "zara", "lucy", "meg", "meggie", "nell",
    }
)
_MALE_FIRST: frozenset[str] = frozenset(
    {
        "eli", "elijah", "noah", "liam", "jacob", "mason", "ethan", "james",
        "benjamin", "lucas", "henry", "alexander", "jack", "daniel", "owen", "samuel",
        "david", "joseph", "john", "michael", "thomas", "chris", "christopher",
        "matthew", "andrew", "ryan", "adam", "aaron", "brad", "brian", "carl", "dan",
        "eric", "felix", "george", "harry", "ian", "jake", "jason", "jordan",
        "kevin", "leo", "luke", "marcus", "mark", "nate", "nathan", "oscar", "paul",
        "peter", "robert", "sean", "simon", "steve", "tim", "tom", "tyler", "victor",
        "will", "william", "zach", "zachary",
    }
)


def _name_guess_gender(name: str) -> str | None:
    """Return 'f', 'm', or None if unknown."""
    low = name.lower()
    if low in _FEMALE_FIRST:
        return "f"
    if low in _MALE_FIRST:
        return "m"
    return None


def _pronoun_class(low: str) -> str | None:
    if low in {"she", "her", "hers", "herself"}:
        return "f"
    if low in {"he", "him", "his", "himself"}:
        return "m"
    if low in {"they", "them", "their", "theirs", "themself", "themselves"}:
        return "p"
    return None


def _gender_compatible(name_g: str | None, pron_c: str) -> bool:
    """Block obvious cross-gender links when both are known."""
    if pron_c == "p":
        return True
    if name_g is None:
        return True
    if pron_c == "f" and name_g == "m":
        return False
    if pron_c == "m" and name_g == "f":
        return False
    return True


def _coref_max_lookback_chars() -> int:
    raw = os.environ.get("BLOOM_COREF_MAX_LOOKBACK_CHARS", "").strip()
    if raw.isdigit():
        return max(500, min(int(raw), 2_000_000))
    return 2_000_000


def _strip_noise(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _is_person_name_token(tok: str) -> bool:
    return tok not in _STOP_CAPITALISED


def analyse_characters(text: str) -> dict[str, Any]:
    """
    Estimate recurring proper-noun-like tokens as *possible* character names.
    Not NER — heuristic only; false positives/negatives are expected.
    """
    t = _strip_noise(text)
    if not t.strip():
        return {
            "enabled": True,
            "candidates": [],
            "note": "Paste some story text to see name-like words that repeat.",
        }

    raw = _NAME_RE.findall(t)
    counts = Counter(w for w in raw if w not in _STOP_CAPITALISED)
    candidates = [{"name": w, "mentions": c} for w, c in counts.most_common(12) if c >= 2]

    note = (
        "Heuristic only: repeated capitalised words may be characters, places, or ships — "
        "not a substitute for careful human editing."
    )
    return {
        "enabled": True,
        "candidates": candidates,
        "distinct_recurring": len(candidates),
        "note": note,
    }


def _segments_in_curly_or_straight_quotes(text: str) -> list[str]:
    """Extract quoted spans (straight \"…\", curly “…” or ‘…’, and simple 'dialogue')."""
    spans: list[str] = []

    for m in re.finditer(r'"([^"]{1,4000})"', text):
        spans.append(m.group(1).strip())

    oq, cq = "\u201c", "\u201d"
    for m in re.finditer(oq + "([^" + cq + "]{1,4000})" + cq, text):
        spans.append(m.group(1).strip())

    sq_o, sq_c = "\u2018", "\u2019"
    for m in re.finditer(sq_o + "([^" + sq_c + "]{1,4000})" + sq_c, text):
        spans.append(m.group(1).strip())

    return [s for s in spans if s]


def analyse_dialogue(text: str) -> dict[str, Any]:
    """
    Rough dialogue vs narration split using quoted spans.
    """
    t = _strip_noise(text)
    if not t.strip():
        return {
            "enabled": True,
            "quoted_segments": 0,
            "dialogue_char_ratio": 0.0,
            "note": "Paste text with double quotes around spoken lines for dialogue stats.",
        }

    quoted = _segments_in_curly_or_straight_quotes(t)
    q_chars = sum(len(s) for s in quoted)
    total = max(len(t.replace("\n", " ").strip()), 1)
    ratio = round(q_chars / total, 3)

    tips: list[str] = []
    if not quoted:
        tips.append("No quoted speech detected — if characters speak, try wrapping lines in “double quotes”.")
    elif ratio < 0.05:
        tips.append("Very little text is inside quotes — check whether you want more spoken dialogue on the page.")
    elif ratio > 0.55:
        tips.append("A large share of the paragraph is dialogue — make sure action and interiority still ground the scene.")

    avg_len = round(sum(len(s) for s in quoted) / len(quoted), 1) if quoted else 0.0

    return {
        "enabled": True,
        "quoted_segments": len(quoted),
        "dialogue_char_ratio": ratio,
        "avg_quoted_segment_chars": avg_len,
        "preview": quoted[:3],
        "tips": tips,
        "note": "Quote detection is literal (punctuation-based), not semantic turn-taking.",
    }


def analyse_coreference(text: str) -> dict[str, Any]:
    """
    Lightweight coreference: link each gendered pronoun to the **closest preceding**
    capitalised name (character-like token), with **gender compatibility** when the name
    is in a small lexicon — avoids obvious errors like *her* → Eli.

    Scans the **full** pasted text (see BLOOM_COREF_MAX_LOOKBACK_CHARS for how far back
    a name may bind; default is effectively the whole document).
    """
    t = _strip_noise(text)
    if not t.strip():
        return {
            "enabled": True,
            "links": [],
            "note": "Paste text to estimate simple pronoun-to-name links.",
        }

    titlecase_mentions = list(_NAME_RE.finditer(t))
    titlecase_counts = Counter(
        m.group(1) for m in titlecase_mentions if _is_person_name_token(m.group(1))
    )
    names: set[str] = set()
    for m in titlecase_mentions:
        name = m.group(1)
        if not _is_person_name_token(name):
            continue
        after = t[m.end() : m.end() + 20]
        followed_by_number = bool(re.match(r"\s+\d", after))
        if titlecase_counts[name] == 1 and followed_by_number:
            continue
        names.add(name)

    name_spans: list[tuple[int, int, str]] = []
    for m in titlecase_mentions:
        name = m.group(1)
        if name not in names:
            continue
        name_spans.append((m.start(), m.end(), name))
    name_spans.sort(key=lambda x: x[0])

    max_back = _coref_max_lookback_chars()
    token_re = re.compile(r"\b[A-Za-z]+\b")
    links: list[dict[str, str]] = []
    tokens = list(token_re.finditer(t))

    def resolve_pronoun(low: str, pron_start: int) -> str | None:
        pc = _pronoun_class(low)
        if pc is None:
            return None
        candidates = [
            (ns, ne, nm)
            for ns, ne, nm in name_spans
            if ne <= pron_start and (pron_start - ne) <= max_back
        ]
        candidates.sort(key=lambda x: -x[1])
        for _, _, nm in candidates:
            ng = _name_guess_gender(nm)
            if _gender_compatible(ng, pc):
                return nm
        return None

    for m in tokens:
        tok = m.group(0)
        low = tok.lower()
        if tok in names and _is_person_name_token(tok):
            continue
        pc = _pronoun_class(low)
        if pc is None:
            continue
        guess = resolve_pronoun(low, m.start())
        if guess:
            links.append({"pronoun": low, "antecedent_guess": guess})

    return {
        "enabled": True,
        "links": links[:40],
        "link_count": len(links),
        "note": (
            "Heuristic coreference: each pronoun is linked to the nearest preceding name-like "
            "token within the lookback window, with gender filtering when the name is known "
            "to the lexicon. Unknown names still match any pronoun — expect errors on rare names."
        ),
    }
