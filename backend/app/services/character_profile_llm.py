from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

_DEFAULT_LLM_EXCERPT = 120_000


def _max_excerpt_chars() -> int:
    raw = os.environ.get("BLOOM_CHARACTER_LLM_MAX_CHARS", "").strip()
    if raw.isdigit():
        return max(2_000, min(int(raw), 500_000))
    return _DEFAULT_LLM_EXCERPT


_TIMEOUT_SEC = 90

_SYSTEM_PROMPT = """You are a careful literary assistant for young writers. Given ONLY the story excerpt the user pasted, produce a JSON object with this exact top-level shape (no markdown, no commentary outside JSON):
{
  "characters": [
    {
      "name": "string",
      "role_hint": "protagonist|antagonist|supporting|unknown",
      "goals_or_motivation": "one short sentence; prefix uncertain inferences with \"Seems:\"",
      "conflict_or_stakes": "one short sentence or empty string",
      "traits": ["up to 4 short trait words"],
      "evidence_quotes": ["up to 2 short verbatim phrases from the excerpt, under 120 chars each"]
    }
  ],
  "relationships": [
    {
      "from": "name A",
      "to": "name B",
      "relation": "family|friend|rival|romantic|authority|peer|other",
      "support": "one sentence citing behaviour or dialogue in the excerpt"
    }
  ],
  "arc_in_excerpt": [
    { "name": "character name", "beat": "what shifts, is attempted, or is revealed in this passage only" }
  ],
  "limitations": "one sentence: this is inference from a short excerpt, not the full story."
}

Rules:
- Only name characters who clearly appear or are referred to in the excerpt.
- If the excerpt has no dialogue or few clues, use fewer characters and more "unknown".
- Do not invent events not supported by the text.
- "relationships" should be edges between names you listed in "characters" (or obvious pronoun referents resolved in the excerpt).
- Maximum 8 characters, 12 relationships, 6 arc_in_excerpt items.
"""


def _api_key() -> str:
    return (
        os.environ.get("BLOOM_OPENAI_API_KEY", "").strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
    )


def _base_url() -> str:
    raw = os.environ.get("BLOOM_OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
    return raw.rstrip("/")


def _model() -> str:
    return os.environ.get("BLOOM_OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"


def _is_groq() -> bool:
    return "groq.com" in _base_url().lower()


def _use_json_object_mode() -> bool:
    raw = os.environ.get("BLOOM_OPENAI_JSON_OBJECT", "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    return not _is_groq()


def _request_headers(key: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "User-Agent": os.environ.get(
            "BLOOM_LLM_USER_AGENT",
            "Bloom/1.0 (thesis; +https://github.com/)",
        ),
    }


def _profiling_enabled() -> bool:
    return os.environ.get("BLOOM_ENABLE_CHARACTER_PROFILE_LLM", "true").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _excerpt(text: str) -> str:
    t = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    cap = _max_excerpt_chars()
    if len(t) <= cap:
        return t
    return t[: cap - 1].rstrip() + "…"


def _hints_block(character_signals: dict[str, Any] | None) -> str:
    if not character_signals or not isinstance(character_signals, dict):
        return ""
    cands = character_signals.get("candidates") or []
    if not cands:
        return ""
    lines = [
        f"- {c.get('name', '?')} (mentioned ~{c.get('mentions', '?')}× as a capitalised token)"
        for c in cands[:12]
        if isinstance(c, dict) and c.get("name")
    ]
    if not lines:
        return ""
    return (
        "Bloom also detected these recurring capitalised tokens (may include places, not only people):\n"
        + "\n".join(lines)
        + "\n\nUse them only if the excerpt supports treating them as characters.\n"
    )


def _parse_json_content(raw: str) -> dict[str, Any]:
    s = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s, re.IGNORECASE)
    if fence:
        s = fence.group(1).strip()
    return json.loads(s)


def _validate_profile(obj: Any) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ValueError("root must be object")
    out: dict[str, Any] = {
        "characters": [],
        "relationships": [],
        "arc_in_excerpt": [],
        "limitations": "",
    }
    if isinstance(obj.get("limitations"), str):
        out["limitations"] = obj["limitations"].strip()[:500]
    for key in ("characters", "relationships", "arc_in_excerpt"):
        val = obj.get(key)
        if isinstance(val, list):
            out[key] = val[:20]
    return out


def analyse_character_profile_llm(
    text: str,
    *,
    character_signals: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Return structured character / relationship / arc hints from an LLM, or a disabled payload.
    """
    if not _profiling_enabled():
        return {
            "enabled": False,
            "note": "Deep character profiling is disabled (BLOOM_ENABLE_CHARACTER_PROFILE_LLM=false).",
        }

    key = _api_key()
    if not key:
        return {
            "enabled": False,
            "note": (
                "Deep character profiling needs an API key. Set BLOOM_OPENAI_API_KEY "
                "(or OPENAI_API_KEY). No extra training dataset is required — only this excerpt is sent."
            ),
        }

    excerpt = _excerpt(text)
    if not excerpt:
        return {
            "enabled": True,
            "unavailable": True,
            "error": "Empty text",
        }

    user_msg = (
        _hints_block(character_signals)
        + "--- STORY EXCERPT ---\n"
        + excerpt
    )

    body: dict[str, Any] = {
        "model": _model(),
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.3,
    }
    if _use_json_object_mode():
        body["response_format"] = {"type": "json_object"}

    url = f"{_base_url()}/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers=_request_headers(key),
    )

    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SEC) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:800]
        low = err_body.lower()
        quota = e.code == 429 or "insufficient_quota" in low or "rate limit" in low
        out: dict[str, Any] = {
            "enabled": True,
            "unavailable": True,
            "error": f"HTTP {e.code}: {err_body}",
            "model": _model(),
        }
        if quota:
            out["quota_exceeded"] = True
            out["user_hint"] = (
                "The hosted LLM returned a quota or rate limit error. Add billing/credits on "
                "your OpenAI account, switch model, or unset BLOOM_OPENAI_API_KEY to skip this block."
            )
        elif e.code == 403 or "1010" in err_body:
            out["user_hint"] = (
                "Cloudflare blocked the LLM request (error 1010). If using Groq, verify "
                "BLOOM_OPENAI_BASE_URL=https://api.groq.com/openai/v1, your key starts with gsk_, "
                "and restart the backend after setting env vars. Bloom now sends a browser-like "
                "User-Agent; if this persists, set BLOOM_OPENAI_JSON_OBJECT=false or disable profiling "
                "with BLOOM_ENABLE_CHARACTER_PROFILE_LLM=false."
            )
        elif e.code == 401:
            out["user_hint"] = "The API key was rejected. Check BLOOM_OPENAI_API_KEY and restart the backend."
        return out
    except urllib.error.URLError as e:
        return {
            "enabled": True,
            "unavailable": True,
            "error": str(e.reason or e),
            "model": _model(),
        }
    except TimeoutError:
        return {
            "enabled": True,
            "unavailable": True,
            "error": "Request timed out",
            "model": _model(),
        }
    except json.JSONDecodeError as e:
        return {
            "enabled": True,
            "unavailable": True,
            "error": f"Invalid API response JSON: {e}",
            "model": _model(),
        }

    try:
        choice = (payload.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        content = msg.get("content") or ""
        parsed = _parse_json_content(content)
        profile = _validate_profile(parsed)
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as e:
        return {
            "enabled": True,
            "unavailable": True,
            "error": f"Could not parse model output: {e}",
            "model": _model(),
        }

    return {
        "enabled": True,
        "unavailable": False,
        "model": _model(),
        "excerpt_truncated": len(text.strip()) > _max_excerpt_chars(),
        **profile,
    }
