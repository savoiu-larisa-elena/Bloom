from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from training_runs import RUNS_FILE


def load_runs(path: Path | None = None) -> list[dict]:
    runs_file = path or RUNS_FILE
    if not runs_file.is_file():
        return []
    runs: list[dict] = []
    with runs_file.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                runs.append(json.loads(line))
    return runs


def _data_basename(data_path: str) -> str:
    return Path(data_path).name


def _fmt_loss(v: object) -> str:
    if v is None:
        return "—"
    return f"{float(v):.4f}"


def print_table(runs: list[dict]) -> None:
    if not runs:
        print(f"No runs found in {RUNS_FILE}")
        print("Finish a train_gec.py / train_emotion.py / train_paraphrase.py run first.")
        return

    cols = ("#", "task", "finished (local)", "data", "train", "eval", "train_loss", "eval_loss", "output")
    widths = [3, 10, 26, 28, 6, 5, 10, 9, 36]
    header = "".join(h.ljust(w) for h, w in zip(cols, widths))
    print(header)
    print("-" * len(header))
    for i, r in enumerate(runs, 1):
        finished = (r.get("finished_at_local") or r.get("finished_at_utc") or "")[:26]
        row = (
            str(i),
            str(r.get("task", "?")),
            finished,
            _data_basename(str(r.get("data", ""))),
            str(r.get("train_rows", "")),
            str(r.get("eval_rows", "")),
            _fmt_loss(r.get("train_loss")),
            _fmt_loss(r.get("eval_loss")),
            Path(str(r.get("output", ""))).name,
        )
        print("".join(str(c).ljust(w)[:w] for c, w in zip(row, widths)))


def format_markdown(runs: list[dict]) -> str:
    lines = [
        "# Bloom training results",
        "",
        f"Source: `{RUNS_FILE.name}` ({len(runs)} run(s))",
        "",
        "| # | Task | Finished (local) | Data file | Train n | Eval n | Train loss | Eval loss | Output dir | Base model |",
        "|---|------|------------------|-----------|---------|--------|------------|-----------|------------|------------|",
    ]
    for i, r in enumerate(runs, 1):
        finished = (r.get("finished_at_local") or r.get("finished_at_utc") or "—")[:19]
        lines.append(
            "| {i} | {task} | {fin} | `{data}` | {tr} | {ev} | {tl} | {el} | `{out}` | `{base}` |".format(
                i=i,
                task=r.get("task", "?"),
                fin=finished,
                data=_data_basename(str(r.get("data", ""))),
                tr=r.get("train_rows", "—"),
                ev=r.get("eval_rows", "—"),
                tl=_fmt_loss(r.get("train_loss")),
                el=_fmt_loss(r.get("eval_loss")),
                out=Path(str(r.get("output", ""))).name,
                base=r.get("base_model", "—"),
            )
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Metrics are **validation loss** on a 10% held-out split (`seed=42`), best epoch by `eval_loss`.",
            "- GEC bulk vs JFLEG used different data files; lower `eval_loss` on one does not rank the other.",
            "- Regenerate this file: `python show_training_results.py --markdown --out TRAINING_RESULTS.md`",
            "",
        ]
    )
    return "\n".join(lines)


def format_latex_rows(runs: list[dict]) -> str:
    """LaTeX table rows for thesis tab:eval-runs (booktabs)."""
    task_labels = {
        "gec": "GEC (T5)",
        "emotion": "Emotion (RoBERTa)",
        "paraphrase": "Paraphrase (T5)",
    }
    lines: list[str] = []
    for r in runs:
        task = r.get("task", "")
        label = task_labels.get(task, task)
        data = _data_basename(str(r.get("data", ""))).replace("_", r"\_")
        tr = r.get("train_rows", "")
        ev = r.get("eval_rows", "")
        tl = _fmt_loss(r.get("train_loss"))
        el = _fmt_loss(r.get("eval_loss"))
        if tl != "—":
            tl = f"{float(r['train_loss']):.3f}"
        if el != "—":
            el = f"{float(r['eval_loss']):.3f}"
        lines.append(
            f"{label} & \\texttt{{{data}}} & {tr} & {ev} & {tl} & {el} \\\\"
        )
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="Show logged fine-tuning results.")
    p.add_argument("--file", type=Path, default=None, help="Alternate training_runs.jsonl path")
    p.add_argument("--markdown", action="store_true", help="Write markdown report")
    p.add_argument("--latex", action="store_true", help="Print LaTeX table rows to stdout")
    p.add_argument(
        "--out",
        type=Path,
        default=Path("TRAINING_RESULTS.md"),
        help="Output path for --markdown (default: TRAINING_RESULTS.md)",
    )
    p.add_argument("--json", action="store_true", help="Print raw runs as JSON array")
    args = p.parse_args()

    runs = load_runs(args.file)
    if args.json:
        print(json.dumps(runs, indent=2, ensure_ascii=False))
        return 0 if runs else 1

    if args.latex:
        if not runs:
            print("% No runs in training_runs.jsonl", file=sys.stderr)
            return 1
        print(format_latex_rows(runs))
        return 0

    if args.markdown:
        text = format_markdown(runs)
        args.out.write_text(text, encoding="utf-8")
        print(f"Wrote {args.out.resolve()}")
        return 0 if runs else 1

    print(f"File: {(args.file or RUNS_FILE).resolve()}\n")
    print_table(runs)
    if runs:
        print("\nTip: --markdown --out TRAINING_RESULTS.md  |  --latex for thesis rows")
    return 0 if runs else 1


if __name__ == "__main__":
    raise SystemExit(main())
