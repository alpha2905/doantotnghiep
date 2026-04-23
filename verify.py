import json

input_file = r'data\phobert_train_aspect.jsonl'

# Kiểm tra xem còn dòng nào có label 'màn_hình_cảm_ứng' không
check_old_label = 0
check_new_label = 0

with open(input_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for line in lines:
        data = json.loads(line.strip())
        if data.get('label') == 'màn_hình_cảm_ứng':
            check_old_label += 1
        elif data.get('label') == 'màn_hình':
            check_new_label += 1

print("✓ Kiểm tra xác minh:")
print(f"  Số dòng còn có label cũ (màn_hình_cảm_ứng): {check_old_label}")
print(f"  Số dòng có label mới (màn_hình): {check_new_label}")
