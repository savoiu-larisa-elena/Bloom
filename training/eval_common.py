from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from datasets import Dataset

TRAINING_DIR = Path(__file__).resolve().parent
BLOOM_ROOT = TRAINING_DIR.parent
EVAL_RESULTS_DIR = TRAINING_DIR / "eval_results"
SPLIT_SEED = 42
SPLIT_TEST_SIZE = 0.1


def setup_bloom_cache_env() -> Path:
    """
    Force HF/Torch caches under ``<repo>/.cache`` on the project drive (e.g. E:).

    Overrides broken user env (e.g. HF_HOME on missing F:\\) before any Hub download.
    Same layout as ``set_bloom_cache_env.cmd`` and ``backend/app/cache_env.py``.
    """
    cache_root = BLOOM_ROOT / ".cache"
    hf_home = cache_root / "huggingface"
    torch_home = cache_root / "torch"
    pip_cache = cache_root / "pip"
    hub_cache = hf_home / "hub"

    for d in (hf_home, hub_cache, torch_home, pip_cache):
        d.mkdir(parents=True, exist_ok=True)

    os.environ["HF_HOME"] = str(hf_home)
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(hub_cache)
    os.environ["TORCH_HOME"] = str(torch_home)
    os.environ["PIP_CACHE_DIR"] = str(pip_cache)
    os.environ["TRANSFORMERS_CACHE"] = str(hf_home)
    return hf_home


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    if not rows:
        raise FileNotFoundError(f"No rows in {path}")
    return rows


def train_eval_split(rows: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    ds = Dataset.from_list(rows)
    split = ds.train_test_split(test_size=SPLIT_TEST_SIZE, seed=SPLIT_SEED)
    return list(split["train"]), list(split["test"])


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def exact_match_rate(hypotheses: list[str], references: list[str]) -> float:
    if not hypotheses:
        return 0.0
    hits = sum(
        1 for h, r in zip(hypotheses, references) if normalize_text(h) == normalize_text(r)
    )
    return hits / len(hypotheses)


def checkpoint_ready(path: Path) -> bool:
    return path.is_dir() and (path / "config.json").is_file()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
