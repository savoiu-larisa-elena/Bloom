#!/usr/bin/env python3
"""
Download public Hugging Face datasets and save Bloom training JSONL.

Examples:
  pip install datasets
  python prepare_hf_dataset.py --dataset jfleg --output data/jfleg_from_hf.jsonl
  python prepare_hf_dataset.py --dataset emotion --output data/emotion_train.jsonl
  python prepare_hf_dataset.py --dataset paws --output data/paraphrase_train.jsonl --max-rows 20000

JFLEG: first human correction only (see export_jfleg).
Emotion: ``dair-ai/emotion`` (6-class tweets); ``love`` -> ``joy`` for compatibility with
``j-hartmann/emotion-english-distilroberta-base`` (no ``disgust`` / ``neutral`` rows in source).
PAWS: ``paws`` / ``labeled_final``; only label==1 (paraphrase) pairs.
"""

from __future__ import annotations

import os

for _k, _v in (
    ("OPENBLAS_NUM_THREADS", "1"),
    ("OMP_NUM_THREADS", "1"),
    ("MKL_NUM_THREADS", "1"),
    ("NUMEXPR_NUM_THREADS", "1"),
):
    os.environ.setdefault(_k, _v)

import argparse
import json
import random
from pathlib import Path

_EMOTION_LABELS: tuple[str, ...] = ("sadness", "joy", "love", "anger", "fear", "surprise")


def export_jfleg(output: Path) -> int:
    from datasets import load_dataset

    ds = load_dataset("jhu-clsp/jfleg")
    n = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for split in ("dev", "test"):
            if split not in ds:
                continue
            for row in ds[split]:
                src = row["sentence"].strip()
                corrs = row.get("corrections") or []
                if not src or not corrs:
                    continue
                tgt = str(corrs[0]).strip()
                if not tgt:
                    continue
                f.write(
                    json.dumps({"source": src, "target": tgt}, ensure_ascii=False) + "\n"
                )
                n += 1
    return n


def export_emotion(
    output: Path,
    *,
    splits: tuple[str, ...],
    max_rows: int | None,
    seed: int,
) -> int:
    """
    ``dair-ai/emotion`` on the Hub (``load_dataset("emotion")``): tweet-style self-reports.
    Maps ``love`` -> ``joy`` so every label exists in Hartmann's 7-way head except
    ``disgust`` and ``neutral`` (those classes simply have no rows from this corpus).

    Uses **streaming** reads (split-by-split) to avoid loading the full dataset into RAM.
    """
    from datasets import load_dataset

    def label_for_row(row: dict) -> str:
        lab = row["label"]
        if isinstance(lab, str):
            return lab.strip().lower()
        return _EMOTION_LABELS[int(lab)]

    rng = random.Random(seed)
    output.parent.mkdir(parents=True, exist_ok=True)

    reservoir: list[dict[str, str]] | None = [] if max_rows is not None else None
    cap = max_rows
    n_seen = 0

    def maybe_record(obj: dict[str, str]) -> None:
        nonlocal n_seen
        if reservoir is None or cap is None:
            return
        n_seen += 1
        if len(reservoir) < cap:
            reservoir.append(obj)
        else:
            j = rng.randrange(n_seen)  # 0 .. n_seen-1 inclusive
            if j < cap:
                reservoir[j] = obj

    written = 0
    with output.open("w", encoding="utf-8") as f:
        if reservoir is None:
            for split in splits:
                try:
                    stream = load_dataset("emotion", split=split, streaming=True)
                except Exception:
                    continue
                for row in stream:
                    text = str(row.get("text", "")).strip()
                    if not text:
                        continue
                    name = label_for_row(row)
                    if name == "love":
                        name = "joy"
                    rec = {"text": text, "label": name}
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    written += 1
        else:
            for split in splits:
                try:
                    stream = load_dataset("emotion", split=split, streaming=True)
                except Exception:
                    continue
                for row in stream:
                    text = str(row.get("text", "")).strip()
                    if not text:
                        continue
                    name = label_for_row(row)
                    if name == "love":
                        name = "joy"
                    maybe_record({"text": text, "label": name})
            assert reservoir is not None
            rng.shuffle(reservoir)
            for rec in reservoir:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                written += 1

    return written


def export_paws_paraphrase(
    output: Path,
    *,
    max_rows: int | None,
    seed: int,  # reserved for future shuffled caps
) -> int:
    """
    PAWS ``labeled_final``: sentence pairs where ``label == 1`` are paraphrases.

    Uses **streaming** so the full PAWS tables are not materialised in RAM (avoids
    OpenBLAS / memory failures on laptops). Order is split order then stream order;
    ``--max-rows`` stops after that many paraphrase pairs (no global shuffle).
    """
    from datasets import load_dataset

    output.parent.mkdir(parents=True, exist_ok=True)
    cap = max_rows if max_rows is not None else (1 << 30)
    n = 0
    with output.open("w", encoding="utf-8") as f:
        for split in ("train", "validation", "test"):
            try:
                stream = load_dataset("paws", "labeled_final", split=split, streaming=True)
            except Exception:
                continue
            for row in stream:
                if int(row.get("label", 0)) != 1:
                    continue
                s1 = str(row.get("sentence1", "")).strip()
                s2 = str(row.get("sentence2", "")).strip()
                if not s1 or not s2 or s1 == s2:
                    continue
                f.write(
                    json.dumps({"source": s1, "target": s2}, ensure_ascii=False) + "\n"
                )
                n += 1
                if n >= cap:
                    return n
    return n


def main() -> None:
    p = argparse.ArgumentParser(description="Export Hugging Face datasets to Bloom JSONL.")
    p.add_argument(
        "--dataset",
        choices=("jfleg", "emotion", "paws"),
        default="jfleg",
        help="jfleg=GEC; emotion=dair-ai/emotion; paws=paraphrase pairs (label==1)",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSONL path (defaults: data/jfleg_from_hf.jsonl, data/emotion_train.jsonl, data/paraphrase_train.jsonl)",
    )
    p.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Cap rows (emotion: reservoir sample; PAWS: first N stream pairs). Omit for full export.",
    )
    p.add_argument(
        "--seed",
        type=int,
        default=42,
        help="RNG seed when --max-rows truncates",
    )
    p.add_argument(
        "--emotion-splits",
        type=str,
        default="train,validation,test",
        help="Comma-separated splits for emotion (default: all official splits)",
    )
    args = p.parse_args()

    defaults: dict[str, Path] = {
        "jfleg": Path("data/jfleg_from_hf.jsonl"),
        "emotion": Path("data/emotion_train.jsonl"),
        "paws": Path("data/paraphrase_train.jsonl"),
    }
    out = args.output or defaults[args.dataset]

    if args.dataset == "jfleg":
        if args.max_rows is not None:
            print("Note: --max-rows is ignored for jfleg.", flush=True)
        count = export_jfleg(out)
    elif args.dataset == "emotion":
        splits = tuple(s.strip() for s in args.emotion_splits.split(",") if s.strip())
        count = export_emotion(out, splits=splits, max_rows=args.max_rows, seed=args.seed)
    elif args.dataset == "paws":
        count = export_paws_paraphrase(out, max_rows=args.max_rows, seed=args.seed)
    else:
        raise SystemExit("Unknown dataset")

    print(f"Wrote {count} lines to {out.resolve()}")


if __name__ == "__main__":
    main()
