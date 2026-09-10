#!/usr/bin/env python3
"""
Post-training evaluation: fine-tuned vs base checkpoints.

Produces thesis-ready tables in training/eval_results/:
  - emotion_metrics.json + emotion_confusion_matrix.png
  - gec_metrics.json + gec_manual_predictions.jsonl
  - paraphrase_metrics.json + paraphrase_manual_predictions.jsonl
  - EVALUATION_REPORT.md

Usage (from training/, after fine-tuned weights exist under outputs/):
  pip install -r requirements-eval.txt
  python evaluate_checkpoints.py --task all
  python evaluate_checkpoints.py --task emotion
  python evaluate_checkpoints.py --task gec --quick
  python evaluate_checkpoints.py --task paraphrase --bertscore --max-eval 500
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from eval_common import (
    EVAL_RESULTS_DIR,
    TRAINING_DIR,
    checkpoint_ready,
    exact_match_rate,
    load_jsonl,
    normalize_text,
    setup_bloom_cache_env,
    train_eval_split,
    write_json,
)

# Must run before torch/transformers Hub access (avoids bad HF_HOME e.g. F:\)
_hf_cache = setup_bloom_cache_env()

import torch  # noqa: E402

# ---------------------------------------------------------------------------
# Optional metric libraries
# ---------------------------------------------------------------------------


def _require_sklearn():
    try:
        import sklearn  # noqa: F401
    except ImportError as exc:
        raise SystemExit("Install: pip install scikit-learn") from exc


def _sacrebleu_corpus(hypotheses: list[str], references: list[str]) -> dict[str, float]:
    import sacrebleu

    bleu = sacrebleu.corpus_bleu(hypotheses, [references])
    chrf = sacrebleu.corpus_chrf(hypotheses, [references])
    return {"bleu": round(bleu.score, 2), "chrf": round(chrf.score, 2)}


def _rouge_l(hypotheses: list[str], references: list[str]) -> float:
    from rouge_score import rouge_scorer

    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    scores = [scorer.score(r, h)["rougeL"].fmeasure for h, r in zip(hypotheses, references)]
    return round(sum(scores) / len(scores), 4) if scores else 0.0


def _gleu_corpus(hypotheses: list[str], references: list[str]) -> float | None:
    try:
        from nltk.translate.gleu_score import sentence_gleu
    except ImportError:
        return None
    total = 0.0
    for hyp, ref in zip(hypotheses, references):
        ref_toks = [ref.split()]
        hyp_toks = hyp.split()
        total += sentence_gleu(ref_toks, hyp_toks, min_len=1, max_len=4)
    return round(total / len(hypotheses), 4) if hypotheses else 0.0


def _bertscore_f1(hypotheses: list[str], references: list[str]) -> float | None:
    try:
        from bert_score import score as bert_score
    except ImportError:
        return None
    _, _, f1 = bert_score(hypotheses, references, lang="en", verbose=False)
    return round(f1.mean().item(), 4)


def _seq_metrics(hypotheses: list[str], references: list[str], bertscore: bool) -> dict[str, Any]:
    out: dict[str, Any] = {
        "n": len(hypotheses),
        "exact_match": round(exact_match_rate(hypotheses, references), 4),
    }
    if not hypotheses:
        return out
    try:
        out.update(_sacrebleu_corpus(hypotheses, references))
    except ImportError:
        out["bleu"] = None
        out["chrf"] = None
    gleu = _gleu_corpus(hypotheses, references)
    if gleu is not None:
        out["gleu"] = gleu
    try:
        out["rouge_l"] = _rouge_l(hypotheses, references)
    except ImportError:
        out["rouge_l"] = None
    if bertscore:
        bs = _bertscore_f1(hypotheses, references)
        if bs is not None:
            out["bertscore_f1"] = bs
    return out


# ---------------------------------------------------------------------------
# Seq2seq generation (GEC / paraphrase)
# ---------------------------------------------------------------------------


def generate_seq2seq(
    model_id: str,
    sources: list[str],
    *,
    prefix: str,
    use_fast_tokenizer: bool = True,
    num_beams: int = 4,
    batch_size: int = 8,
    max_input: int = 256,
    max_new: int = 128,
) -> list[str]:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=use_fast_tokenizer)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_id)
    model.eval()
    model.to(device)

    outputs: list[str] = []
    for i in range(0, len(sources), batch_size):
        chunk = sources[i : i + batch_size]
        inputs = [prefix + s for s in chunk]
        enc = tokenizer(
            inputs,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_input,
        ).to(device)
        with torch.no_grad():
            ids = model.generate(
                **enc,
                max_new_tokens=max_new,
                num_beams=num_beams,
                early_stopping=True,
            )
        decoded = tokenizer.batch_decode(ids, skip_special_tokens=True)
        outputs.extend(d.strip() for d in decoded)
    return outputs


def compare_pair(
    label: str,
    base_id: str,
    tuned_id: str | None,
    hypotheses_fn,
    references: list[str],
    *,
    bertscore: bool,
) -> dict[str, Any]:
    base_h = hypotheses_fn(base_id)
    base_m = _seq_metrics(base_h, references, bertscore)
    base_m["model"] = base_id

    block: dict[str, Any] = {"label": label, "references_n": len(references), "base": base_m}
    if tuned_id and checkpoint_ready(Path(tuned_id)):
        tuned_h = hypotheses_fn(tuned_id)
        tuned_m = _seq_metrics(tuned_h, references, bertscore)
        tuned_m["model"] = tuned_id
        block["finetuned"] = tuned_m
        block["delta_exact_match"] = round(
            tuned_m["exact_match"] - base_m["exact_match"], 4
        )
        if tuned_m.get("bleu") is not None and base_m.get("bleu") is not None:
            block["delta_bleu"] = round(tuned_m["bleu"] - base_m["bleu"], 2)
    else:
        block["finetuned"] = {
            "skipped": True,
            "reason": f"Checkpoint not found: {tuned_id}",
        }
    return block


# ---------------------------------------------------------------------------
# Emotion classification
# ---------------------------------------------------------------------------


def eval_emotion(
    *,
    data: Path,
    base_model: str,
    finetuned: Path,
    out_dir: Path,
    max_eval: int | None,
) -> dict[str, Any]:
    _require_sklearn()
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        confusion_matrix,
        f1_score,
        precision_recall_fscore_support,
    )
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    rows = load_jsonl(data)
    for r in rows:
        r["label"] = r["label"].strip().lower()
    _, eval_rows = train_eval_split(rows)
    if max_eval:
        eval_rows = eval_rows[:max_eval]

    texts = [r["text"] for r in eval_rows]
    gold_labels = [r["label"] for r in eval_rows]

    def predict(model_id: str) -> list[str]:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForSequenceClassification.from_pretrained(model_id)
        model.eval()
        model.to(device)
        label2id = model.config.label2id
        id2label = {int(v): k for k, v in label2id.items()}

        preds: list[str] = []
        bs = 32
        for i in range(0, len(texts), bs):
            enc = tokenizer(
                texts[i : i + bs],
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512,
            ).to(device)
            with torch.no_grad():
                logits = model(**enc).logits
            ids = logits.argmax(dim=-1).cpu().tolist()
            preds.extend(id2label[i] for i in ids)
        return preds

    def metrics_block(model_id: str, preds: list[str]) -> dict[str, Any]:
        acc = accuracy_score(gold_labels, preds)
        p_macro, r_macro, f_macro, _ = precision_recall_fscore_support(
            gold_labels, preds, average="macro", zero_division=0
        )
        p_w, r_w, f_w, _ = precision_recall_fscore_support(
            gold_labels, preds, average="weighted", zero_division=0
        )
        return {
            "model": model_id,
            "accuracy": round(acc, 4),
            "precision_macro": round(p_macro, 4),
            "recall_macro": round(r_macro, 4),
            "f1_macro": round(f_macro, 4),
            "precision_weighted": round(p_w, 4),
            "recall_weighted": round(r_w, 4),
            "f1_weighted": round(f_w, 4),
            "classification_report": classification_report(
                gold_labels, preds, zero_division=0
            ),
        }

    base_preds = predict(base_model)
    result: dict[str, Any] = {
        "task": "emotion",
        "data": str(data.resolve()),
        "eval_n": len(eval_rows),
        "split": "10% hold-out, seed=42 (same as train_emotion.py)",
        "base": metrics_block(base_model, base_preds),
    }

    tuned_path = str(finetuned.resolve())
    if checkpoint_ready(finetuned):
        tuned_preds = predict(tuned_path)
        result["finetuned"] = metrics_block(tuned_path, tuned_preds)
        result["delta"] = {
            "accuracy": round(result["finetuned"]["accuracy"] - result["base"]["accuracy"], 4),
            "f1_macro": round(result["finetuned"]["f1_macro"] - result["base"]["f1_macro"], 4),
        }
        labels = sorted(set(gold_labels) | set(tuned_preds))
        cm = confusion_matrix(gold_labels, tuned_preds, labels=labels)
        result["confusion_matrix"] = {"labels": labels, "matrix": cm.tolist()}

        _save_confusion_matrix_png(labels, cm, out_dir / "emotion_confusion_matrix.png")
    else:
        result["finetuned"] = {"skipped": True, "reason": f"Missing {finetuned}"}
        labels = sorted(set(gold_labels))
        cm = confusion_matrix(gold_labels, base_preds, labels=labels)
        result["confusion_matrix"] = {"labels": labels, "matrix": cm.tolist()}
        _save_confusion_matrix_png(labels, cm, out_dir / "emotion_confusion_matrix_base.png")

    write_json(out_dir / "emotion_metrics.json", result)
    return result


def _save_confusion_matrix_png(labels: list[str], cm, path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
    ax.figure.colorbar(im, ax=ax)
    ax.set(
        xticks=np.arange(len(labels)),
        yticks=np.arange(len(labels)),
        xticklabels=labels,
        yticklabels=labels,
        ylabel="True label",
        xlabel="Predicted label",
        title="Emotion classifier (fine-tuned, eval split)",
    )
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
    thresh = cm.max() / 2.0 if cm.max() else 0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], "d"), ha="center", va="center", color="white" if cm[i, j] > thresh else "black")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# GEC
# ---------------------------------------------------------------------------


def eval_gec(
    *,
    data: Path,
    manual: Path,
    base_model: str,
    finetuned: Path,
    out_dir: Path,
    max_eval: int | None,
    bertscore: bool,
    num_beams: int,
) -> dict[str, Any]:
    rows = load_jsonl(data)
    _, eval_rows = train_eval_split(rows)
    if max_eval:
        eval_rows = eval_rows[:max_eval]

    def hypo_fn(model_id: str) -> list[str]:
        sources = [r["source"] for r in eval_rows]
        return generate_seq2seq(
            model_id,
            sources,
            prefix="grammar: ",
            num_beams=num_beams,
        )

    references = [r["target"] for r in eval_rows]
    validation = compare_pair(
        "jfleg_validation_split",
        base_model,
        str(finetuned.resolve()),
        hypo_fn,
        references,
        bertscore=bertscore,
    )

    manual_rows = load_jsonl(manual)
    manual_sources = [r["source"] for r in manual_rows]
    manual_refs = [r["target"] for r in manual_rows]

    def manual_hypo(model_id: str) -> list[str]:
        return generate_seq2seq(
            model_id,
            manual_sources,
            prefix="grammar: ",
            num_beams=num_beams,
        )

    manual_block = compare_pair(
        "manual_grammar_sentences",
        base_model,
        str(finetuned.resolve()),
        manual_hypo,
        manual_refs,
        bertscore=bertscore,
    )

    manual_preds: list[dict[str, str]] = []
    if checkpoint_ready(finetuned):
        tuned_h = manual_hypo(str(finetuned.resolve()))
        base_h = manual_hypo(base_model)
        for row, b, t, g in zip(manual_rows, base_h, tuned_h, manual_refs):
            manual_preds.append(
                {
                    "source": row["source"],
                    "gold": g,
                    "base_prediction": b,
                    "finetuned_prediction": t,
                }
            )
    write_jsonl(out_dir / "gec_manual_predictions.jsonl", manual_preds)

    result = {
        "task": "gec",
        "data": str(data.resolve()),
        "manual_file": str(manual.resolve()),
        "eval_n": len(eval_rows),
        "manual_n": len(manual_rows),
        "split": "10% hold-out, seed=42",
        "validation": validation,
        "manual_eval": manual_block,
    }
    write_json(out_dir / "gec_metrics.json", result)
    return result


# ---------------------------------------------------------------------------
# Paraphrase
# ---------------------------------------------------------------------------


def eval_paraphrase(
    *,
    data: Path,
    manual: Path,
    base_model: str,
    finetuned: Path,
    out_dir: Path,
    max_eval: int | None,
    bertscore: bool,
    num_beams: int,
) -> dict[str, Any]:
    rows = load_jsonl(data)
    _, eval_rows = train_eval_split(rows)
    if max_eval:
        eval_rows = eval_rows[:max_eval]

    def hypo_fn(model_id: str) -> list[str]:
        sources = [r["source"] for r in eval_rows]
        return generate_seq2seq(
            model_id,
            sources,
            prefix="paraphrase: ",
            use_fast_tokenizer=False,
            num_beams=num_beams,
        )

    references = [r["target"] for r in eval_rows]
    validation = compare_pair(
        "paraphrase_validation_split",
        base_model,
        str(finetuned.resolve()),
        hypo_fn,
        references,
        bertscore=bertscore,
    )

    manual_rows = load_jsonl(manual)
    manual_sources = [r["source"] for r in manual_rows]
    manual_refs = [r["target"] for r in manual_rows]

    def manual_hypo(model_id: str) -> list[str]:
        return generate_seq2seq(
            model_id,
            manual_sources,
            prefix="paraphrase: ",
            use_fast_tokenizer=False,
            num_beams=num_beams,
        )

    manual_block = compare_pair(
        "manual_paraphrase_examples",
        base_model,
        str(finetuned.resolve()),
        manual_hypo,
        manual_refs,
        bertscore=bertscore,
    )

    manual_preds: list[dict[str, str]] = []
    base_h = manual_hypo(base_model)
    tuned_h = (
        manual_hypo(str(finetuned.resolve()))
        if checkpoint_ready(finetuned)
        else [""] * len(manual_rows)
    )
    for row, b, t in zip(manual_rows, base_h, tuned_h):
        manual_preds.append(
            {
                "source": row["source"],
                "reference_paraphrase": row["target"],
                "base_prediction": b,
                "finetuned_prediction": t if checkpoint_ready(finetuned) else None,
                "note": row.get("note", ""),
            }
        )
    write_jsonl(out_dir / "paraphrase_manual_predictions.jsonl", manual_preds)

    result = {
        "task": "paraphrase",
        "data": str(data.resolve()),
        "manual_file": str(manual.resolve()),
        "eval_n": len(eval_rows),
        "manual_n": len(manual_rows),
        "validation": validation,
        "manual_eval": manual_block,
    }
    write_json(out_dir / "paraphrase_metrics.json", result)
    return result


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


def _fmt_seq_row(name: str, m: dict[str, Any]) -> str:
    parts = [
        f"**{name}**",
        f"n={m.get('n', '?')}",
        f"exact={m.get('exact_match', '—')}",
        f"BLEU={m.get('bleu', '—')}",
        f"chrF={m.get('chrf', '—')}",
        f"GLEU={m.get('gleu', '—')}",
        f"ROUGE-L={m.get('rouge_l', '—')}",
    ]
    if "bertscore_f1" in m:
        parts.append(f"BERTScore F1={m['bertscore_f1']}")
    return " | ".join(parts)


def write_markdown_report(results: dict[str, Any], path: Path) -> None:
    lines = [
        "# Bloom post-training evaluation",
        "",
        "Generated by `evaluate_checkpoints.py`. Use these numbers in the thesis **only after** you run the script on your machine with real checkpoints in `outputs/`.",
        "",
        "> Split: same 10% validation partition as training (`seed=42`). Seq2seq: beam search (default 4).",
        "",
    ]

    if "emotion" in results:
        e = results["emotion"]
        lines.extend(["## Emotion (DistilRoBERTa)", "", f"Eval samples: **{e['eval_n']}**", ""])
        b, f = e["base"], e.get("finetuned", {})
        lines.append(
            "| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) |"
        )
        lines.append("|-------|----------|-------------------|----------------|------------|")
        lines.append(
            f"| Base | {b['accuracy']} | {b['precision_macro']} | {b['recall_macro']} | {b['f1_macro']} |"
        )
        if not f.get("skipped"):
            lines.append(
                f"| Fine-tuned | {f['accuracy']} | {f['precision_macro']} | {f['recall_macro']} | {f['f1_macro']} |"
            )
            if "delta" in e:
                d = e["delta"]
                lines.append(f"\n**Δ (fine-tuned − base):** accuracy {d['accuracy']:+.4f}, macro-F1 {d['f1_macro']:+.4f}")
        lines.append("\nConfusion matrix: `eval_results/emotion_confusion_matrix.png`\n")

    if "gec" in results:
        g = results["gec"]
        lines.extend(["## Grammar correction (T5 GEC)", ""])
        for key, block in (("validation", g["validation"]), ("manual_eval", g["manual_eval"])):
            lines.append(f"### {block['label']}")
            lines.append(_fmt_seq_row("Base", block["base"]))
            ft = block.get("finetuned", {})
            if not ft.get("skipped"):
                lines.append(_fmt_seq_row("Fine-tuned", ft))
                if "delta_bleu" in block:
                    lines.append(f"\nΔ BLEU: **{block['delta_bleu']:+.2f}**, Δ exact match: **{block['delta_exact_match']:+.4f}**")
            lines.append("")
        lines.append("Manual examples: `eval_results/gec_manual_predictions.jsonl`\n")

    if "paraphrase" in results:
        p = results["paraphrase"]
        lines.extend(["## Paraphrase (T5)", ""])
        for key, block in (("validation", p["validation"]), ("manual_eval", p["manual_eval"])):
            lines.append(f"### {block['label']}")
            lines.append(_fmt_seq_row("Base", block["base"]))
            ft = block.get("finetuned", {})
            if not ft.get("skipped"):
                lines.append(_fmt_seq_row("Fine-tuned", ft))
            lines.append("")
        lines.append("Manual examples: `eval_results/paraphrase_manual_predictions.jsonl`\n")

    lines.extend(
        [
            "## Thesis LaTeX (paste after you have real numbers)",
            "",
            "Replace placeholders with values from the JSON files in this folder.",
            "",
            "```latex",
            "% Emotion: Table — validation split, seed=42",
            "% Fine-tuned macro-F1 = ???  (base = ???)",
            "",
            "% GEC: BLEU / GLEU / exact match on JFLEG val + 30 manual sentences",
            "",
            "% Paraphrase: BLEU, ROUGE-L, BERTScore F1 on val + manual set",
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description="Evaluate Bloom fine-tuned checkpoints vs base.")
    p.add_argument("--task", choices=("emotion", "gec", "paraphrase", "all"), default="all")
    p.add_argument("--quick", action="store_true", help="Small eval subsets for smoke test")
    p.add_argument("--full", action="store_true", help="Use full validation split (no cap)")
    p.add_argument("--max-eval", type=int, default=None, help="Cap validation rows per task")
    p.add_argument("--bertscore", action="store_true", help="Compute BERTScore (slow)")
    p.add_argument("--num-beams", type=int, default=4)
    p.add_argument("--emotion-data", type=Path, default=TRAINING_DIR / "data/emotion_train.jsonl")
    p.add_argument("--gec-data", type=Path, default=TRAINING_DIR / "data/jfleg_from_hf.jsonl")
    p.add_argument("--gec-manual", type=Path, default=TRAINING_DIR / "data/gec_manual_test.jsonl")
    p.add_argument("--paraphrase-data", type=Path, default=TRAINING_DIR / "data/paraphrase_train.jsonl")
    p.add_argument("--paraphrase-manual", type=Path, default=TRAINING_DIR / "data/paraphrase_manual_test.jsonl")
    p.add_argument("--emotion-base", default="j-hartmann/emotion-english-distilroberta-base")
    p.add_argument("--emotion-finetuned", type=Path, default=TRAINING_DIR / "outputs/emotion-finetuned")
    p.add_argument("--gec-base", default="vennify/t5-base-grammar-correction")
    p.add_argument("--gec-finetuned", type=Path, default=TRAINING_DIR / "outputs/gec-finetuned")
    p.add_argument("--paraphrase-base", default="Vamsi/T5_Paraphrase_Paws")
    p.add_argument("--paraphrase-finetuned", type=Path, default=TRAINING_DIR / "outputs/paraphrase-finetuned")
    args = p.parse_args()

    max_eval: int | None = None if args.full else args.max_eval
    if args.quick and max_eval is None:
        max_eval = 75

    out_dir = EVAL_RESULTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"HF cache: {_hf_cache}", flush=True)

    results: dict[str, Any] = {}
    tasks = ["emotion", "gec", "paraphrase"] if args.task == "all" else [args.task]

    for task in tasks:
        print(f"\n=== {task} ===", flush=True)
        if task == "emotion":
            results["emotion"] = eval_emotion(
                data=args.emotion_data,
                base_model=args.emotion_base,
                finetuned=args.emotion_finetuned,
                out_dir=out_dir,
                max_eval=max_eval,
            )
        elif task == "gec":
            results["gec"] = eval_gec(
                data=args.gec_data,
                manual=args.gec_manual,
                base_model=args.gec_base,
                finetuned=args.gec_finetuned,
                out_dir=out_dir,
                max_eval=max_eval,
                bertscore=args.bertscore,
                num_beams=args.num_beams,
            )
        elif task == "paraphrase":
            cap = max_eval if max_eval is not None else (200 if args.quick else 500)
            results["paraphrase"] = eval_paraphrase(
                data=args.paraphrase_data,
                manual=args.paraphrase_manual,
                base_model=args.paraphrase_base,
                finetuned=args.paraphrase_finetuned,
                out_dir=out_dir,
                max_eval=cap,
                bertscore=args.bertscore,
                num_beams=args.num_beams,
            )

    write_markdown_report(results, out_dir / "EVALUATION_REPORT.md")
    write_json(out_dir / "evaluation_summary.json", results)
    print(f"\nWrote {out_dir.resolve()}")
    print("Open EVALUATION_REPORT.md for thesis tables.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
