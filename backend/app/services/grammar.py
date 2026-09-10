import os
import re
from typing import Any, Optional

from app.config import GRAMMAR_MAX_ISSUES_SHOWN, GRAMMAR_PICKY

_lt_local: Any = None

_GRAMMAR_MODE = os.environ.get("BLOOM_GRAMMAR_MODE", "auto").strip().lower()
_GRAMMAR_LANG = os.environ.get("BLOOM_GRAMMAR_LANG", "en-GB").strip() or "en-GB"

_AFTER_A_AN_SKIP = (
    "few",
    "little",
    "many",
    "several",
    "some",
    "number",
    "lot",
    "lots",
    "couple",
    "range",
    "variety",
    "series",
    "certain",
)

_ARTICLE_PLURAL_TO_SINGULAR: dict[str, str] = {
    "issues": "issue",
    "problems": "problem",
    "mistakes": "mistake",
    "errors": "error",
    "questions": "question",
    "answers": "answer",
    "things": "thing",
    "ways": "way",
    "days": "day",
    "books": "book",
    "words": "word",
    "lines": "line",
    "pages": "page",
    "moments": "moment",
    "places": "place",
    "cases": "case",
    "points": "point",
    "reasons": "reason",
    "ideas": "idea",
    "stories": "story",
    "chapters": "chapter",
    "characters": "character",
    "names": "name",
    "examples": "example",
    "details": "detail",
    "parts": "part",
    "types": "type",
    "kinds": "kind",
    "sorts": "sort",
    "bits": "bit",
    "pieces": "piece",
    "times": "time",
}

_PLURAL_ALT = "|".join(
    re.escape(p)
    for p in sorted(
        _ARTICLE_PLURAL_TO_SINGULAR.keys(),
        key=len,
        reverse=True,
    )
)

_PATTERN_A_WORD_PLURAL = re.compile(
    r"\b(a|an)\s+(?!(?:" + "|".join(re.escape(w) for w in _AFTER_A_AN_SKIP) + r")\b)"
    r"(\w+)\s+("
    + _PLURAL_ALT
    + r")\b",
    re.IGNORECASE,
)


def _get_local_tool():
    global _lt_local
    if _lt_local is None:
        import language_tool_python

        _lt_local = language_tool_python.LanguageTool(_GRAMMAR_LANG)
        _lt_local.picky = GRAMMAR_PICKY
    return _lt_local


def _sentence_span(text: str, offset: int) -> tuple[int, int]:
    """Half-open [start, end) span of the sentence containing offset (best effort)."""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    n = len(t)
    if n == 0:
        return 0, 0
    pos = max(0, min(offset, n - 1))
    start = pos
    while start > 0 and t[start - 1] not in ".!?\n":
        start -= 1
    while start < n and t[start] in " \t":
        start += 1
    end = pos + 1
    while end < n and t[end - 1] not in ".!?\n":
        end += 1
    return start, min(end, n)


def _enrich_issues_with_context(text: str, issues: list[dict[str, Any]]) -> None:
    """Attach matched span + containing sentence so the UI can show where each flag applies."""
    n = len(text)
    for issue in issues:
        off = int(issue.get("offset", 0))
        length = max(1, int(issue.get("length", 1)))
        end = min(off + length, n)
        issue["matched_text"] = text[off:end] if off < n else ""
        sent_start, sent_end = _sentence_span(text, off)
        sentence = text[sent_start:sent_end].strip()
        if len(sentence) > 500:
            sentence = sentence[:499].rstrip() + "…"
        issue["sentence"] = sentence
        issue["highlight_start"] = max(0, off - sent_start)
        issue["highlight_length"] = min(length, max(0, sent_end - off))


def _suggestions_from_match(match: Any, limit: int = 5) -> list[str]:
    out: list[str] = []
    for repl in (getattr(match, "replacements", None) or [])[:limit]:
        if isinstance(repl, str):
            out.append(repl)
        else:
            val = getattr(repl, "value", None)
            out.append(val if val is not None else str(repl))
    return out


def _issues_from_lt_matches(matches: list[Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for m in matches:
        offset = getattr(m, "offset", None)
        length = (
            getattr(m, "errorLength", None)
            if getattr(m, "errorLength", None) is not None
            else getattr(m, "error_length", None)
        )
        if length is None:
            length = getattr(m, "length", None)
        if offset is None:
            offset = 0
        if length is None:
            length = 1

        msg = getattr(m, "message", None) or str(m)
        lt_context = getattr(m, "context", None)
        if isinstance(lt_context, str) and lt_context.strip():
            context_text = lt_context.strip()
        else:
            context_text = None
        issues.append(
            {
                "offset": int(offset),
                "length": int(length),
                "message": msg,
                "rule_id": getattr(m, "ruleId", None),
                "category": getattr(m, "category", None),
                "suggestions": _suggestions_from_match(m),
                "source": "languagetool",
                "lt_context": context_text,
            }
        )
    return issues


def _ranges_overlap(o1: int, len1: int, o2: int, len2: int) -> bool:
    """True if half-open ranges [o1,o1+len1) and [o2,o2+len2) overlap."""
    return not (o1 + len1 <= o2 or o2 + len2 <= o1)


def _heuristic_bloom_issues(text: str, existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Extra checks LanguageTool often misses: 'a/an + word + <plural>' where the
    plural may need to be singular (see _ARTICLE_PLURAL_TO_SINGULAR).
    """
    extra: list[dict[str, Any]] = []
    for m in _PATTERN_A_WORD_PLURAL.finditer(text):
        raw_plural = m.group(3)
        plural = raw_plural.lower()
        singular = _ARTICLE_PLURAL_TO_SINGULAR.get(plural)
        if not singular:
            continue
        if raw_plural[:1].isupper():
            suggestion = singular.capitalize()
        else:
            suggestion = singular
        off = m.start(3)
        length = len(raw_plural)
        candidate = {
            "offset": off,
            "length": length,
            "message": (
                f'Possible agreement: after "a/an …" you may need singular '
                f'"{singular}" instead of "{plural}".'
            ),
            "rule_id": "BLOOM_ARTICLE_PLURAL",
            "category": "BLOOM_HEURISTIC",
            "suggestions": [suggestion],
            "source": "bloom_heuristic",
        }
        if any(
            _ranges_overlap(candidate["offset"], candidate["length"], e["offset"], e["length"])
            for e in existing
        ):
            continue
        if any(
            _ranges_overlap(candidate["offset"], candidate["length"], e["offset"], e["length"])
            for e in extra
        ):
            continue
        extra.append(candidate)
    return extra


def _build_grammar_payload(
    lt_matches: list[Any],
    text: str,
    cap: int,
    source: str,
    used_remote_fallback: bool = False,
) -> dict[str, Any]:
    issues = _issues_from_lt_matches(lt_matches)
    for h in _heuristic_bloom_issues(text, issues):
        issues.append(h)
    issues.sort(key=lambda x: x["offset"])
    _enrich_issues_with_context(text, issues)
    total = len(issues)
    truncated = total > cap
    shown = issues[:cap]

    out: dict[str, Any] = {
        "issue_count": total,
        "issues": shown,
        "truncated": truncated,
        "shown": len(shown),
        "source": source,
        "picky": GRAMMAR_PICKY,
    }
    if used_remote_fallback:
        out["used_remote_fallback"] = True
        out["note"] = (
            "Local LanguageTool needs Java 17+. Using the public LanguageTool API "
            "(requires internet). Install JDK 17+ for fully local checks."
        )
    return out


def _looks_like_java_env_error(msg: str) -> bool:
    lower = msg.lower()
    return (
        "java" in lower
        and (
            "requires java" in lower
            or "version" in lower
            or "detected java" in lower
            or "jvm" in lower
        )
    )


def _looks_like_rate_limit(msg: str) -> bool:
    lower = msg.lower()
    return "rate limit" in lower or (
        "exceeded" in lower and ("api" in lower or "free" in lower)
    )


def _error_payload(exc: Exception) -> dict[str, Any]:
    """Return a consistent grammar error response (rate limit, etc.)."""
    exc_str = str(exc)
    out: dict[str, Any] = {
        "issue_count": 0,
        "issues": [],
        "unavailable": True,
        "error": exc_str,
    }
    if _looks_like_rate_limit(exc_str):
        out["rate_limited"] = True
        out["hint"] = (
            "The free public LanguageTool API has strict rate limits. "
            "To avoid them: install JDK 17 or newer (e.g. Eclipse Temurin), "
            "set JAVA_HOME to that JDK, restart your terminal and the API — "
            "then grammar runs locally with no API quota. "
            "Or wait a while and try again."
        )
    return out


def check_grammar(text: str, max_issues: Optional[int] = None) -> dict[str, Any]:
    """Run LanguageTool; return issues + metadata or an error payload."""
    cap = max_issues if max_issues is not None else GRAMMAR_MAX_ISSUES_SHOWN
    import language_tool_python

    def run_with_remote() -> dict[str, Any]:
        tool = language_tool_python.LanguageToolPublicAPI(_GRAMMAR_LANG)
        tool.picky = GRAMMAR_PICKY
        matches = tool.check(text)
        return _build_grammar_payload(matches, text, cap, source="remote")

    def run_with_local() -> dict[str, Any]:
        tool = _get_local_tool()
        matches = tool.check(text)
        return _build_grammar_payload(matches, text, cap, source="local")

    try:
        if _GRAMMAR_MODE == "remote":
            return run_with_remote()

        if _GRAMMAR_MODE == "local":
            return run_with_local()

        try:
            return run_with_local()
        except Exception as local_exc:  # noqa: BLE001
            if not _looks_like_java_env_error(str(local_exc)):
                raise
            global _lt_local
            _lt_local = None
            payload = run_with_remote()
            payload["used_remote_fallback"] = True
            payload["note"] = (
                "Local LanguageTool needs Java 17+. Using the public LanguageTool API "
                "(requires internet). Install JDK 17+ for fully local checks."
            )
            return payload

    except Exception as exc: 
        return _error_payload(exc)
