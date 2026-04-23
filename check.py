import pandas as pd

# 1. Đọc dữ liệu từ file của An
df = pd.read_csv('data/phobert_training_data.csv')

# 2. Tách các nhóm nhãn
df_neutral = df[df['sentiment'] == 'neutral']
df_negative = df[df['sentiment'] == 'negative']
df_positive = df[df['sentiment'] == 'positive']

# 3. Xử lý cân bằng:
# - Giảm Neutral xuống còn khoảng 2000 câu (Random Sampling)
df_neutral_downsampled = df_neutral.sample(n=2000, random_state=42)

# - Nhân bản Positive lên gấp 2 lần để model "nhớ mặt" từ khóa tích cực
df_positive_upsampled = pd.concat([df_positive] * 2, ignore_index=True)

# 4. Gộp lại thành bộ Dataset mới
df_balanced = pd.concat([df_neutral_downsampled, df_negative, df_positive_upsampled])

# 5. Xáo trộn dữ liệu (Shuffle) để model học khách quan
df_balanced = df_balanced.sample(frac=1, random_state=42).reset_index(drop=True)

# Xuất file mới
df_balanced.to_csv('data/phobert_training_data_v2.csv', index=False)
print("Đã tạo file v2 cân bằng hơn!")