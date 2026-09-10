from __future__ import annotations

import os
import re
from difflib import SequenceMatcher
from typing import Any

_DEFAULT_MODEL = "vennify/t5-base-grammar-correction"

_ENABLED_RAW = os.environ.get("BLOOM_ENABLE_NEURAL_GRAMMAR", "true").strip().lower()
NEURAL_GRAMMAR_ENABLED: bool = _ENABLED_RAW in ("1", "true", "yes", "on")

MAX_SENTENCES = int(os.environ.get("BLOOM_NEURAL_MAX_SENTENCES", "40"))
MAX_INPUT_CHARS_PER_SENT = int(os.environ.get("BLOOM_NEURAL_MAX_CHARS_PER_SENT", "512"))

_NEURAL_NUM_BEAMS = int(os.environ.get("BLOOM_NEURAL_NUM_BEAMS", "8"))
_NEURAL_MAX_GEN_LENGTH = int(os.environ.get("BLOOM_NEURAL_MAX_GEN_LENGTH", "256"))
_NEURAL_REP_PEN = float(os.environ.get("BLOOM_NEURAL_REPETITION_PENALTY", "1.15"))

LIMITATIONS_BLURB = (
    "Public GEC models are trained mostly on learner essays (e.g. JFLEG), not fiction or poetry. "
    "They often use American spelling (e.g. spelled). Bloom defaults to British variant post-processing. "
    "Use as hints; trust LanguageTool for rules and your own judgment for voice."
)

_model: Any = None
_tokenizer: Any = None
_device: Any = None
_model_name: str = _DEFAULT_MODEL


def _get_model_name() -> str:
    return os.environ.get("BLOOM_NEURAL_GRAMMAR_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL


def _get_model_and_tokenizer():
    """Lazy-load T5 + tokenizer (first call downloads ~900MB model)."""
    global _model, _tokenizer, _model_name, _device
    if _model is None:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        _model_name = _get_model_name()
        _tokenizer = AutoTokenizer.from_pretrained(_model_name)
        _model = AutoModelForSeq2SeqLM.from_pretrained(_model_name)
        _model.eval()
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        _model = _model.to(_device)

    return _model, _tokenizer, _model_name


def _dup_typo_score(segment: str) -> int:
    """Higher = more likely garbled; used to pick the better of two duplicate hypotheses."""
    t = segment.lower()
    score = len(re.findall(r"\bi\b", segment))
    score += len(re.findall(r"([a-z])\1", t))
    return score


def _pick_better_duplicate(left: str, right: str) -> str:
    """
    Model often prints two parallel versions separated by ' - '; order is inconsistent.
    Prefer the side with fewer obvious typos (worrd, lowercase i as pronoun).
    On a tie, prefer the second span (often the refined beam).
    """
    left, right = left.strip(), right.strip()
    if not left:
        return right
    if not right:
        return left
    ratio = SequenceMatcher(None, left.lower(), right.lower()).ratio()
    if ratio < 0.48:
        return f"{left} - {right}"

    sl, sr = _dup_typo_score(left), _dup_typo_score(right)
    if sl < sr:
        return left
    if sr < sl:
        return right
    return right


def _apply_english_variant(s: str) -> str:
    """Optional British spelling (verb spell → spelt). Env: BLOOM_ENGLISH_VARIANT=uk|gb|british."""
    v = os.environ.get("BLOOM_ENGLISH_VARIANT", "uk").strip().lower()
    if v not in ("uk", "gb", "british"):
        return s

    def _spelled_to_spelt(m: re.Match[str]) -> str:
        w = m.group(0)
        return "Spelt" if w[0].isupper() else "spelt"

    return re.sub(r"\bspelled\b", _spelled_to_spelt, s, flags=re.IGNORECASE)


def _postprocess_gec(s: str) -> str:
    """
    T5 GEC sometimes emits two near-duplicate sentences joined by ' - '.
    Pick the cleaner hypothesis; fix pronoun i -> I; optional UK spelling.
    """
    s = s.strip()
    if not s:
        return s

    if " - " in s:
        left, right = s.split(" - ", 1)
        left, right = left.strip(), right.strip()
        if left and right and min(len(left), len(right)) >= 8:
            ratio = SequenceMatcher(None, left.lower(), right.lower()).ratio()
            if ratio >= 0.48:
                s = _pick_better_duplicate(left, right)

    s = re.sub(r"\bi\b", "I", s)
    s = _apply_english_variant(s)
    return s.strip()


def _correct_sentence(model: Any, tokenizer: Any, device: Any, sent: str) -> str:
    import torch

    prefix = "grammar: "
    inp = prefix + sent
    inputs = tokenizer(inp, return_tensors="pt", truncation=True, max_length=256)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    gen_kwargs: dict[str, Any] = {
        "max_length": _NEURAL_MAX_GEN_LENGTH,
        "num_beams": max(1, _NEURAL_NUM_BEAMS),
        "do_sample": False,
        "early_stopping": True,
    }
    if _NEURAL_REP_PEN > 1.0:
        gen_kwargs["repetition_penalty"] = _NEURAL_REP_PEN

    with torch.no_grad():
        outputs = model.generate(**inputs, **gen_kwargs)

    raw = tokenizer.decode(outputs[0].cpu(), skip_special_tokens=True).strip()
    return _postprocess_gec(raw)


def _split_sentences(text: str) -> list[str]:
    """Simple English sentence split (good enough for paragraphs)."""
    text = text.strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _normalize_ws(s: str) -> str:
    return " ".join(s.split())


def neural_grammar_correct(text: str) -> dict[str, Any]:
    """
    Run seq2seq GEC: returns corrected paragraph + metadata.

    If BLOOM_ENABLE_NEURAL_GRAMMAR=false, returns disabled payload without loading torch.
    """
    if not NEURAL_GRAMMAR_ENABLED:
        return {
            "enabled": False,
            "model": None,
            "corrected_text": None,
            "changed": False,
            "note": "Neural grammar is disabled (BLOOM_ENABLE_NEURAL_GRAMMAR=false).",
        }

    stripped = text.strip()
    if not stripped:
        return {
            "enabled": True,
            "unavailable": True,
            "error": "Empty text",
            "model": _get_model_name(),
        }

    try:
        model, tokenizer, model_name = _get_model_and_tokenizer()
        dev = _device
    except Exception as exc:  # noqa: BLE001
        return {
            "enabled": True,
            "unavailable": True,
            "error": str(exc),
            "model": _get_model_name(),
            "hint": "Install: pip install torch transformers sentencepiece",
        }

    sentences = _split_sentences(stripped)
    if not sentences:
        sentences = [stripped]
    if len(sentences) > MAX_SENTENCES:
        sentences = sentences[:MAX_SENTENCES]
        truncated = True
    else:
        truncated = False

    corrected_parts: list[str] = []

    for sent in sentences:
        if len(sent) > MAX_INPUT_CHARS_PER_SENT:
            sent = sent[:MAX_INPUT_CHARS_PER_SENT]
        try:
            gen = _correct_sentence(model, tokenizer, dev, sent)
        except Exception as exc:  # noqa: BLE001
            return {
                "enabled": True,
                "unavailable": True,
                "error": str(exc),
                "model": model_name,
            }
        corrected_parts.append(gen if gen else sent)

    corrected_text = _postprocess_gec(" ".join(corrected_parts))
    orig_n = _normalize_ws(stripped)
    cor_n = _normalize_ws(corrected_text)
    changed = orig_n != cor_n

    payload: dict[str, Any] = {
        "enabled": True,
        "unavailable": False,
        "model": model_name,
        "task": "seq2seq_generate (T5)",
        "training_note": "Fine-tuned T5 on JFLEG-style grammatical error correction.",
        "limitations": LIMITATIONS_BLURB,
        "decode_settings": {
            "num_beams": max(1, _NEURAL_NUM_BEAMS),
            "max_gen_length": _NEURAL_MAX_GEN_LENGTH,
            "repetition_penalty": _NEURAL_REP_PEN if _NEURAL_REP_PEN > 1.0 else None,
        },
        "corrected_text": corrected_text,
        "changed": changed,
        "sentences_processed": len(sentences),
        "truncated": truncated,
    }
    if truncated:
        payload["warning"] = (
            f"Only the first {MAX_SENTENCES} sentences were processed (configurable)."
        )
    return payload
