from __future__ import annotations

import os
from pathlib import Path


def setup_local_caches() -> None:
    backend_dir = Path(__file__).resolve().parent.parent
    bloom_root = backend_dir.parent
    cache_root = bloom_root / ".cache"
    hf_home = cache_root / "huggingface"
    torch_home = cache_root / "torch"
    pip_cache = cache_root / "pip"

    for d in (hf_home, torch_home, pip_cache):
        d.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("HF_HOME", str(hf_home))
    os.environ.setdefault("TORCH_HOME", str(torch_home))
    os.environ.setdefault("PIP_CACHE_DIR", str(pip_cache))
