# -*- coding: utf-8 -*-
"""
Script tạo dữ liệu mẫu cho PhoBERT training.
Tạo file JSONL với format:
- Sentiment: {"text": "...", "label": "positive/neutral/negative"}
- Aspect: {"text": "...", "label": "camera/pin/giá/..."}
"""
import os
import sys
import json
import random

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Template sentences cho sentiment
positive_templates = [
    "Sản phẩm rất tốt, chất lượng cao, đáng mua",
    "Pin trâu, dùng cả ngày không hết, rất hài lòng",
    "Màn hình đẹp, màu sắc chân thật, xem phim rất đã",
    "Camera chụp rõ nét, chụp đêm cũng ổn",
    "Giá tốt, rẻ hơn các cửa hàng khác nhiều",
    "Đáng tiền, shop uy tín, giao hàng nhanh",
    "Sản phẩm chính hãng, đóng gói cẩn thận",
    "Mượt mà, chạy game rất ổn định, không lag",
    "Thiết kế đẹp, cầm chắc tay, sang trọng",
    "Tốt hơn mong đợi, sẽ ủng hộ shop lần sau",
]

neutral_templates = [
    "Sản phẩm tạm được, không có gì đặc biệt",
    "Dùng được, không có lỗi gì nghiêm trọng",
    "Giá cả phải chăng, không đắt không rẻ",
    "Điện thoại mẫu, thời gian sử dụng bình thường",
    "Màn hình khá, không quá sáng cũng không quá tối",
    "Camera ổn, chụp ban ngày tốt, ban đêm hơi mờ",
    "Pin dùng được 1 ngày, không quá trâu cũng không kém",
    "Shop giao hàng đúng hạn, đóng gói cẩn thận",
    "Sản phẩm đúng như mô tả, không có gì để phàn nàn",
    "Tốt trong tầm giá, không đòi hỏi nhiều thì được",
]

negative_templates = [
    "Sản phẩm kém chất lượng, dùng 1 ngày đã lỗi",
    "Pin kém, tụt pin nhanh, phải sạc nhiều lần",
    "Màn hình xấu, màu nhợt, nhìn mỏi mắt",
    "Camera mờ, chụp không rõ, thất vọng",
    "Giá đắt hơn thị trường nhiều, không đáng",
    "Shop không uy tín, giao hàng chậm, đóng gói sơ sài",
    "Sản phẩm không chính hãng, nhái kém chất lượng",
    "Lag giật, chạy app nặng rất chậm, nóng máy",
    "Thiết kế xấu, cấu trúc kém, cầm không chắc tay",
    "Rất tệ, không nên mua, phí tiền",
]

# Template sentences cho aspect
aspect_templates = {
    "camera": [
        "Camera chụp rõ nét, màu sắc đẹp",
        "Camera selfie xấu, không tự nhiên",
        "Chụp đêm tốt, giữ được chi tiết",
        "Camera chậm, lỗi lúc focus",
        "Quay phim mượt, ổn định",
        "Camera bị mờ, không sắc nét",
        "Chụp xóa phông tự nhiên, background đẹp",
        "Camera trước kém, không đủ sáng",
        "Ảnh chụp đẹp, lưu nét",
        "Camera không ổn định, rung lắc",
    ],
    "pin": [
        "Pin trâu, dùng cả ngày không hết",
        "Pin kém, tụt nhanh, phải sạc nhiều lần",
        "Sạc nhanh tiện lợi, đầy pin nhanh",
        "Pin không đủ dùng, nhanh hết",
        "Thời lượng pin ổn, đủ dùng trong ngày",
        "Pin chai nhanh, dùng ít đã hết",
        "Sạc không dây tiện, nhưng hơi chậm",
        "Pin rất trâu, chơi game cả ngày",
        "Hết pin nhanh, phải mang sạc theo",
        "Pin ổn, không có vấn đề gì",
    ],
    "giá": [
        "Giá tốt, rẻ hơn các cửa hàng khác",
        "Giá đắt, không đáng tiền",
        "Giá hợp lý, phù hợp với chất lượng",
        "Giá cao hơn thị trường nhiều",
        "Sale khuyến mãi, giá rẻ",
        "Giá không đổi, ổn định",
        "Đáng tiền, chất lượng đúng giá",
        "Giá quá đắt so với tính năng",
        "Giá tốt trong phân khúc",
        "Khuyến mãi hấp dẫn, nên mua",
    ],
    "màn_hình": [
        "Màn hình đẹp, màu sắc chân thật",
        "Màn hình xấu, màu nhợt",
        "Màn hình OLED đẹp, độ sáng cao",
        "Màn hình bị burn-in, có vết cháy",
        "Tần số quét 120Hz mượt mà",
        "Màn hình bị đơ, không nhạy cảm ứng",
        "Độ phân giải cao, nét căng",
        "Màn hình to, xem phim đã",
        "Màn hình nhỏ, khó nhìn",
        "Màn hình ổn, không có vấn đề",
    ],
    "hiệu_năng": [
        "Mượt mà, chạy game rất ổn",
        "Lag giật, không chơi game nặng được",
        "Hiệu năng mạnh, xử lý nhanh",
        "Nóng máy khi chơi game lâu",
        "Đa nhiệm tốt, mở nhiều app không lag",
        "Hiệu năng kém, chậm chạp",
        "RAM lớn, chạy đa nhiệm tốt",
        "CPU mạnh, xử lý nhanh",
        "Chơi game nặng bị giật lag",
        "Hiệu năng ổn, đủ dùng hàng ngày",
    ],
    "thiết_kế": [
        "Thiết kế đẹp, sang trọng",
        "Thiết kế xấu, không đẹp",
        "Cầm chắc tay, nhôm kim loại đẹp",
        "Mỏng nhẹ, dễ cầm",
        "Màu sắc đẹp, nhiều lựa chọn",
        "Thiết kế lỗi thời, không bắt mắt",
        "Vỏ nhựa kém, dễ trầy xước",
        "Hoàn thiện tốt, không có lỗi",
        "Thiết kế đơn giản, bình thường",
        "Đẹp hơn mong đợi, rất ưng ý",
    ],
    "loa_âm_thanh": [
        "Loa lớn, nghe nhạc rất đã",
        "Loa nhỏ, âm thanh nhỏ",
        "Âm bass tốt, chắc khỏe",
        "Loa bị rè, nghe không rõ",
        "Âm thanh rõ ràng, chi tiết",
        "Loa yếu, không đủ lớn",
        "Nghe gọi rõ, không bị ngắt quãng",
        "Loa stereo hay, nghe nhạc đã",
        "Âm thanh bị méo, không tự nhiên",
        "Loa ổn, không có vấn đề gì",
    ],
    "bảo_mật": [
        "Vân tay nhạy, mở khóa nhanh",
        "Face ID chính xác, bảo mật tốt",
        "Mật khẩu dễ nhập, an toàn",
        "Vân tay không nhạy, thường bị lỗi",
        "Face ID không nhận diện đúng",
        "Bảo mật tốt, không lo mất dữ liệu",
        "Khóa màn hình tiện lợi",
        "Bảo mật kém, dễ bẻ khóa",
        "Nhận diện khuôn mặt chậm",
        "Mở khóa nhanh, tiện lợi",
    ],
    "hệ_điều_hành": [
        "iOS mượt mà, ổn định",
        "Android mượt, dễ sử dụng",
        "Hệ điều hành mới, nhiều tính năng",
        "Cập nhật thường xuyên, bảo mật tốt",
        "Giao diện đẹp, dễ dùng",
        "Hệ điều hành lỗi, bị crash",
        "Android cập nhật chậm",
        "iOS ổn định, không bị lỗi",
        "Giao diện phức tạp, khó dùng",
        "Hệ điều hành tốt, không có vấn đề",
    ],
    "khác": [
        "Sản phẩm đúng như mô tả",
        "Giao hàng nhanh, đóng gói cẩn thận",
        "Shop phục vụ tốt, tư vấn nhiệt tình",
        "Chất lượng ổn, không có gì để phàn nàn",
        "Mua lần thứ n, vẫn hài lòng",
        "Bảo hành tốt, hỗ trợ nhanh",
        "Không có gì đặc biệt, bình thường",
        "Tạm được, không tốt không xấu",
        "Chưa dùng lâu, chưa biết độ bền",
        "Sản phẩm ổn, dùng được",
    ],
}

def generate_sentiment_data():
    """Tạo dữ liệu sentiment đã cân bằng: 280 mỗi lớp = 840 tổng"""
    data = []
    labels = ['positive', 'neutral', 'negative']
    templates = [positive_templates, neutral_templates, negative_templates]
    
    for label, temps in zip(labels, templates):
        for i in range(280):
            text = random.choice(temps)
            # Thêm biến thể
            if random.random() > 0.5:
                text += f" - review {i}"
            data.append({"text": text, "label": label})
    
    random.shuffle(data)
    return data

def generate_aspect_data():
    """Tạo dữ liệu aspect với phân bố mất cân bằng thực tế"""
    data = []
    # Phân bố mất cân bằng dựa trên thống kê thực
    aspect_dist = {
        "camera": 159,
        "giá": 1142,
        "hiệu_năng": 479,
        "khác": 2736,
        "loa_âm_thanh": 201,
        "màn_hình": 183,
        "pin": 298,
        "thiết_kế": 540,
        "hệ_điều_hành": 20,
        "bảo_mật": 11,
    }
    
    for aspect, count in aspect_dist.items():
        temps = aspect_templates.get(aspect, aspect_templates["khác"])
        for i in range(count):
            text = random.choice(temps)
            if random.random() > 0.5:
                text += f" - {aspect} review {i}"
            data.append({"text": text, "label": aspect})
    
    random.shuffle(data)
    return data

def main():
    print("Đang tạo dữ liệu mẫu cho PhoBERT...")
    
    # Tạo sentiment data
    sentiment_data = generate_sentiment_data()
    sentiment_path = os.path.join(DATA_DIR, "..", "phobert_train_sentiment_datn_balanced.jsonl")
    sentiment_path = os.path.normpath(sentiment_path)
    with open(sentiment_path, 'w', encoding='utf-8') as f:
        for item in sentiment_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"✅ Đã tạo {len(sentiment_data)} mẫu sentiment: {sentiment_path}")
    
    # Tạo aspect data
    aspect_data = generate_aspect_data()
    aspect_path = os.path.join(DATA_DIR, "..", "phobert_train_aspect.jsonl")
    aspect_path = os.path.normpath(aspect_path)
    with open(aspect_path, 'w', encoding='utf-8') as f:
        for item in aspect_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"✅ Đã tạo {len(aspect_data)} mẫu aspect: {aspect_path}")
    
    # Thống kê
    print("\n[Thống kê Sentiment]")
    from collections import Counter
    sent_counts = Counter(d['label'] for d in sentiment_data)
    for label, count in sent_counts.items():
        print(f"  {label}: {count} ({count/len(sentiment_data)*100:.1f}%)")
    
    print("\n[Thống kê Aspect]")
    aspect_counts = Counter(d['label'] for d in aspect_data)
    for label, count in sorted(aspect_counts.items(), key=lambda x: -x[1]):
        print(f"  {label}: {count} ({count/len(aspect_data)*100:.1f}%)")
    
    print(f"\n💾 Dữ liệu đã lưu tại: {DATA_DIR}")

if __name__ == "__main__":
    main()
