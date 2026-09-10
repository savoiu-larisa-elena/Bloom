from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_required_user_id
from app.services.analysis_history import (
    count_recent_for_user,
    delete_analysis_for_user,
    get_analysis_for_user,
    history_db_available,
    list_character_evolution_for_user,
    list_recent_for_user,
    retention_days,
)

_HISTORY_DB_WARNING = (
    "History is temporarily unavailable. Start PostgreSQL from backend/: docker compose up -d"
)

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
def get_history(
    limit: int = Query(30, ge=1, le=100),
    user_id: int = Depends(get_required_user_id),
):
    """Recent analysis summaries for the signed-in user (rolling retention window)."""
    days = retention_days()
    out = {
        "retention_days": days,
        "entries": list_recent_for_user(user_id, limit=limit),
    }
    if not history_db_available():
        out["history_warning"] = _HISTORY_DB_WARNING
    return out


@router.get("/history/dashboard")
def get_history_dashboard(
    limit: int = Query(50, ge=1, le=100),
    user_id: int = Depends(get_required_user_id),
):
    """Count + recent entries for the home dashboard (rolling retention window)."""
    days = retention_days()
    out = {
        "retention_days": days,
        "analysis_count": count_recent_for_user(user_id),
        "entries": list_recent_for_user(user_id, limit=limit),
    }
    if not history_db_available():
        out["history_warning"] = _HISTORY_DB_WARNING
    return out


@router.get("/history/characters/evolution")
def get_character_evolution(
    limit: int = Query(50, ge=1, le=100),
    user_id: int = Depends(get_required_user_id),
):
    """Character profile snapshots grouped by name across saved analyses."""
    out = {
        "retention_days": retention_days(),
        "characters": list_character_evolution_for_user(user_id, limit=limit),
    }
    if not history_db_available():
        out["history_warning"] = _HISTORY_DB_WARNING
    return out


@router.get("/history/{analysis_id}")
def get_history_entry(
    analysis_id: int,
    user_id: int = Depends(get_required_user_id),
):
    """One saved analysis including stored character profiles and full analysis JSON."""
    entry = get_analysis_for_user(user_id, analysis_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return entry


@router.delete("/history/{analysis_id}")
def delete_history_entry(
    analysis_id: int,
    user_id: int = Depends(get_required_user_id),
):
    """Remove one saved analysis for the signed-in user."""
    if not delete_analysis_for_user(user_id, analysis_id):
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"deleted": True, "id": analysis_id}
