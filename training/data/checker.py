import json
from collections import Counter

counts = Counter()

with open("emotion_train.jsonl", "r") as f:
    for line in f:
        obj = json.loads(line)
        counts[obj["label"]] += 1

total = sum(counts.values())

for label, count in counts.items():
    print(label, count, f"{count/total*100:.1f}%")

print("TOTAL:", total)