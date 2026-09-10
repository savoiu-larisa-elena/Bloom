from __future__ import annotations

import os
import re
from difflib import SequenceMatcher
from typing import Any

from app.services.grammar import check_grammar
from app.services.neural_grammar import neural_grammar_correct

_DEFAULT_PARAPHRASE_MODEL = "Vamsi/T5_Paraphrase_Paws"


def _paraphrase_model_name() -> str:
    return (
        os.environ.get("BLOOM_PARAPHRASE_MODEL", _DEFAULT_PARAPHRASE_MODEL).strip()
        or _DEFAULT_PARAPHRASE_MODEL
    )

_ENABLE_PARAPHRASE = os.environ.get("BLOOM_ENABLE_PARAPHRASE", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

_PARAPHRASE_MAX_CHARS = int(os.environ.get("BLOOM_PARAPHRASE_MAX_CHARS", "480"))
_PARAPHRASE_LEAD_MAX_CHARS = int(os.environ.get("BLOOM_PARAPHRASE_LEAD_MAX_CHARS", "220"))
_PARAPHRASE_ENABLE_POLISH = os.environ.get(
    "BLOOM_PARAPHRASE_ENABLE_POLISH",
    "true",
).strip().lower() in ("1", "true", "yes", "on")
_PARAPHRASE_MAX_SIMILARITY = float(os.environ.get("BLOOM_PARAPHRASE_MAX_SIMILARITY", "0.9"))
_PARAPHRASE_ENABLE_NEURAL_POLISH = os.environ.get(
    "BLOOM_PARAPHRASE_ENABLE_NEURAL_POLISH",
    "true",
).strip().lower() in ("1", "true", "yes", "on")

_para_tokenizer: Any = None
_para_model: Any = None
_device: Any = None


def _get_device():
    global _device
    if _device is None:
        import torch

        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return _device


def _load_paraphrase():
    global _para_tokenizer, _para_model
    if _para_model is None:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        name = _paraphrase_model_name()
        _para_tokenizer = AutoTokenizer.from_pretrained(name, use_fast=False)
        _para_model = AutoModelForSeq2SeqLM.from_pretrained(name)
        _para_model.eval()
        _para_model = _para_model.to(_get_device())
    return _para_tokenizer, _para_model


def _truncate(s: str, max_chars: int) -> str:
    s = s.strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1].rstrip() + "…"


def _normalize_for_compare(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _similarity_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_for_compare(a), _normalize_for_compare(b)).ratio()


def _lead_span_for_paraphrase(text: str) -> str:
    """
    Paraphrase the lead only (1-2 sentences) to encourage true rewriting.
    Very long inputs cause T5 paraphrase models to mostly copy.
    """
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p.strip()]
    if not parts:
        return text.strip()
    lead = parts[0]
    if len(parts) > 1 and len(lead) < (_PARAPHRASE_LEAD_MAX_CHARS // 2):
        lead = f"{lead} {parts[1]}"
    if len(lead) > _PARAPHRASE_LEAD_MAX_CHARS:
        lead = lead[:_PARAPHRASE_LEAD_MAX_CHARS].rstrip()
    return lead


def _unique_suggestions(candidates: list[str], original: str, limit: int) -> list[str]:
    orig_n = _normalize_for_compare(original)
    out: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        t = c.strip()
        if not t:
            continue
        n = _normalize_for_compare(t)
        if n == orig_n or n in seen:
            continue
        if _similarity_ratio(t, original) >= _PARAPHRASE_MAX_SIMILARITY:
            continue
        seen.add(n)
        out.append(t)
        if len(out) >= limit:
            break
    return out


def _apply_grammar_polish(text: str, max_changes: int = 8) -> str:
    """
    Apply a bounded set of LanguageTool first-choice replacements.
    Conservative cleanup pass to reduce obvious residual errors in paraphrases.
    """
    payload = check_grammar(text, max_issues=30)
    if payload.get("unavailable"):
        return text

    issues = payload.get("issues", []) or []
    if not issues:
        return text

    edits: list[tuple[int, int, str]] = []
    for issue in issues:
        sugg = issue.get("suggestions") or []
        if not sugg:
            continue
        off = int(issue.get("offset", 0))
        length = int(issue.get("length", 0))
        repl = str(sugg[0])
        if length < 0:
            continue
        edits.append((off, length, repl))
        if len(edits) >= max_changes:
            break

    if not edits:
        return text

    out = text
    for off, length, repl in sorted(edits, key=lambda x: x[0], reverse=True):
        if off < 0 or off > len(out):
            continue
        end = min(off + max(0, length), len(out))
        out = out[:off] + repl + out[end:]
    return out


def _apply_neural_polish(text: str) -> str:
    """
    Optional stronger cleanup pass using the same neural GEC model used by the app.
    Falls back silently if neural grammar is disabled/unavailable.
    """
    payload = neural_grammar_correct(text)
    if not payload.get("enabled"):
        return text
    if payload.get("unavailable"):
        return text
    corrected = payload.get("corrected_text")
    if isinstance(corrected, str) and corrected.strip():
        return corrected.strip()
    return text


def paraphrase_suggestions(text: str, n: int = 3) -> dict[str, Any]:
    """Up to n alternative phrasings of the start of the text (T5 paraphrase)."""
    if not _ENABLE_PARAPHRASE:
        return {
            "enabled": False,
            "note": "Paraphrase suggestions are disabled (BLOOM_ENABLE_PARAPHRASE=false).",
        }

    stripped = text.strip()
    if not stripped:
        return {"enabled": True, "unavailable": True, "error": "Empty text"}

    snippet = _truncate(stripped, _PARAPHRASE_MAX_CHARS)
    lead_snippet = _lead_span_for_paraphrase(snippet)
    note: str | None = None
    if len(stripped) > _PARAPHRASE_MAX_CHARS:
        note = (
            f"Suggestions are based on the first ~{_PARAPHRASE_MAX_CHARS} characters "
            "to keep the model fast and stable."
        )

    try:
        import torch

        tok, model = _load_paraphrase()
        device = _get_device()
        prefix = "paraphrase: "
        inp = prefix + lead_snippet
        inputs = tok(inp, return_tensors="pt", truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        max_gen = 256
        num_beams = max(n, 8)
        gen_kwargs: dict[str, Any] = {
            "max_length": max_gen,
            "num_beams": max(num_beams, 10),
            "no_repeat_ngram_size": 3,
            "num_return_sequences": min(n, max(num_beams, 10)),
            "early_stopping": True,
            "do_sample": False,
        }

        with torch.no_grad():
            outputs = model.generate(**inputs, **gen_kwargs)

        decoded = tok.batch_decode(outputs, skip_special_tokens=True)
        unique = _unique_suggestions(decoded, lead_snippet, n)

        if len(unique) < n:
            extra: list[str] = []
            for seed in (42, 43, 44):
                torch.manual_seed(seed)
                with torch.no_grad():
                    out2 = model.generate(
                        **inputs,
                        max_length=256,
                        do_sample=True,
                        top_p=0.9,
                        top_k=70,
                        temperature=1.0,
                        no_repeat_ngram_size=3,
                        num_return_sequences=1,
                    )
                extra.extend(tok.batch_decode(out2, skip_special_tokens=True))
            unique = _unique_suggestions(unique + extra, lead_snippet, n)

        if _PARAPHRASE_ENABLE_POLISH and unique:
            polished = [_apply_grammar_polish(s) for s in unique]
            unique = _unique_suggestions(polished, lead_snippet, n)
        if _PARAPHRASE_ENABLE_NEURAL_POLISH and unique:
            neural_polished = [_apply_neural_polish(s) for s in unique]
            unique = _unique_suggestions(neural_polished, lead_snippet, n)

        payload: dict[str, Any] = {
            "enabled": True,
            "unavailable": False,
            "model": _paraphrase_model_name(),
            "suggestions": unique,
            "source_excerpt": lead_snippet,
        }
        postprocess_steps: list[str] = []
        if _PARAPHRASE_ENABLE_POLISH:
            postprocess_steps.append("grammar_polish")
        if _PARAPHRASE_ENABLE_NEURAL_POLISH:
            postprocess_steps.append("neural_polish")
        if postprocess_steps:
            payload["postprocess"] = ", ".join(postprocess_steps)
        if note:
            payload["note"] = note
        return payload
    except Exception as exc:  # noqa: BLE001
        return {
            "enabled": True,
            "unavailable": True,
            "error": str(exc),
            "model": _paraphrase_model_name(),
            "hint": "pip install torch transformers sentencepiece",
        }
