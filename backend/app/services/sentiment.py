from __future__ import annotations

import re
from typing import Any

_POSITIVE_WORDS: set[str] = {
    "good",
    "great",
    "happy",
    "joy",
    "love",
    "calm",
    "hope",
    "kind",
    "brave",
    "warm",
    "smile",
    "beautiful",
    "wonderful",
    "excellent",
    "peaceful",
    "gentle",
    "safe",
    "friend",
    "friends",
    "laugh",
}

_NEGATIVE_WORDS: set[str] = {
    "bad",
    "sad",
    "angry",
    "fear",
    "hate",
    "cold",
    "pain",
    "hurt",
    "dark",
    "worry",
    "worried",
    "awful",
    "terrible",
    "horrible",
    "lonely",
    "cry",
    "cried",
    "danger",
    "lost",
    "broken",
}


def _tokenize_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z']+", text.lower())


def analyse_sentiment_polarity(text: str) -> dict[str, Any]:
    """Return a simple polarity signal (positive/neutral/negative)."""
    tokens = _tokenize_words(text)
    if not tokens:
        return {
            "enabled": True,
            "unavailable": True,
            "error": "Empty text",
        }

    pos_hits = sum(1 for t in tokens if t in _POSITIVE_WORDS)
    neg_hits = sum(1 for t in tokens if t in _NEGATIVE_WORDS)
    score = (pos_hits - neg_hits) / max(len(tokens), 1)

    if score > 0.02:
        label = "positive"
    elif score < -0.02:
        label = "negative"
    else:
        label = "neutral"

    return {
        "enabled": True,
        "unavailable": False,
        "label": label,
        "polarity_score": round(score, 4),
        "positive_hits": pos_hits,
        "negative_hits": neg_hits,
        "token_count": len(tokens),
        "note": "Lexicon-based polarity; lightweight baseline, not a deep sentiment model.",
    }
