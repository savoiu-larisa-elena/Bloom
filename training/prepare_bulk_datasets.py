#!/usr/bin/env python3
"""
Export LARGE public Hugging Face datasets to Bloom JSONL (streaming where possible).

  python prepare_bulk_datasets.py gec --output data/gec_bulk.jsonl
  python prepare_bulk_datasets.py emotion --output data/emotion_bulk.jsonl
  python prepare_bulk_datasets.py paraphrase --output data/paraphrase_bulk.jsonl

--max-rows caps total lines (per command). Omit for full export (very large / long training).

Licenses: JFLEG CC BY-NC-SA; PAWS CC BY-SA; emotion / go_emotions per Hugging Face dataset cards.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TextIO


def _write(f: TextIO, obj: dict[str, Any]) -> None:
    f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def export_jfleg_all_corrections(output: Path, max_rows: int | None) -> int:
    """JFLEG: one row per (sentence, correction); up to 4 refs per sentence."""
    from datasets import load_dataset

    n = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        ds = load_dataset("jhu-clsp/jfleg")
        for split in ("dev", "test"):
            if split not in ds:
                continue
            for row in ds[split]:
                src = (row.get("sentence") or "").strip()
                corrs = row.get("corrections") or []
                if not src or not corrs:
                    continue
                for c in corrs:
                    tgt = str(c).strip()
                    if not tgt:
                        continue
                    _write(f, {"source": src, "target": tgt})
                    n += 1
                    if max_rows is not None and n >= max_rows:
                        return n
    return n


def export_paws_paraphrase(
    output: Path,
    max_rows: int | None,
    config: str = "labeled_final",
) -> int:
    """PAWS: paraphrase pairs (label == 1)."""
    from datasets import load_dataset

    n = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    ds = load_dataset("paws", config, split="train", streaming=True)
    with output.open("w", encoding="utf-8") as out:
        for row in ds:
            if row.get("label") != 1:
                continue
            s1 = (row.get("sentence1") or "").strip()
            s2 = (row.get("sentence2") or "").strip()
            if not s1 or not s2:
                continue
            _write(out, {"source": s1, "target": s2})
            n += 1
            if max_rows is not None and n >= max_rows:
                break
    return n


_DAIR_TO_7 = {
    0: "sadness",
    1: "joy",
    2: "joy",
    3: "anger",
    4: "fear",
    5: "surprise",
}

_GO28_TO_7: dict[str, str] = {
    "admiration": "joy",
    "amusement": "joy",
    "anger": "anger",
    "annoyance": "anger",
    "approval": "joy",
    "caring": "joy",
    "confusion": "surprise",
    "curiosity": "surprise",
    "desire": "joy",
    "disappointment": "sadness",
    "disapproval": "anger",
    "disgust": "disgust",
    "embarrassment": "fear",
    "excitement": "joy",
    "fear": "fear",
    "gratitude": "joy",
    "grief": "sadness",
    "joy": "joy",
    "love": "joy",
    "nervousness": "fear",
    "optimism": "joy",
    "pride": "joy",
    "realization": "surprise",
    "relief": "joy",
    "remorse": "sadness",
    "sadness": "sadness",
    "surprise": "surprise",
    "neutral": "neutral",
}


def export_emotion_combined(
    output: Path,
    max_rows: int | None,
    skip_dair: bool,
    skip_go: bool,
) -> int:
    """dair-ai emotion + go_emotions simplified, mapped to 7 labels."""
    from datasets import load_dataset

    n = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        if not skip_dair:
            for split in ("train", "validation", "test"):
                try:
                    ds = load_dataset("emotion", split=split)
                except Exception as exc:
                    print(f"skip emotion/{split}: {exc}", file=sys.stderr)
                    continue
                for row in ds:
                    text = (row.get("text") or "").strip()
                    if not text:
                        continue
                    lab = row.get("label")
                    if lab is None:
                        continue
                    label = _DAIR_TO_7.get(int(lab))
                    if label is None:
                        continue
                    _write(f, {"text": text, "label": label})
                    n += 1
                    if max_rows is not None and n >= max_rows:
                        return n

        if skip_go or (max_rows is not None and n >= max_rows):
            return n

        try:
            peek = load_dataset("go_emotions", "simplified", split="train[:1]")
            go_names = list(peek.features["labels"].names)  # type: ignore[union-attr]
        except Exception as exc:
            print(f"skip go_emotions (features): {exc}", file=sys.stderr)
            return n

        try:
            ds_go = load_dataset("go_emotions", "simplified", split="train", streaming=True)
        except Exception as exc:
            print(f"skip go_emotions: {exc}", file=sys.stderr)
            return n

        for row in ds_go:
            if max_rows is not None and n >= max_rows:
                break
            text = (row.get("text") or "").strip()
            if not text:
                continue
            raw = row.get("labels")
            if raw is None:
                continue
            idx = int(raw[0]) if isinstance(raw, (list, tuple)) else int(raw)
            if idx < 0 or idx >= len(go_names):
                continue
            name = str(go_names[idx]).lower().replace(" ", "_")
            label = _GO28_TO_7.get(name)
            if label is None:
                continue
            _write(f, {"text": text, "label": label})
            n += 1

    return n


def cmd_gec(args: argparse.Namespace) -> None:
    n = export_jfleg_all_corrections(args.output, args.max_rows)
    print(f"Wrote {n} GEC lines -> {args.output.resolve()}")


def cmd_paraphrase(args: argparse.Namespace) -> None:
    n = export_paws_paraphrase(args.output, args.max_rows, config=args.paws_config)
    print(f"Wrote {n} paraphrase lines -> {args.output.resolve()}")


def cmd_emotion(args: argparse.Namespace) -> None:
    n = export_emotion_combined(
        args.output,
        args.max_rows,
        skip_dair=args.skip_dair,
        skip_go=args.skip_go,
    )
    print(f"Wrote {n} emotion lines -> {args.output.resolve()}")


def main() -> None:
    p = argparse.ArgumentParser(description="Export large HF datasets to JSONL")
    sub = p.add_subparsers(dest="cmd", required=True)

    pg = sub.add_parser("gec", help="JFLEG all correction refs (~3k lines)")
    pg.add_argument("--output", type=Path, default=Path("data/gec_bulk.jsonl"))
    pg.add_argument("--max-rows", type=int, default=None)
    pg.set_defaults(func=cmd_gec)

    pp = sub.add_parser("paraphrase", help="PAWS paraphrase (~49k in labeled_final)")
    pp.add_argument("--output", type=Path, default=Path("data/paraphrase_bulk.jsonl"))
    pp.add_argument("--max-rows", type=int, default=None)
    pp.add_argument("--paws-config", default="labeled_final")
    pp.set_defaults(func=cmd_paraphrase)

    pe = sub.add_parser("emotion", help="dair-ai emotion + go_emotions (100k+)")
    pe.add_argument("--output", type=Path, default=Path("data/emotion_bulk.jsonl"))
    pe.add_argument("--max-rows", type=int, default=None)
    pe.add_argument("--skip-dair", action="store_true")
    pe.add_argument("--skip-go", action="store_true")
    pe.set_defaults(func=cmd_emotion)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
