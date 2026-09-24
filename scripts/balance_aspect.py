import json
import random
from collections import defaultdict

file_path = r"data\phobert_train_aspect.jsonl"
output_path = r"data\phobert_train_aspect_balanced.jsonl"
aspect_data = defaultdict(list)

print("\n" + "=" * 70)
print("CÂN BẰNG DỮ LIỆU ASPECT")
print("=" * 70)

# Đọc dữ liệu
with open(file_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            try:
                data = json.loads(line)
                aspect = data.get('label', 'unknown')
                aspect_data[aspect].append(data)
            except:
                pass

# Thống kê trước
print("\n[TRƯỚC] Phân bố aspect:")
before_stats = {}
total_before = 0
for aspect in sorted(aspect_data.keys()):
    count = len(aspect_data[aspect])
    before_stats[aspect] = count
    total_before += count
    pct = (count / total_before * 100) if total_before > 0 else 0
    print(f"  {aspect:20} {count:5,}")

# Xác định baseline (loại bỏ phụ_kiện nếu có)
valid_counts = [len(v) for k, v in aspect_data.items() if k != 'phụ_kiện']
min_count = min(valid_counts) if valid_counts else 1
baseline = int(min_count * 1.5)
# Điều chỉnh baseline để đạt target ~50 per class
if baseline < 40:
    baseline = 50
    
print(f"\nMin count (không tính phụ_kiện): {min_count}")
print(f"Baseline cho undersampling: {baseline}")

# Undersampling
undersampled_data = []
after_stats = {}

for aspect in sorted(aspect_data.keys()):
    if aspect == 'phụ_kiện' and len(aspect_data[aspect]) == 0:
        print(f"  → Bỏ qua {aspect} (0 dòng)")
        continue
    
    samples = aspect_data[aspect]
    if len(samples) > baseline:
        # Undersampling
        sampled = random.sample(samples, baseline)
        print(f"  ↓ {aspect:20} {len(samples):5,} → {baseline:5,} (undersampled)")
    else:
        # Giữ nguyên nếu nhỏ hơn baseline
        sampled = samples
        if len(samples) < baseline:
            print(f"  - {aspect:20} {len(samples):5,} (giữ nguyên, nhỏ hơn baseline)")
        else:
            print(f"  = {aspect:20} {len(samples):5,} (bằng baseline)")
    
    undersampled_data.extend(sampled)
    after_stats[aspect] = len(sampled)

# Shuffle
random.shuffle(undersampled_data)

# Ghi file
with open(output_path, 'w', encoding='utf-8') as f:
    for data in undersampled_data:
        f.write(json.dumps(data, ensure_ascii=False) + '\n')

# Thống kê sau
print("\n[SAU] Phân bố aspect:")
total_after = 0
for aspect in sorted(after_stats.keys()):
    count = after_stats[aspect]
    total_after += count
    pct = (count / total_after * 100) if total_after > 0 else 0
    bar = "█" * int(pct / 5)
    print(f"  {aspect:20} {count:5,} ({pct:6.2f}%) {bar}")

# Tóm tắt
print("\n" + "=" * 70)
print("TÓM TẮT:")
print(f"  Tổng trước: {total_before:,} dòng")
print(f"  Tổng sau:  {total_after:,} dòng")
print(f"  Tỉ lệ:     {(total_after/total_before)*100:.1f}% dữ liệu được giữ lại")
print(f"  File output: {output_path}")
print("=" * 70 + "\n")
