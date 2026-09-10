#!/usr/bin/env python3
"""
Dataset statistics + plots for Bloom training JSONL files.

Generates figures under: training/eval_results/dataset_stats/

Examples:
  python dataset_stats.py
  python dataset_stats.py --out-dir eval_results/dataset_stats
  python dataset_stats.py --gec data/jfleg_from_hf.jsonl --emotion data/emotion_train.jsonl --paraphrase data/paraphrase_train.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    if not rows:
        raise SystemExit(f"No rows in {path}")
    return rows


def _word_count(s: str) -> int:
    return len([w for w in s.strip().split() if w])


def _quantiles(xs: list[float], ps: list[float]) -> dict[str, float]:
    if not xs:
        return {str(p): float("nan") for p in ps}
    s = sorted(xs)
    out: dict[str, float] = {}
    n = len(s)
    for p in ps:
        if p <= 0:
            out[str(p)] = float(s[0])
            continue
        if p >= 1:
            out[str(p)] = float(s[-1])
            continue
        idx = p * (n - 1)
        lo = int(math.floor(idx))
        hi = int(math.ceil(idx))
        if lo == hi:
            out[str(p)] = float(s[lo])
        else:
            w = idx - lo
            out[str(p)] = float(s[lo] * (1 - w) + s[hi] * w)
    return out


def _summary(nums: list[float]) -> dict[str, float]:
    if not nums:
        return {}
    return {
        "n": float(len(nums)),
        "mean": float(mean(nums)),
        "median": float(median(nums)),
        "min": float(min(nums)),
        "max": float(max(nums)),
        "p10": _quantiles(nums, [0.10])["0.1"],
        "p90": _quantiles(nums, [0.90])["0.9"],
    }


@dataclass
class TextStats:
    char_len: list[int]
    word_len: list[int]


def _text_stats(texts: list[str]) -> TextStats:
    return TextStats(
        char_len=[len(t) for t in texts],
        word_len=[_word_count(t) for t in texts],
    )


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _try_import_matplotlib():
    try:
        import matplotlib.pyplot as plt  # noqa: F401

        return True
    except Exception:
        return False


def _save_hist_png(values: list[int], title: str, xlabel: str, out_path: Path) -> None:
    import matplotlib.pyplot as plt

    plt.figure(figsize=(7, 4))
    plt.hist(values, bins=40, color="#6b4c3b", alpha=0.85)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("Count")
    plt.grid(True, axis="y", alpha=0.2)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def _save_bar_png(labels: list[str], counts: list[int], title: str, out_path: Path) -> None:
    import matplotlib.pyplot as plt

    plt.figure(figsize=(7, 4))
    plt.bar(labels, counts, color="#6b4c3b", alpha=0.9)
    plt.title(title)
    plt.xlabel("Label")
    plt.ylabel("Count")
    plt.grid(True, axis="y", alpha=0.2)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--gec", type=Path, default=Path("data/jfleg_from_hf.jsonl"))
    p.add_argument("--emotion", type=Path, default=Path("data/emotion_train.jsonl"))
    p.add_argument("--paraphrase", type=Path, default=Path("data/paraphrase_train.jsonl"))
    p.add_argument("--out-dir", type=Path, default=Path("eval_results/dataset_stats"))
    args = p.parse_args()

    out_dir = args.out_dir
    _ensure_dir(out_dir)

    report: dict[str, Any] = {"files": {}, "stats": {}}

    # -------------------------
    # GEC (source/target)
    # -------------------------
    if args.gec.is_file():
        rows = _load_jsonl(args.gec)
        src = [str(r.get("source", "")).strip() for r in rows]
        tgt = [str(r.get("target", "")).strip() for r in rows]
        s_stats = _text_stats(src)
        t_stats = _text_stats(tgt)
        report["files"]["gec"] = str(args.gec)
        report["stats"]["gec"] = {
            "rows": len(rows),
            "source_chars": _summary([float(x) for x in s_stats.char_len]),
            "source_words": _summary([float(x) for x in s_stats.word_len]),
            "target_chars": _summary([float(x) for x in t_stats.char_len]),
            "target_words": _summary([float(x) for x in t_stats.word_len]),
            "identical_pairs": int(sum(1 for a, b in zip(src, tgt) if a == b)),
        }
    else:
        report["files"]["gec"] = {"missing": str(args.gec)}

    # -------------------------
    # Emotion (text/label)
    # -------------------------
    if args.emotion.is_file():
        rows = _load_jsonl(args.emotion)
        texts = [str(r.get("text", "")).strip() for r in rows]
        labels = [str(r.get("label", "")).strip().lower() for r in rows]
        t_stats = _text_stats(texts)
        c = Counter(labels)
        report["files"]["emotion"] = str(args.emotion)
        report["stats"]["emotion"] = {
            "rows": len(rows),
            "text_chars": _summary([float(x) for x in t_stats.char_len]),
            "text_words": _summary([float(x) for x in t_stats.word_len]),
            "label_counts": dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))),
        }
    else:
        report["files"]["emotion"] = {"missing": str(args.emotion)}

    # -------------------------
    # Paraphrase (source/target)
    # -------------------------
    if args.paraphrase.is_file():
        rows = _load_jsonl(args.paraphrase)
        src = [str(r.get("source", "")).strip() for r in rows]
        tgt = [str(r.get("target", "")).strip() for r in rows]
        s_stats = _text_stats(src)
        t_stats = _text_stats(tgt)
        report["files"]["paraphrase"] = str(args.paraphrase)
        report["stats"]["paraphrase"] = {
            "rows": len(rows),
            "source_chars": _summary([float(x) for x in s_stats.char_len]),
            "source_words": _summary([float(x) for x in s_stats.word_len]),
            "target_chars": _summary([float(x) for x in t_stats.char_len]),
            "target_words": _summary([float(x) for x in t_stats.word_len]),
            "identical_pairs": int(sum(1 for a, b in zip(src, tgt) if a == b)),
        }
    else:
        report["files"]["paraphrase"] = {"missing": str(args.paraphrase)}

    # Write JSON report
    (out_dir / "dataset_stats.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Plots (optional if matplotlib available)
    if not _try_import_matplotlib():
        print("Wrote dataset_stats.json (matplotlib not available; skipping plots).")
        return 0

    if "gec" in report["stats"]:
        gec = report["stats"]["gec"]
        # Note: stored as floats in report; use source stats direct from file for plotting
        rows = _load_jsonl(args.gec)
        src = [str(r.get("source", "")).strip() for r in rows]
        tgt = [str(r.get("target", "")).strip() for r in rows]
        _save_hist_png(
            [len(s) for s in src],
            "GEC (JFLEG export): source length distribution",
            "Characters per source sentence",
            out_dir / "gec_source_len_chars.png",
        )
        _save_hist_png(
            [_word_count(s) for s in src],
            "GEC (JFLEG export): source length distribution",
            "Words per source sentence",
            out_dir / "gec_source_len_words.png",
        )
        _save_hist_png(
            [_word_count(t) for t in tgt],
            "GEC (JFLEG export): target length distribution",
            "Words per target sentence",
            out_dir / "gec_target_len_words.png",
        )

    if "emotion" in report["stats"]:
        rows = _load_jsonl(args.emotion)
        labels = [str(r.get("label", "")).strip().lower() for r in rows]
        c = Counter(labels)
        labs = [k for k, _ in c.most_common()]
        vals = [c[k] for k in labs]
        _save_bar_png(
            labs,
            vals,
            "Emotion dataset: label distribution",
            out_dir / "emotion_label_distribution.png",
        )
        texts = [str(r.get("text", "")).strip() for r in rows]
        _save_hist_png(
            [_word_count(t) for t in texts],
            "Emotion dataset: text length distribution",
            "Words per text",
            out_dir / "emotion_text_len_words.png",
        )

    if "paraphrase" in report["stats"]:
        rows = _load_jsonl(args.paraphrase)
        src = [str(r.get("source", "")).strip() for r in rows]
        tgt = [str(r.get("target", "")).strip() for r in rows]
        _save_hist_png(
            [_word_count(s) for s in src],
            "Paraphrase dataset: source length distribution",
            "Words per source sentence",
            out_dir / "paraphrase_source_len_words.png",
        )
        _save_hist_png(
            [_word_count(t) for t in tgt],
            "Paraphrase dataset: target length distribution",
            "Words per target sentence",
            out_dir / "paraphrase_target_len_words.png",
        )

    print("Wrote:", (out_dir / "dataset_stats.json").resolve())
    print("Wrote plots under:", out_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

