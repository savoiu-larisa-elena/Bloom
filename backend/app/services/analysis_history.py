from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg
from psycopg.types.json import Json

from app.services.database import connection, init_schema

logger = logging.getLogger(__name__)


_DEFAULT_RETENTION_DAYS = 7


def retention_days() -> int:
    """Rolling window for stored analyses (default 7). Override with BLOOM_HISTORY_RETENTION_DAYS."""
    raw = os.environ.get("BLOOM_HISTORY_RETENTION_DAYS", "").strip()
    if raw.isdigit():
        return max(1, min(int(raw), 3650))
    return _DEFAULT_RETENTION_DAYS


def _max_full_text_chars() -> int | None:
    """None = store full text with no application-side truncation (DB limit ~1GB TEXT)."""
    raw = os.environ.get("BLOOM_HISTORY_MAX_FULL_TEXT_CHARS", "").strip()
    if not raw or raw == "0":
        return None
    if raw.isdigit():
        return max(1_000, min(int(raw), 1_000_000_000))
    return None


def _enabled() -> bool:
    return os.environ.get("BLOOM_ENABLE_ANALYSIS_HISTORY", "true").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _prune(conn: Any) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days())
    with conn.cursor() as cur:
        cur.execute("DELETE FROM analyses WHERE created_at < %s", (cutoff,))


def _extract_characters_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """Compact character data for history, evolution tracking, and dashboard previews."""
    chars_heuristic = payload.get("characters") if isinstance(payload.get("characters"), dict) else {}
    profile = payload.get("character_profile") if isinstance(payload.get("character_profile"), dict) else {}

    detected: list[dict[str, Any]] = []
    for c in (chars_heuristic.get("candidates") or [])[:12]:
        if isinstance(c, dict) and c.get("name"):
            detected.append(
                {
                    "name": str(c["name"]).strip(),
                    "mentions": c.get("mentions"),
                }
            )

    arcs: dict[str, str] = {}
    for a in profile.get("arc_in_excerpt") or []:
        if isinstance(a, dict) and a.get("name"):
            arcs[str(a["name"]).strip().lower()] = str(a.get("beat") or "").strip()[:500]

    profiles: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    profile_note: str | None = None

    profile_ok = profile.get("enabled") is not False and not profile.get("unavailable")
    if profile_ok:
        for ch in (profile.get("characters") or [])[:8]:
            if not isinstance(ch, dict) or not ch.get("name"):
                continue
            name = str(ch["name"]).strip()
            profiles.append(
                {
                    "name": name,
                    "role_hint": str(ch.get("role_hint") or "unknown"),
                    "goals_or_motivation": str(ch.get("goals_or_motivation") or "")[:500],
                    "conflict_or_stakes": str(ch.get("conflict_or_stakes") or "")[:500],
                    "traits": [str(t) for t in (ch.get("traits") or [])[:4] if t],
                    "arc_beat": arcs.get(name.lower(), ""),
                    "evidence_quotes": [
                        str(q)[:120] for q in (ch.get("evidence_quotes") or [])[:2] if q
                    ],
                }
            )
        for rel in (profile.get("relationships") or [])[:12]:
            if isinstance(rel, dict) and rel.get("from") and rel.get("to"):
                relationships.append(
                    {
                        "from": str(rel["from"]).strip(),
                        "to": str(rel["to"]).strip(),
                        "relation": str(rel.get("relation") or "other"),
                        "support": str(rel.get("support") or "")[:300],
                    }
                )
    else:
        profile_note = str(profile.get("note") or profile.get("user_hint") or "")[:500] or None

    return {
        "detected": detected,
        "profiles": profiles,
        "relationships": relationships,
        "profile_available": bool(profiles),
        "profile_note": profile_note,
        "limitations": str(profile.get("limitations") or "")[:500],
    }


def _build_summary(payload: dict[str, Any]) -> dict[str, Any]:
    et = payload.get("emotion_tone") or {}
    dom = et.get("dominant_emotion") if isinstance(et, dict) else None
    gr = payload.get("grammar") or {}
    issues = gr.get("issue_count") if isinstance(gr, dict) else None
    st = payload.get("style_consistency") or {}
    characters = _extract_characters_snapshot(payload)
    return {
        "flesch_score": payload.get("flesch_score"),
        "flesch_kincaid_grade": payload.get("flesch_kincaid_grade"),
        "dominant_emotion": dom,
        "grammar_issue_count": issues,
        "style_consistency_score": st.get("consistency_score") if isinstance(st, dict) else None,
        "lexical_diversity_lemma_ttr": st.get("lexical_diversity_lemma_ttr")
        if isinstance(st, dict)
        else None,
        "characters": characters,
    }


def _is_db_unavailable(exc: BaseException) -> bool:
    if isinstance(exc, psycopg.OperationalError):
        return True
    return isinstance(exc, RuntimeError) and "PostgreSQL connection failed" in str(exc)


def _iso_utc(dt: Any) -> str:
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(dt, str):
        return dt
    return str(dt)


def append_analysis(text: str, payload: dict[str, Any], user_id: int | None) -> bool:
    """Persist one analysis row (full text + full JSON) for signed-in users.

    Returns True when saved (or when history is disabled / user is anonymous).
    Returns False when the database is unavailable so callers can still succeed.
    """
    if not _enabled() or not text.strip() or user_id is None:
        return True
    try:
        init_schema()
        full = text.strip()
        cap = _max_full_text_chars()
        if cap is not None and len(full) > cap:
            full = full[: cap - 1].rstrip() + "…"
        preview = full.replace("\n", " ")[:280]
        summary = _build_summary(payload)
        characters = summary.get("characters") if isinstance(summary.get("characters"), dict) else {}
        with connection() as conn:
            try:
                _prune(conn)
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO analyses (
                            user_id, full_text, text_preview, summary_json, analysis_json, characters_json
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (user_id, full, preview, Json(summary), Json(payload), Json(characters)),
                    )
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                raise
        return True
    except psycopg.OperationalError as exc:
        logger.warning("analysis history save failed (database unavailable): %s", exc)
        return False
    except RuntimeError as exc:
        if "PostgreSQL connection failed" in str(exc):
            logger.warning("analysis history save failed: %s", exc)
            return False
        raise


def count_recent_for_user(user_id: int) -> int:
    """Number of analyses in the rolling retention window for this user."""
    if not _enabled():
        return 0
    try:
        init_schema()
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days())
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*)::bigint AS c
                    FROM analyses
                    WHERE created_at >= %s AND user_id = %s
                    """,
                    (cutoff, user_id),
                )
                row = cur.fetchone()
        if not row:
            return 0
        return int(row["c"])
    except Exception as exc:
        if _is_db_unavailable(exc):
            logger.warning("analysis history count failed (database unavailable): %s", exc)
            return 0
        raise


def list_recent_for_user(user_id: int, limit: int = 30) -> list[dict[str, Any]]:
    if not _enabled():
        return []
    try:
        init_schema()
        cap = max(1, min(limit, 100))
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days())
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, created_at, text_preview, summary_json, full_text, characters_json
                    FROM analyses
                    WHERE created_at >= %s AND user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (cutoff, user_id, cap),
                )
                rows = cur.fetchall()
        return [_row_to_list_entry(r) for r in rows]
    except Exception as exc:
        if _is_db_unavailable(exc):
            logger.warning("analysis history list failed (database unavailable): %s", exc)
            return []
        raise


def _characters_from_row(row: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    chars = row.get("characters_json")
    if isinstance(chars, dict) and (
        chars.get("profiles") or chars.get("detected") or chars.get("relationships")
    ):
        return chars
    nested = summary.get("characters")
    if isinstance(nested, dict) and (
        nested.get("profiles") or nested.get("detected") or nested.get("relationships")
    ):
        return nested
    analysis = row.get("analysis_json")
    if isinstance(analysis, dict):
        return _extract_characters_snapshot(analysis)
    return chars if isinstance(chars, dict) else {}


def _row_to_list_entry(row: dict[str, Any]) -> dict[str, Any]:
    summary = row.get("summary_json")
    if not isinstance(summary, dict):
        summary = {}
    ft = row.get("full_text")
    preview = row.get("text_preview") or ""
    characters = _characters_from_row(row, summary)
    return {
        "id": int(row["id"]),
        "created_at": _iso_utc(row["created_at"]),
        "text_preview": preview,
        "full_text": ft if isinstance(ft, str) and ft.strip() else preview,
        "summary": summary,
        "characters": characters,
    }


def get_analysis_for_user(user_id: int, analysis_id: int) -> dict[str, Any] | None:
    if not _enabled():
        return None
    try:
        init_schema()
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days())
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, created_at, text_preview, full_text, summary_json, analysis_json, characters_json
                    FROM analyses
                    WHERE id = %s AND user_id = %s AND created_at >= %s
                    """,
                    (analysis_id, user_id, cutoff),
                )
                row = cur.fetchone()
        if not row:
            return None
        entry = _row_to_list_entry(row)
        analysis = row.get("analysis_json")
        entry["analysis"] = analysis if isinstance(analysis, dict) else {}
        return entry
    except Exception as exc:
        if _is_db_unavailable(exc):
            logger.warning("analysis history get failed (database unavailable): %s", exc)
            return None
        raise


def list_character_evolution_for_user(user_id: int, limit: int = 50) -> list[dict[str, Any]]:
    """Group stored character profiles across recent analyses (oldest snapshot first per character)."""
    if not _enabled():
        return []
    try:
        init_schema()
        cap = max(1, min(limit, 100))
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days())
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, created_at, text_preview, characters_json, summary_json, analysis_json
                    FROM analyses
                    WHERE created_at >= %s AND user_id = %s
                    ORDER BY created_at ASC
                    LIMIT %s
                    """,
                    (cutoff, user_id, cap),
                )
                rows = cur.fetchall()
    except Exception as exc:
        if _is_db_unavailable(exc):
            logger.warning("character evolution list failed (database unavailable): %s", exc)
            return []
        raise

    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        summary = row.get("summary_json") if isinstance(row.get("summary_json"), dict) else {}
        chars = _characters_from_row(row, summary)
        profiles = chars.get("profiles") if isinstance(chars.get("profiles"), list) else []
        if not profiles:
            continue
        created = _iso_utc(row["created_at"])
        preview = row.get("text_preview") or ""
        for p in profiles:
            if not isinstance(p, dict) or not p.get("name"):
                continue
            key = str(p["name"]).strip().lower()
            if key not in grouped:
                grouped[key] = {"name": str(p["name"]).strip(), "snapshots": []}
            grouped[key]["snapshots"].append(
                {
                    "analysis_id": int(row["id"]),
                    "created_at": created,
                    "text_preview": preview,
                    "role_hint": p.get("role_hint"),
                    "goals_or_motivation": p.get("goals_or_motivation"),
                    "conflict_or_stakes": p.get("conflict_or_stakes"),
                    "traits": p.get("traits") or [],
                    "arc_beat": p.get("arc_beat"),
                    "evidence_quotes": p.get("evidence_quotes") or [],
                }
            )

    out = list(grouped.values())
    out.sort(key=lambda g: (-len(g["snapshots"]), g["name"].lower()))
    return out


def delete_analysis_for_user(user_id: int, analysis_id: int) -> bool:
    """Delete one history row owned by the user. Returns True when a row was removed."""
    if not _enabled():
        return False
    try:
        init_schema()
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM analyses
                    WHERE id = %s AND user_id = %s
                    RETURNING id
                    """,
                    (analysis_id, user_id),
                )
                row = cur.fetchone()
            conn.commit()
        return row is not None
    except Exception as exc:
        if _is_db_unavailable(exc):
            logger.warning("analysis history delete failed (database unavailable): %s", exc)
            return False
        raise


def history_db_available() -> bool:
    """Quick check used by API routes to surface a friendly warning when Postgres is down."""
    if not _enabled():
        return True
    try:
        init_schema()
        with connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return True
    except Exception as exc:
        if _is_db_unavailable(exc):
            return False
        raise
