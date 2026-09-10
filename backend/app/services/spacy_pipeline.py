from __future__ import annotations

import os
from typing import Any

_MAX_DOC_CHARS = int(os.environ.get("BLOOM_SPACY_MAX_CHARS", "100000"))


def _enabled() -> bool:
    return os.environ.get("BLOOM_ENABLE_SPACY", "false").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _model_name() -> str:
    return os.environ.get("BLOOM_SPACY_MODEL", "en_core_web_sm").strip() or "en_core_web_sm"


_nlp: Any = None


def _load_nlp():
    global _nlp
    if _nlp is None:
        import spacy

        _nlp = spacy.load(_model_name())
    return _nlp


def analyse_spacy(text: str) -> dict[str, Any]:
    """
    Run spaCy NER + POS + dependency head labels on the text (truncated for safety).
    """
    if not _enabled():
        return {
            "enabled": False,
            "note": (
                "SpaCy pipeline disabled. Set BLOOM_ENABLE_SPACY=true after installing "
                "requirements-spacy.txt and downloading a model (e.g. en_core_web_sm)."
            ),
        }

    stripped = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not stripped:
        return {"enabled": True, "unavailable": True, "error": "Empty text"}

    cap = max(2_000, min(_MAX_DOC_CHARS, 500_000))
    truncated = len(stripped) > cap
    doc_src = stripped[:cap] if truncated else stripped

    try:
        nlp = _load_nlp()
    except OSError as e:
        return {
            "enabled": True,
            "unavailable": True,
            "error": str(e),
            "hint": (
                f"Run: pip install -r requirements-spacy.txt && "
                f"python -m spacy download {_model_name()}"
            ),
        }
    except Exception as e:  # noqa: BLE001
        return {
            "enabled": True,
            "unavailable": True,
            "error": str(e),
            "hint": "pip install spacy && python -m spacy download en_core_web_sm",
        }

    doc = nlp(doc_src)

    entities: list[dict[str, Any]] = []
    for ent in doc.ents:
        if len(entities) >= 40:
            break
        entities.append(
            {
                "text": ent.text,
                "label": ent.label_,
                "start_char": int(ent.start_char),
                "end_char": int(ent.end_char),
            }
        )

    token_rows: list[dict[str, Any]] = []
    for i, tok in enumerate(doc):
        if i >= 80:
            break
        head = tok.head
        token_rows.append(
            {
                "text": tok.text,
                "lemma": tok.lemma_,
                "pos": tok.pos_,
                "tag": tok.tag_,
                "dep": tok.dep_,
                "head": head.text if head is not None else "",
            }
        )

    return {
        "enabled": True,
        "unavailable": False,
        "model": _model_name(),
        "doc_truncated": truncated,
        "sentence_count": len(list(doc.sents)),
        "entity_count": len(doc.ents),
        "entities": entities,
        "token_preview": token_rows,
        "note": (
            "Pretrained English pipeline: good on news-like text; fiction names and "
            "literary syntax can still be wrong. No extra training or dataset on your side."
        ),
    }
