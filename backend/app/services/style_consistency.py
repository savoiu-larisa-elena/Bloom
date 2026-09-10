from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from app.services.linguistics import _lemma, _pos_tag

_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def _first_sentence_word(sentence: str) -> str | None:
    """First alphabetic token after optional opening quotes / dash."""
    s = sentence.lstrip()
    s = re.sub(r'^[\s"\u201c\u2018\u2014\-]+', "", s)
    m = _WORD_RE.match(s)
    return m.group(0) if m else None


_PASSIVE_BE = re.compile(
    r"(?i)\b(?:am|is|are|was|were|be|been|being)\s+([a-z]{3,})\b",
)


def _passive_like_hits(sentence: str) -> int:
    n = 0
    for m in _PASSIVE_BE.finditer(sentence):
        w = m.group(1).lower()
        if w.endswith("ing"):
            continue
        if w.endswith("ed") or w.endswith("en"):
            n += 1
            continue
        if w in {
            "gone",
            "done",
            "seen",
            "taken",
            "given",
            "known",
            "shown",
            "born",
            "shut",
            "sung",
            "run",
            "beat",
        }:
            n += 1
    return min(n, 3)


def analyse_style_consistency(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        return {"enabled": True, "unavailable": True, "error": "Empty text"}

    sentences = _split_sentences(stripped)
    if not sentences:
        sentences = [stripped]

    sentence_lengths = [len(_WORD_RE.findall(s)) for s in sentences]
    mean_len = sum(sentence_lengths) / len(sentence_lengths)
    var = sum((x - mean_len) ** 2 for x in sentence_lengths) / max(len(sentence_lengths), 1)
    std = math.sqrt(var)
    coeff_var = std / mean_len if mean_len > 0 else 0.0

    words_lower = [w.lower() for w in _WORD_RE.findall(stripped)]
    unique_ratio = len(set(words_lower)) / max(len(words_lower), 1)

    lemmas: list[str] = []
    for w in _WORD_RE.findall(stripped):
        lemmas.append(_lemma(w.lower()))
    lemma_ttr = len(set(lemmas)) / max(len(lemmas), 1) if lemmas else 0.0

    starters: list[str] = []
    starter_pos_tags: list[str] = []
    passive_sentence_hits = 0
    for s in sentences:
        fw = _first_sentence_word(s)
        if fw:
            starters.append(fw.lower())
            starter_pos_tags.append(_pos_tag(fw))
        passive_sentence_hits += _passive_like_hits(s)

    repeated_starters = [f"{w} ({c}×)" for w, c in Counter(starters).most_common(5) if c >= 2]
    pos_counts = Counter(starter_pos_tags)
    repeated_starter_pos = [
        f"{tag} ({c}×)" for tag, c in pos_counts.most_common(8) if c >= 2
    ]
    sentence_starter_pos_counts = dict(pos_counts.most_common(12))

    passive_like_ratio = round(
        sum(1 for s in sentences if _passive_like_hits(s) > 0) / max(len(sentences), 1),
        3,
    )

    consistency_score = max(0.0, min(100.0, 100.0 - coeff_var * 85.0))

    return {
        "enabled": True,
        "unavailable": False,
        "consistency_score": round(consistency_score, 2),
        "sentence_length_mean": round(mean_len, 2),
        "sentence_length_std": round(std, 2),
        "lexical_diversity_ttr": round(unique_ratio, 3),
        "lexical_diversity_lemma_ttr": round(lemma_ttr, 3),
        "passive_like_hits_total": passive_sentence_hits,
        "passive_like_sentence_ratio": passive_like_ratio,
        "sentence_starter_pos_counts": sentence_starter_pos_counts,
        "repeated_sentence_starter_pos": repeated_starter_pos,
        "repeated_sentence_starters": repeated_starters,
        "note": (
            "Heuristic metrics: surface and lemma-type TTR, sentence-length rhythm, "
            "coarse POS of first word per sentence (not full parsing), and passive-like "
            "be+participle patterns (approximate; many false positives/negatives possible)."
        ),
    }
