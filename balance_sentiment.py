import json
import random
from collections import defaultdict

# Đọc file
input_file = r"data\phobert_train_sentiment.jsonl"
output_file = r"data\phobert_train_sentiment.jsonl"

# Đọc và phân loại dữ liệu
sentiment_data = defaultdict(list)
total_lines = 0

print("=" * 60)
print("PHÂN TÍCH DỮ LIỆU GỐC")
print("=" * 60)

with open(input_file, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            data = json.loads(line)
            label = data.get('label', 'unknown')
            sentiment_data[label].append(data)
            total_lines += 1

# In thống kê trước
print(f"\nTổng dòng: {total_lines}")
for sentiment, records in sorted(sentiment_data.items()):
    count = len(records)
    percentage = (count / total_lines) * 100
    print(f"  {sentiment}: {count:,} dòng ({percentage:.2f}%)")

# Tính baseline từ số lớp nhỏ nhất
min_count = min(len(records) for records in sentiment_data.values())
baseline = min_count * 3

print(f"\nSố lớp nhỏ nhất: {min_count}")
print(f"Baseline (min × 3): {baseline}")

# Tính số lượng target cho mỗi lớp
target_positive = int(baseline * 0.35)
target_neutral = int(baseline * 0.35)
target_negative = int(baseline * 0.30)
target_total = target_positive + target_neutral + target_negative

print(f"\n" + "=" * 60)
print("MỤC TIÊU CÂN BẰNG")
print("=" * 60)
print(f"  positive: {target_positive:,} ({(target_positive/target_total)*100:.2f}%)")
print(f"  neutral: {target_neutral:,} ({(target_neutral/target_total)*100:.2f}%)")
print(f"  negative: {target_negative:,} ({(target_negative/target_total)*100:.2f}%)")
print(f"  TỔNG: {target_total:,}")

# Undersampling
balanced_data = []
random.seed(42)

print(f"\n" + "=" * 60)
print("UNDERSAMPLING")
print("=" * 60)

for sentiment, target in [('positive', target_positive), 
                          ('neutral', target_neutral), 
                          ('negative', target_negative)]:
    if sentiment in sentiment_data:
        records = sentiment_data[sentiment]
        if len(records) > target:
            sampled = random.sample(records, target)
            print(f"  {sentiment}: {len(records):,} → {target:,} (lấy {target}/{len(records)})")
        else:
            sampled = records
            print(f"  {sentiment}: {len(records):,} → {len(records):,} (không đủ, lấy tất cả)")
        balanced_data.extend(sampled)

# Shuffle dữ liệu
random.shuffle(balanced_data)

# Ghi file
with open(output_file, 'w', encoding='utf-8') as f:
    for record in balanced_data:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')

# In thống kê sau
print(f"\n" + "=" * 60)
print("PHÂN TÍCH DỮ LIỆU SAU CÂN BẰNG")
print("=" * 60)

balanced_sentiment_count = defaultdict(int)
for record in balanced_data:
    label = record.get('label', 'unknown')
    balanced_sentiment_count[label] += 1

print(f"\nTổng dòng: {len(balanced_data):,}")
for sentiment in sorted(balanced_sentiment_count.keys()):
    count = balanced_sentiment_count[sentiment]
    percentage = (count / len(balanced_data)) * 100
    print(f"  {sentiment}: {count:,} dòng ({percentage:.2f}%)")

print(f"\n✓ File đã lưu: {output_file}")
print("=" * 60)
