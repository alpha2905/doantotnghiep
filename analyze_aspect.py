import json
from collections import defaultdict

file_path = r"data\phobert_train_aspect.jsonl"
aspect_count = defaultdict(int)
all_data = []

print("\n" + "=" * 70)
print("PHÂN TÍCH - DỮ LIỆU ASPECT HIỆN TẠI (sử dụng field 'label')")
print("=" * 70)

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    aspect = data.get('label', 'unknown')
                    aspect_count[aspect] += 1
                    all_data.append(data)
                except:
                    pass
    
    total = sum(aspect_count.values())
    print(f"\nFile: {file_path}")
    print(f"Tổng bản ghi: {total:,}")
    print(f"\nPhân bố aspect (label):")
    
    sorted_aspects = sorted(aspect_count.items(), key=lambda x: x[1], reverse=True)
    for aspect, count in sorted_aspects:
        pct = (count / total) * 100 if total > 0 else 0
        bar = "█" * int(pct / 5)
        print(f"  {aspect:20} {count:5,} ({pct:6.2f}%) {bar}")
    
    if aspect_count:
        min_count = min(aspect_count.values())
        max_count = max(aspect_count.values())
        print(f"\nClass nhỏ nhất: {min_count} dòng")
        print(f"Class lớn nhất: {max_count} dòng")
except FileNotFoundError:
    print(f"Lỗi: Không tìm thấy file {file_path}")
except Exception as e:
    print(f"Lỗi: {e}")

print("=" * 70 + "\n")
