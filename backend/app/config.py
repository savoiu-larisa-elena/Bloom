import os


def get_database_url() -> str:
    """PostgreSQL DSN. Set BLOOM_DATABASE_URL; optional default for local dev."""
    url = os.environ.get("BLOOM_DATABASE_URL", "").strip()
    if url:
        return url
    return "postgresql://bloom:bloom@127.0.0.1:5433/bloom"

CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

GRAMMAR_MAX_ISSUES_SHOWN: int = 50

_GRAMMAR_PICKY_RAW = os.environ.get("BLOOM_LANGUAGETOOL_PICKY", "true").strip().lower()
GRAMMAR_PICKY: bool = _GRAMMAR_PICKY_RAW in ("1", "true", "yes", "on")
