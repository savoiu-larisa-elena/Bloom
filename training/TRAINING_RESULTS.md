# Bloom training results

Source: `training_runs.jsonl` (5 run(s))

| # | Task | Finished (local) | Data file | Train n | Eval n | Train loss | Eval loss | Output dir | Base model |
|---|------|------------------|-----------|---------|--------|------------|-----------|------------|------------|
| 1 | gec | 2026-04-08T06:12:24 | `gec_bulk.jsonl` | 2689 | 299 | 0.2914 | 0.2814 | `gec-finetuned` | `vennify/t5-base-grammar-correction` |
| 2 | emotion | 2026-04-08T07:42:29 | `emotion_bulk.jsonl` | 18000 | 2000 | 0.0975 | 0.1305 | `emotion-finetuned` | `j-hartmann/emotion-english-distilroberta-base` |
| 3 | gec | 2026-04-27T01:46:59 | `jfleg_from_hf.jsonl` | 672 | 75 | 0.2924 | 0.3091 | `gec-finetuned` | `vennify/t5-base-grammar-correction` |
| 4 | emotion | 2026-04-27T03:05:56 | `emotion_train.jsonl` | 18000 | 2000 | 0.0975 | 0.1305 | `emotion-finetuned` | `j-hartmann/emotion-english-distilroberta-base` |
| 5 | paraphrase | 2026-04-27T13:05:29 | `paraphrase_train.jsonl` | 22500 | 2500 | 0.3191 | 0.3156 | `paraphrase-finetuned` | `Vamsi/T5_Paraphrase_Paws` |

## Notes

- Metrics are **validation loss** on a 10% held-out split (`seed=42`), best epoch by `eval_loss`.
- GEC bulk vs JFLEG used different data files; lower `eval_loss` on one does not rank the other.
- **Last write to `gec-finetuned`:** run #3 (JFLEG), after bulk run #1.
- Regenerate: `python show_training_results.py --markdown --out TRAINING_RESULTS.md`
