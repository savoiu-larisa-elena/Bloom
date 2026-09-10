#!/usr/bin/env python3
"""
Fine-tune DistilRoBERTa for emotion classification (same label space as the default Bloom model).

Usage:
  python train_emotion.py --data data/emotion_train.jsonl --output outputs/emotion-finetuned

Populate ``data/emotion_train.jsonl`` from the Hub with::

  python prepare_hf_dataset.py --dataset emotion --output data/emotion_train.jsonl

Each JSONL line: {"text": "sentence", "label": "joy"}
Labels must be a subset of: anger, disgust, fear, joy, neutral, sadness, surprise
(same string ids as j-hartmann/emotion-english-distilroberta-base). The public
``emotion`` (dair-ai) export maps ``love`` -> ``joy`` and omits disgust/neutral rows.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from datasets import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

from training_runs import append_training_run


def load_jsonl(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            rows.append({"text": obj["text"].strip(), "label": obj["label"].strip().lower()})
    if not rows:
        raise SystemExit(f"No rows in {path}")
    return rows


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--output", type=Path, default=Path("outputs/emotion-finetuned"))
    p.add_argument(
        "--model",
        default="j-hartmann/emotion-english-distilroberta-base",
        help="Base emotion classifier",
    )
    p.add_argument("--epochs", type=float, default=5.0)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--lr", type=float, default=2e-5)
    p.add_argument("--no-fp16", action="store_true")
    args = p.parse_args()

    rows = load_jsonl(args.data)
    dataset = Dataset.from_list(rows)
    split = dataset.train_test_split(test_size=0.1, seed=42)
    train_ds, eval_ds = split["train"], split["test"]

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSequenceClassification.from_pretrained(args.model)
    label2id: dict[str, int] = model.config.label2id

    unknown = {r["label"] for r in rows} - set(label2id.keys())
    if unknown:
        raise SystemExit(f"Unknown labels (not in model): {unknown}. Expected: {sorted(label2id)}")

    def preprocess(batch: dict) -> dict:
        enc = tokenizer(batch["text"], truncation=True, max_length=512)
        enc["labels"] = [label2id[l] for l in batch["label"]]
        return enc

    train_tok = train_ds.map(preprocess, batched=True, remove_columns=train_ds.column_names)
    eval_tok = eval_ds.map(preprocess, batched=True, remove_columns=eval_ds.column_names)

    data_collator = DataCollatorWithPadding(tokenizer)

    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(out),
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=args.lr,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        num_train_epochs=args.epochs,
        weight_decay=0.01,
        fp16=not args.no_fp16,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        dataloader_pin_memory=torch.cuda.is_available(),
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_tok,
        eval_dataset=eval_tok,
        processing_class=tokenizer,
        data_collator=data_collator,
    )

    trainer.train()
    trainer.save_model(str(out))
    tokenizer.save_pretrained(str(out))
    log_file = append_training_run(
        task="emotion",
        data_path=args.data,
        output_dir=out,
        base_model=args.model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        train_rows=len(train_tok),
        eval_rows=len(eval_tok),
        trainer=trainer,
    )
    print("Done. Set BLOOM_EMOTION_MODEL to:", out.resolve())
    print("Run logged for comparison:", log_file.resolve())


if __name__ == "__main__":
    main()
