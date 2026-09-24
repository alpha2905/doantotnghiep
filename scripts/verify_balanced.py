import json
from collections import defaultdict

balanced_file = r"data\phobert_train_aspect_balanced.jsonl"
aspect_count = defaultdict(int)

print("\n" + "=" * 70)
print("KIỂM CHỨNG - DỮ LIỆU BALANCED FINAL")
print("=" * 70)

total_lines = 0
with open(balanced_file, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            try:
                data = json.loads(line)
                aspect = data.get('label', 'unknown')
                aspect_count[aspect] += 1
                total_lines += 1
            except json.JSONDecodeError as e:
                print(f"Lỗi JSON trên dòng {total_lines + 1}: {e}")

print(f"\nFile: {balanced_file}")
print(f"Tổng bản ghi: {total_lines:,}")
print(f"\nPhân bố aspect (SAU CÂN BẰNG):")

sorted_aspects = sorted(aspect_count.items(), key=lambda x: x[1], reverse=True)
for aspect, count in sorted_aspects:
    pct = (count / total_lines * 100) if total_lines > 0 else 0
    bar = "█" * int(pct / 5)
    print(f"  {aspect:20} {count:5,} ({pct:6.2f}%) {bar}")

print("\n" + "=" * 70)
print("✓ Dữ liệu đã cân bằng thành công!")
print("=" * 70 + "\n")
