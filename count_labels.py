import json
from collections import Counter
import os

# Paths to the JSONL files
sentiment_file = r'e:\ecommerce-price-comparison\data\phobert_train_sentiment.jsonl'
aspect_file = r'e:\ecommerce-price-comparison\data\phobert_train_aspect.jsonl'

# Expected aspect labels
expected_aspects = ['khác', 'pin', 'giá', 'hiệu_năng', 'màn_hình', 'camera', 
                    'thiết_kế', 'loa_âm_thanh', 'bảo_mật', 'hệ_điều_hành', 
                    'phụ_kiện', 'phục_vụ']

def count_labels(file_path, label_key):
    """Read JSONL file and count labels"""
    counter = Counter()
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return counter, 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    if label_key in data:
                        counter[data[label_key]] += 1
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return counter, sum(counter.values())

# Count sentiment labels
print("=" * 50)
print("Processing sentiment labels...")
print("=" * 50)
sentiment_counter, sentiment_total = count_labels(sentiment_file, 'label')

print("\nSENTIMENT:")
sentiment_labels = ['positive', 'neutral', 'negative']
for label in sentiment_labels:
    count = sentiment_counter.get(label, 0)
    percentage = (count / sentiment_total * 100) if sentiment_total > 0 else 0
    print(f"{label}: {count} ({percentage:.2f}%)")
print(f"Total: {sentiment_total}")

# Count aspect labels
print("\n" + "=" * 50)
print("Processing aspect labels...")
print("=" * 50)
aspect_counter, aspect_total = count_labels(aspect_file, 'label')

print("\nASPECT:")
for label in expected_aspects:
    count = aspect_counter.get(label, 0)
    percentage = (count / aspect_total * 100) if aspect_total > 0 else 0
    print(f"{label}: {count} ({percentage:.2f}%)")
print(f"Total: {aspect_total}")

# Show any unexpected aspect labels found
unexpected = set(aspect_counter.keys()) - set(expected_aspects)
if unexpected:
    print("\nUnexpected aspect labels found:")
    for label in unexpected:
        count = aspect_counter[label]
        percentage = (count / aspect_total * 100) if aspect_total > 0 else 0
        print(f"{label}: {count} ({percentage:.2f}%)")
