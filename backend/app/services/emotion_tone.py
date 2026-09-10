from __future__ import annotations

import os
from typing import Any

_DEFAULT_EMOTION_MODEL = "j-hartmann/emotion-english-distilroberta-base"


def _emotion_model_name() -> str:
    return (
        os.environ.get("BLOOM_EMOTION_MODEL", _DEFAULT_EMOTION_MODEL).strip()
        or _DEFAULT_EMOTION_MODEL
    )

_ENABLE_EMOTION = os.environ.get("BLOOM_ENABLE_EMOTION", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

_MAX_EMOTION_CHARS = int(os.environ.get("BLOOM_EMOTION_MAX_CHARS", "32000"))

_emotion_tokenizer: Any = None
_emotion_model: Any = None
_device: Any = None

_EMOTION_LABEL_TO_SUMMARY: dict[str, str] = {
    "joy": "Upbeat and positive in mood.",
    "sadness": "Reflective or sombre in tone.",
    "anger": "Sharp or frustrated in tone.",
    "fear": "Uneasy or tense in mood.",
    "surprise": "Lively or surprised in tone.",
    "disgust": "Critical or disapproving in tone.",
    "neutral": "Fairly neutral in emotional tone.",
}


def _get_device():
    global _device
    if _device is None:
        import torch

        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return _device


def _load_emotion():
    global _emotion_tokenizer, _emotion_model
    if _emotion_model is None:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        name = _emotion_model_name()
        _emotion_tokenizer = AutoTokenizer.from_pretrained(name)
        _emotion_model = AutoModelForSequenceClassification.from_pretrained(name)
        _emotion_model.eval()
        _emotion_model = _emotion_model.to(_get_device())
    return _emotion_tokenizer, _emotion_model


def _truncate(s: str, max_chars: int) -> str:
    s = s.strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1].rstrip() + "…"


def analyse_emotion_tone(text: str) -> dict[str, Any]:
    """Return dominant emotion label, score map, and a one-line summary."""
    if not _ENABLE_EMOTION:
        return {
            "enabled": False,
            "note": "Emotion/tone is disabled (BLOOM_ENABLE_EMOTION=false).",
        }

    stripped = text.strip()
    if not stripped:
        return {"enabled": True, "unavailable": True, "error": "Empty text"}

    snippet = _truncate(stripped, _MAX_EMOTION_CHARS)

    try:
        import torch
        import torch.nn.functional as F

        tok, model = _load_emotion()
        device = _get_device()
        inputs = tok(
            snippet,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            logits = model(**inputs).logits
        probs = F.softmax(logits[0], dim=-1)
        id2label = model.config.id2label
        scores: dict[str, float] = {
            id2label[i]: round(float(probs[i].item()), 4) for i in range(len(probs))
        }
        sorted_labels = sorted(scores.items(), key=lambda x: -x[1])
        dominant = sorted_labels[0][0]
        summary = _EMOTION_LABEL_TO_SUMMARY.get(
            dominant,
            f"Dominant mood label: {dominant}.",
        )
        if len(sorted_labels) > 1 and sorted_labels[1][1] >= 0.2:
            runner = sorted_labels[1][0]
            if runner != dominant:
                summary = f"{summary} A hint of {runner} as well."

        return {
            "enabled": True,
            "unavailable": False,
            "model": _emotion_model_name(),
            "dominant_emotion": dominant,
            "emotion_scores": scores,
            "summary": summary,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "enabled": True,
            "unavailable": True,
            "error": str(exc),
            "model": _emotion_model_name(),
            "hint": "pip install torch transformers",
        }
