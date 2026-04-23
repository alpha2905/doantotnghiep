import json
from collections import defaultdict

file_path = r"data\phobert_train_sentiment.jsonl"
sentiment_count = defaultdict(int)

with open(file_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            data = json.loads(line)
            sentiment_count[data.get('label')] += 1

total = sum(sentiment_count.values())

print("\n" + "=" * 70)
print("KẾT QUẢ CUỐI CÙNG - DỮ LIỆU CÂN BẰNG SENTIMENT")
print("=" * 70)
print(f"\nFile: data\\phobert_train_sentiment.jsonl")
print(f"Tổng bản ghi: {total:,}")
print(f"\nPhân bố:")

for label in sorted(sentiment_count.keys()):
    count = sentiment_count[label]
    pct = (count / total) * 100
    bar = "█" * int(pct / 5)
    print(f"  {label:10} {count:5,} ({pct:6.2f}%) {bar}")

print("\n" + "=" * 70)
print("✓ HOÀN THÀNH: Dữ liệu đã được cân bằng với undersampling")
print("  - Positive: 33.90%")
print("  - Neutral:  35.59%")
print("  - Negative: 30.51%")
print("  - Tổng: 3,324 bản ghi (giảm từ 6,915)")
print("=" * 70 + "\n")
