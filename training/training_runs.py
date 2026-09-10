from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUNS_FILE = Path(__file__).resolve().parent / "training_runs.jsonl"


def _final_metrics_from_trainer(trainer: Any) -> dict[str, float]:
    out: dict[str, float] = {}
    for entry in reversed(trainer.state.log_history):
        if "eval_loss" in entry and "eval_loss" not in out:
            out["eval_loss"] = float(entry["eval_loss"])
        if "train_loss" in entry and "train_loss" not in out:
            out["train_loss"] = float(entry["train_loss"])
        if len(out) >= 2:
            break
    return out


def append_training_run(
    *,
    task: str,
    data_path: Path,
    output_dir: Path,
    base_model: str,
    epochs: float,
    batch_size: int,
    lr: float,
    train_rows: int,
    eval_rows: int,
    trainer: Any | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Append a record to training_runs.jsonl (UTC + local time)."""
    record: dict[str, Any] = {
        "task": task,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "finished_at_local": datetime.now().astimezone().isoformat(),
        "data": str(data_path.resolve()),
        "output": str(output_dir.resolve()),
        "base_model": base_model,
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": lr,
        "train_rows": train_rows,
        "eval_rows": eval_rows,
    }
    if trainer is not None:
        record.update(_final_metrics_from_trainer(trainer))
    if extra:
        record.update(extra)

    RUNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RUNS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return RUNS_FILE
