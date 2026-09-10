#!/usr/bin/env python3
"""
Fine-tune T5 for paraphrasing (same task shape as Bloom paraphrase: source -> paraphrase).

Usage:
  python train_paraphrase.py --data data/paraphrase_train.jsonl --output outputs/paraphrase-finetuned

Populate ``data/paraphrase_train.jsonl`` from PAWS with::

  python prepare_hf_dataset.py --dataset paws --output data/paraphrase_train.jsonl

Each JSONL line: {"source": "original sentence", "target": "paraphrased sentence"}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from datasets import Dataset
from transformers import (
    AutoModelForSeq2SeqLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
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
            rows.append({"source": obj["source"], "target": obj["target"]})
    if not rows:
        raise SystemExit(f"No rows in {path}")
    return rows


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--output", type=Path, default=Path("outputs/paraphrase-finetuned"))
    p.add_argument(
        "--model",
        default="Vamsi/T5_Paraphrase_Paws",
        help="Base T5 paraphrase checkpoint",
    )
    p.add_argument("--epochs", type=float, default=5.0)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--lr", type=float, default=3e-5)
    p.add_argument("--no-fp16", action="store_true")
    args = p.parse_args()

    rows = load_jsonl(args.data)
    dataset = Dataset.from_list(rows)
    split = dataset.train_test_split(test_size=0.1, seed=42)
    train_ds, eval_ds = split["train"], split["test"]

    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=False)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model)

    prefix = "paraphrase: "

    def preprocess(batch: dict) -> dict:
        inputs = [prefix + s for s in batch["source"]]
        model_inputs = tokenizer(inputs, max_length=256, truncation=True)
        labels = tokenizer(text_target=batch["target"], max_length=256, truncation=True)
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    train_tok = train_ds.map(preprocess, batched=True, remove_columns=train_ds.column_names)
    eval_tok = eval_ds.map(preprocess, batched=True, remove_columns=eval_ds.column_names)

    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model)

    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    training_args = Seq2SeqTrainingArguments(
        output_dir=str(out),
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=args.lr,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        num_train_epochs=args.epochs,
        weight_decay=0.01,
        predict_with_generate=True,
        fp16=not args.no_fp16,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        dataloader_pin_memory=torch.cuda.is_available(),
    )

    trainer = Seq2SeqTrainer(
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
        task="paraphrase",
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
    print("Done. Set BLOOM_PARAPHRASE_MODEL to:", out.resolve())
    print("Run logged for comparison:", log_file.resolve())


if __name__ == "__main__":
    main()
