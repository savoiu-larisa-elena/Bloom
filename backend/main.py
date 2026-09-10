from app.cache_env import setup_local_caches

setup_local_caches()

from app.main import app

__all__ = ["app"]
