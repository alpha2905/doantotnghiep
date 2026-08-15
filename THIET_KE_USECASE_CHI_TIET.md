# 3.4. Mô Hình Xử Lý / Tương Tác

## 3.4.1. Đặc Tả Chi Tiết Use Case

---

### 3.4.1.1. Use Case Đăng Nhập

**Bảng 3-5: Bảng đặc tả use case đăng nhập**

| Thuộc tính | Mô tả |
|-----------|-------|
| **Tên use case** | Đăng nhập hệ thống |
| **Tác nhân chính** | Người dùng (Khách hàng) |
| **Mô tả tóm tắt** | Cho phép người dùng sử dụng tài khoản đã đăng ký để xác thực danh tính. Nếu thông tin chính xác, hệ thống sẽ cấp quyền truy cập (JWT Access Token) vào các chức năng tương ứng. |
| **Điều kiện tiên quyết** | - Người dùng đã có tài khoản trên hệ thống (đã đăng ký).<br>- Người dùng đang ở giao diện trang đăng nhập. |
| **Điều kiện thành công** | - Hệ thống tạo và trả về JWT Access Token (hết hạn 7 ngày).<br>- Người dùng được chuyển đến màn hình trang chủ, các chức năng yêu thích/thông báo được kích hoạt theo quyền. |

**Luồng sự kiện chính**

| Bước | Mô tả |
|------|-------|
| 1 | Người dùng nhập **Email** và **Mật khẩu** vào form đăng nhập. |
| 2 | Người dùng nhấn nút "Đăng nhập". |
| 3 | Hệ thống (Frontend) kiểm tra tính hợp lệ dữ liệu đầu vào (không được để trống, email đúng định dạng). |
| 4 | Hệ thống gửi yêu cầu `POST /api/auth/login` đến Backend (FastAPI). |
| 5 | Backend kiểm tra thông tin trong collection `users` (MongoDB):<br>- Tìm user theo email đã lowercase.<br>- Đối chiếu mật khẩu bằng bcrypt (`verify_password`). |
| 6 | Nếu thông tin đúng, hệ thống tạo JWT Access Token với payload `{"sub": user_id}`. |
| 7 | Hệ thống trả về `access_token`, `token_type`, và thông tin `user` (email, full_name, favorites). |
| 8 | Frontend lưu Token vào localStorage và điều hướng người dùng đến trang chủ. |

**Ngoại lệ**

| Mã | Mô tả |
|----|-------|
| **E1** | **Sai email hoặc mật khẩu**: Tại Bước 5, nếu không tìm thấy tài khoản hoặc mật khẩu không khớp → Hệ thống trả về lỗi HTTP 401 "Email hoặc mật khẩu không đúng" và yêu cầu người dùng nhập lại. |
| **E2** | **Dữ liệu đầu vào bị trống**: Tại Bước 3, nếu người dùng bỏ trống trường thông tin → Hệ thống hiển thị cảnh báo tại trường đó và không gửi request về Server. |
| **E3** | **Token hết hạn**: Khi token hết hạn (sau 7 ngày), hệ thống trả về lỗi "Token đã hết hạn, vui lòng đăng nhập lại" → Yêu cầu người dùng đăng nhập lại. |

---

### 3.4.1.2. Use Case Đăng Ký Tài Khoản

**Bảng 3-6: Bảng đặc tả use case đăng ký tài khoản**

| Thuộc tính | Mô tả |
|-----------|-------|
| **Tên use case** | Đăng ký tài khoản |
| **Tác nhân chính** | Khách hàng (Người dùng mới) |
| **Mô tả tóm tắt** | Cho phép người dùng tạo tài khoản mới bằng cách cung cấp email, mật khẩu và họ tên. Tài khoản được dùng để đăng nhập, lưu yêu thích và nhận thông báo giá. |
| **Điều kiện tiên quyết** | - Người dùng chưa đăng nhập và đang ở giao diện trang "Đăng ký". |
| **Điều kiện thành công** | Tài khoản mới được tạo trong collection `users` (MongoDB) với mật khẩu đã băm bcrypt. Người dùng được cấp JWT Token và có thể sử dụng ngay. |

**Luồng sự kiện chính**

| Bước | Mô tả |
|------|-------|
| 1 | Người dùng nhập thông tin vào biểu mẫu đăng ký: **Email** (bắt buộc), **Mật khẩu** (tối thiểu 6 ký tự), **Họ tên** (tùy chọn). |
| 2 | Người dùng nhấn nút "Đăng ký". |
| 3 | Hệ thống (Frontend) kiểm tra định dạng: Email đúng chuẩn, mật khẩu ≥ 6 ký tự, mật khẩu xác nhận khớp nhau. |
| 4 | Hệ thống gửi dữ liệu `POST /api/auth/register` về Backend (FastAPI). |
| 5 | Backend kiểm tra sự tồn tại của email trong collection `users` (đã lowercase). |
| 6 | Nếu hợp lệ, hệ thống thực hiện:<br>- Băm mật khẩu bằng bcrypt (`hash_password`).<br>- Tạo document mới trong `users` với `favorites: []`, `created_at`. |
| 7 | Hệ thống tạo JWT Token và thông báo "Đăng ký thành công", tự động đăng nhập người dùng. |

**Ngoại lệ**

| Mã | Mô tả |
|----|-------|
| **E1** | **Email đã tồn tại**: Tại Bước 5, nếu email đã có trong DB → Hệ thống trả lỗi HTTP 400 "Email đã được đăng ký", yêu cầu người dùng kiểm tra lại hoặc chuyển sang trang đăng nhập. |
| **E2** | **Mật khẩu quá ngắn**: Tại Bước 3, nếu mật khẩu < 6 ký tự → Hệ thống báo lỗi "Mật khẩu phải có ít nhất 6 ký tự". |
| **E3** | **Email không hợp lệ**: Tại Bước 3, nếu email thiếu "@" hoặc "." → Hệ thống báo lỗi "Email không hợp lệ". |

---

### 3.4.1.3. Use Case Tìm Kiếm Sản Phẩm

**Bảng 3-7: Bảng đặc tả use case tìm kiếm sản phẩm**

| Thuộc tính | Mô tả |
|-----------|-------|
| **Tên use case** | Tìm kiếm sản phẩm |
| **Tác nhân chính** | Người dùng (Khách hàng) |
| **Mô tả tóm tắt** | Người dùng nhập từ khóa tên sản phẩm (điện thoại) để tìm kiếm. Hệ thống truy vấn đồng thời trên 8 collection sàn TMĐT và trả về danh sách sản phẩm phù hợp kèm giá, hình ảnh, URL. Nếu không tìm thấy, hệ thống gợi ý sản phẩm cùng hãng. |
| **Điều kiện tiên quyết** | - Người dùng đang ở giao diện trang tìm kiếm.<br>- Đã có dữ liệu sản phẩm trong MongoDB. |
| **Điều kiện thành công** | - Hệ thống trả về danh sách sản phẩm tìm thấy trên các sàn.<br>- Nếu không có kết quả, hiển thị gợi ý sản phẩm tương tự để người dùng tiếp tục khám phá. |

**Luồng sự kiện chính**

| Bước | Mô tả |
|------|-------|
| 1 | Người dùng nhập từ khóa tìm kiếm (ví dụ: "iPhone 15") vào ô tìm kiếm. |
| 2 | Người dùng nhấn nút "Tìm kiếm" hoặc nhấn Enter. |
| 3 | Hệ thống gửi yêu cầu `GET /api/search?name=...` đến Backend. |
| 4 | Backend chuẩn hóa từ khóa bằng `clean_product_name()` (lowercase, bỏ dấu, chuẩn hóa viết tắt "ip"→"iphone"). |
| 5 | Backend sử dụng `asyncio.gather()` để truy vấn **đồng thời** trên tất cả 8 collection sàn (`fpt`, `tgdd`, `cellphones`, `hoangha`, `didongviet`, `viettelstore`, `clickbuy`, `mobilecity`). |
| 6 | Hệ thống lọc sản phẩm bằng regex trên trường `name` (không phân biệt hoa thường). |
| 7 | Hệ thống tổng hợp kết quả và trả về JSON: `{found, search_term, result_count, message}`. |
| 8 | Frontend hiển thị kết quả tìm kiếm cho người dùng. |

**Luồng sự kiện phụ (Search Fallback Engine)**

| Bước | Mô tả |
|------|-------|
| S1 | Tại Bước 7, nếu không tìm thấy sản phẩm nào, hệ thống kích hoạt **Search Fallback Engine**. |
| S2 | Hệ thống truy vấn sản phẩm mới nhất (sort theo `last_scraped_at` giảm dần) từ mỗi collection sàn. |
| S3 | Hệ thống trả về danh sách gợi ý (tối đa 10 sản phẩm) với `{platform, name, current_price, image, link}`. |
| S4 | Frontend hiển thị thông báo "Không tìm thấy sản phẩm..." kèm danh sách gợi ý. |

**Ngoại lệ**

| Mã | Mô tả |
|----|-------|
| **E1** | **Từ khóa để trống**: Tại Bước 2, nếu người dùng bấm tìm kiếm mà không nhập gì → Hệ thống báo lỗi "Vui lòng nhập từ khóa tìm kiếm". |
| **E2** | **Không có kết quả**: Tại Bước S1, nếu không có sản phẩm nào → Hệ thống hiển thị thông báo và gợi ý sản phẩm cùng hãng. |
| **E3** | **Lỗi kết nối DB**: Nếu MongoDB không phản hồi → Hệ thống trả lỗi và yêu cầu thử lại sau. |

---

### 3.4.1.4. Use Case So Sánh Giá Đa Nền Tảng

**Bảng 3-8: Bảng đặc tả use case so sánh giá đa nền tảng**

| Thuộc tính | Mô tả |
|-----------|-------|
| **Tên use case** | So sánh giá đa nền tảng |
| **Tác nhân chính** | Người dùng (Khách hàng) |
| **Mô tả tóm tắt** | Tổng hợp và so sánh giá của cùng một sản phẩm trên 8 sàn TMĐT. Hệ thống chọn sản phẩm rẻ nhất khớp model trên mỗi sàn, bù giá theo ngày (forward fill), hiển thị biểu đồ 7 ngày, dự báo giá LSTM, phân tích cảm xúc, PQS và khuyến nghị mua. |
| **Điều kiện tiên quyết** | - Người dùng tìm kiếm thành công một sản phẩm.<br>- Có dữ liệu sản phẩm trong MongoDB. |
| **Điều kiện thành công** | - Hiển thị bảng so sánh giá giữa 3 sàn rẻ nhất.<br>- Mỗi sàn kèm biểu đồ giá 7 ngày, dự báo, sentiment, PQS, khuyến nghị mua. |

**Luồng sự kiện chính**

| Bước | Mô tả |
|------|-------|
| 1 | Người dùng chọn một sản phẩm từ kết quả tìm kiếm và nhấn "So sánh giá". |
| 2 | Hệ thống gửi yêu cầu `GET /api/compare?name=...` đến Backend. |
| 3 | Backend chuẩn hóa từ khóa: `clean_product_name()` và `extract_model_base()` (loại bỏ dung lượng GB/TB và từ bổ trợ). |
| 4 | Backend truy vấn đồng thời trên 8 collection sàn để lấy ứng viên. |
| 5 | Hệ thống tính điểm khớp (`scored_candidates`) dựa trên độ khớp model_base và tên đầy đủ, chọn `best_model_base`. |
| 6 | Với mỗi sàn, hệ thống chọn **sản phẩm rẻ nhất** khớp model base. |
| 7 | Hệ thống xây dựng khung 7 ngày chuẩn (`master_date_list`), bù giá thiếu bằng giá ngày trước (Forward Fill). |
| 8 | Hệ thống gọi **LSTM Model** để dự báo giá tương lai cho từng sàn. |
| 9 | Hệ thống gọi `analyze_comments_ai()` để phân tích sentiment, tính PQS, price stats, trend, buy recommendation. |
| 10 | Hệ thống sắp xếp kết quả theo giá tăng dần và trả về **3 sàn rẻ nhất**. |
| 11 | Frontend hiển thị bảng so sánh với các tab: biểu đồ giá, sentiment, PQS, khuyến nghị cho từng sàn. |

**Ngoại lệ**

| Mã | Mô tả |
|----|-------|
| **E1** | **Không tìm thấy sản phẩm trên sàn nào**: Tại Bước 4, nếu không có ứng viên → Hệ thống trả `{results: []}` và hiển thị thông báo. |
| **E2** | **Dữ liệu giá không đủ 7 ngày**: Tại Bước 7, nếu sản phẩm thiếu lịch sử giá → Hệ thống dùng bù giá (lấy giá ngày gần nhất) thay vì báo lỗi. |
| **E3** | **LSTM model chưa tải**: Tại Bước 8, nếu model chưa sẵn sàng → Hệ thống dùng `forecast = current_price` (không dự báo) và vẫn trả kết quả. |

---

### 3.4.1.5. Use Case Xem Phân Tích Cảm Xúc

**Bảng 3-9: Bảng đặc tả use case xem phân tích cảm xúc**

| Thuộc tính | Mô tả |
|-----------|-------|
| **Tên use case** | Xem phân tích cảm xúc (Sentiment Analysis) |
| **Tác nhân chính** | Người dùng (Khách hàng) |
| **Mô tả tóm tắt** | Hiển thị kết quả phân tích cảm xúc của các bình luận khách hàng trên sản phẩm: tỷ lệ Positive/Neutral/Negative, các khía cạnh được nhắc đến (camera, pin, màn hình...) và điểm chất lượng đánh giá (RQS) từng bình luận. |
| **Điều kiện tiên quyết** | - Người dùng đang xem chi tiết so sánh một sản phẩm.<br>- Sản phẩm có bình luận được crawl từ các sàn. |
| **Điều kiện thành công** | - Hiển thị biểu đồ phân bố cảm xúc (phần trăm POSITIVE/NEUTRAL/NEGATIVE).<br>- Hiển thị từng bình luận kèm nhãn cảm xúc, khía cạnh và điểm RQS. |

**Luồng sự kiện chính**

| Bước | Mô tả |
|------|-------|
| 1 | Người dùng mở tab "Phân tích cảm xúc" trên trang so sánh sản phẩm. |
| 2 | Backend lấy danh sách `comments` từ document sản phẩm. |
| 3 | Nếu bình luận > 12, hệ thống lấy mẫu ngẫu nhiên tối đa 12 bình luận để đảm bảo tốc độ API. |
| 4 | For mỗi bình luận mẫu, hệ thống thực hiện: |
| 5 | - **Tokenize** bằng PhoBERT Tokenizer (max_length=128). |
| 6 | - Dự đoán **Sentiment** bằng Sentiment Model (3 labels) và **Aspect** bằng Aspect Model (10 labels). |
| 7 | - Áp dụng **Rule-based** ưu tiên cao: kiểm tra từ khóa negative/positive/hỏi để quyết định sentiment, từ điển keyword→aspect. |
| 8 | - Tính **RQS** (Review Quality Score) 0-5 dựa trên sentiment + độ dài bình luận. |
| 9 | Hệ thống tổng hợp phần trăm pos/neu/neg và danh sách kết quả từng bình luận. |
| 10 | Frontend hiển thị biểu đồ tròn phân bố cảm xúc và danh sách bình luận kèm nhãn, khía cạnh, RQS. |

**Ngoại lệ**

| Mã | Mô tả |
|----|-------|
| **E1** | **Không có bình luận**: Tại Bước 3, nếu sản phẩm không có bình luận → Hệ thống trả `{pos:0, neu:100, neg:0, list:[]}` và hiển thị "Chưa có bình luận". |
| **E2** | **Lỗi model PhoBERT**: Nếu model chưa tải hoặc lỗi → Hệ thống bỏ qua bình luận lỗi, hiển thị kết quả cho các bình luận còn lại. |

---

### 3.4.1.6. Use Case Xem Dự Báo Giá

**Bảng 3-10: Bảng đặc tả use case xem dự báo giá**

| Thuộc tính | Mô tả |
|-----------|-------|
| **Tên use case** | Xem dự báo giá (Price Forecast) |
| **Tác nhân chính** | Người dùng (Khách hàng) |
| **Mô tả tóm tắt** | Hiển thị mức giá dự báo trong tương lai cho sản phẩm dựa trên mô hình LSTM, kèm hướng biến động (Giảm mạnh/Giảm nhẹ/Ổn định/Tăng nhẹ/Tăng mạnh) và các độ đo độ chính xác (MAE, RMSE, MAPE, Direction Accuracy). |
| **Điều kiện tiên quyết** | - Người dùng đang xem chi tiết so sánh một sản phẩm.<br>- LSTM Model và Scaler đã được tải trên server. |
| **Điều kiện thành công** | - Hiển thị giá dự báo tương lai kèm hướng biến động.<br>- Hiển thị các chỉ số đánh giá độ tin cậy của mô hình. |

**Luồng sự kiện chính**

| Bước | Mô tả |
|------|-------|
| 1 | Người dùng mở tab "Dự báo giá" trên trang so sánh sản phẩm. |
| 2 | Backend lấy `price_history` (6-7 ngày) từ document sản phẩm. |
| 3 | Hệ thống chuyển lịch sử thành dict `{date: price}` và bù giá đầy đủ 7 ngày (forward fill). |
| 4 | Hệ thống đảm bảo chuỗi đủ dài LOOK_BACK=5 (padding nếu cần). |
| 5 | Hệ thống chuẩn hóa 5 giá gần nhất bằng `scaler.transform()`. |
| 6 | Hệ thống đưa vào LSTM Model: `model.predict(X_scaled.reshape(1,5,1))`. |
| 7 | Hệ thống khôi phục giá thực bằng `scaler.inverse_transform()`. |
| 8 | Hệ thống tính `get_price_trend()` để xác định hướng biến động. |
| 9 | Hệ thống tính `calculate_lstm_metrics()` — MAE, RMSE, MAPE, Direction Accuracy. |
| 10 | Frontend hiển thị giá dự báo, biểu đồ xu hướng và các chỉ số độ chính xác. |

**Ngoại lệ**

| Mã | Mô tả |
|----|-------|
| **E1** | **Ít hơn 3 điểm dữ liệu giá**: Hệ thống trả `lstm_metrics: null` và dự báo = giá hiện tại. |
| **E2** | **Model chưa tải**: Nếu `lstm_model` hoặc `scaler` là null → forecast = 0, hệ thống dùng `current_price` thay thế. |
| **E3** | **Lỗi dự đoán**: Nếu có exception khi predict → Hệ thống ghi log lỗi và dùng giá hiện tại làm dự báo. |

---

### 3.4.1.7. Use Case Xem Điểm Chất Lượng Sản Phẩm (PQS)

**Bảng 3-11: Bảng đặc tả use case xem điểm chất lượng sản phẩm**

| Thuộc tính | Mô tả |
|-----------|-------|
| **Tên use case** | Xem điểm chất lượng sản phẩm (PQS) |
| **Tác nhân chính** | Người dùng (Khách hàng) |
| **Mô tả tóm tắt** | Hiển thị điểm PQS (0-100) và nhãn chất lượng (🟢 Rất tốt / 🟡 Tốt / 🟠 Trung bình / 🔴 Kém) cho từng sản phẩm. PQS được tính từ 5 thành phần có trọng số: rating, sentiment, uy tín shop, số lượng bán, tỷ lệ tích cực. |
| **Điều kiện tiên quyết** | - Người dùng đang xem chi tiết so sánh một sản phẩm. |
| **Điều kiện thành công** | - Hiển thị điểm PQS và nhãn chất lượng.<br>- Giúp người dùng đánh giá nhanh chất lượng sản phẩm. |

**Luồng sự kiện chính**

| Bước | Mô tả |
|------|-------|
| 1 | Hệ thống lấy thông tin sản phẩm: `rating`, `shop_reputation` (mặc định 70), `sold`. |
| 2 | Hệ thống lấy `sentiment_data` (phần trăm pos/neu/neg từ phân tích cảm xúc). |
| 3 | Hệ thống tính 5 thành phần: |
| 4 | - **Rating score** = (rating/5) × 100, nếu không có rating thì mặc định 50. |
| 5 | - **Sentiment score** = % tích cực (pos). |
| 6 | - **Uy tín gian hàng** = shop_reputation (mặc định 70). |
| 7 | - **Số lượng bán** = min(100, sold/1000 × 100), nếu không có thì 50. |
| 8 | - **Tỷ lệ tích cực** = % pos. |
| 9 | Hệ thống tính PQS = (rating×25% + sentiment×30% + shop×15% + sold×15% + positive×15%). |
| 10 | Hệ thống xác định nhãn: ≥85→🟢 Rất tốt, ≥70→🟡 Tốt, ≥50→🟠 Trung bình, <50→🔴 Kém. |
| 11 | Frontend hiển thị điểm PQS kèm nhãn và giải thích các thành phần. |

**Ngoại lệ**

| Mã | Mô tả |
|----|-------|
| **E1** | **Thiếu dữ liệu rating/sold**: Hệ thống dùng giá trị mặc định (rating score 50, sold score 50) thay vì báo lỗi. |
| **E2** | **Không có bình luận**: sentiment_score = 0 (pos=0), PQS vẫn được tính dựa trên các thành phần còn lại. |

---

### 3.4.1.8. Use Case Nhận Khuyến Nghị Mua

**Bảng 3-12: Bảng đặc tả use case nhận khuyến nghị mua**

| Thuộc tính | Mô tả |
|-----------|-------|
| **Tên use case** | Nhận khuyến nghị mua (Buy Recommendation) |
| **Tác nhân chính** | Người dùng (Khách hàng) |
| **Mô tả tóm tắt** | Hệ thống gợi ý hành động mua (Không khuyến nghị / Nên mua ngay / Nên mua / Nên chờ / Cân nhắc) dựa trên kết hợp điểm PQS, thống kê giá và dự báo giá LSTM. |
| **Điều kiện tiên quyết** | - Người dùng đang xem chi tiết so sánh một sản phẩm.<br>- Đã có PQS, price stats, forecast. |
| **Điều kiện thành công** | - Hiển thị khuyến nghị mua với biểu tượng, màu sắc và lý do chi tiết. |

**Luồng sự kiện chính**

| Bước | Mô tả |
|------|-------|
| 1 | Hệ thống nhận các đầu vào từ các module khác: `pqs`, `price_stats`, `current_price`, `forecast_price`. |
| 2 | Hệ thống áp dụng logic quyết định theo thứ tự ưu tiên: |
| 3 | - Nếu PQS < 50 → **"Không khuyến nghị"** ⛔ (reason: "Chất lượng sản phẩm thấp"). |
| 4 | - Nếu giá hiện tại < 95% giá trung bình VÀ forecast tăng → **"Nên mua ngay"** ✅ (reason: giá thấp hơn TB, dự báo tăng). |
| 5 | - Nếu giá hiện tại < giá trung bình → **"Nên mua"** 🛒. |
| 6 | - Nếu forecast < giá hiện tại → **"Nên chờ"** ⏳ (reason: dự báo giá sẽ giảm X%). |
| 7 | - Ngược lại → **"Cân nhắc"** 🤔 (reason: giá cao hơn TB, có thể chờ giảm giá). |
| 8 | Frontend hiển thị khuyến nghị kèm lý do và biểu tượng màu sắc tương ứng. |

**Ngoại lệ**

| Mã | Mô tả |
|----|-------|
| **E1** | **Thiếu dữ liệu giá**: Nếu `price_stats` hoặc `current_price` là 0 → Hệ thống bỏ qua điều kiện so sánh giá, vẫn trả về khuyến nghị dựa trên PQS và forecast. |
| **E2** | **Không có forecast**: Nếu forecast bằng 0 → Hệ thống dùng `current_price` làm forecast và bỏ qua điều kiện "Nên chờ". |

---

### 3.4.1.9. Use Case Quản Lý Sản Phẩm Yêu Thích

**Bảng 3-13: Bảng đặc tả use case quản lý sản phẩm yêu thích**

| Thuộc tính | Mô tả |
|-----------|-------|
| **Tên use case** | Quản lý sản phẩm yêu thích |
| **Tác nhân chính** | Người dùng (Khách hàng đã đăng nhập) |
| **Mô tả tóm tắt** | Cho phép người dùng lưu sản phẩm vào danh sách yêu thích, xem danh sách đã lưu và xóa sản phẩm khỏi danh sách. Dữ liệu yêu thích được lưu trong collection `users` (mảng `favorites`). |
| **Điều kiện tiên quyết** | - Người dùng đã đăng nhập (có JWT Token hợp lệ). |
| **Điều kiện thành công** | - Sản phẩm được thêm/xóa vào danh sách yêu thích của người dùng.<br>- Danh sách yêu thích được lưu vĩnh viễn trong MongoDB. |

**Luồng sự kiện chính**

| Bước | Mô tả |
|------|-------|
| 1 | Người dùng nhấn nút "Yêu thích" (Heart icon) trên sản phẩm trong trang so sánh. |
| 2 | Frontend gửi yêu cầu `POST /api/favorites` với thông tin sản phẩm (platform, name, current_price, forecast, image, link, pqs). |
| 3 | Hệ thống xác thực token qua `get_current_user()` (Authorization Bearer header). |
| 4 | Backend kiểm tra trùng lặp: sản phẩm đã có trong `favorites` chưa (cùng name + platform). |
| 5 | Nếu chưa có, hệ thống `$push` sản phẩm vào mảng `favorites` của user (kèm `added_at`). |
| 6 | Frontend hiển thị thông báo "Đã thêm vào yêu thích" và cập nhật icon. |
| 7 | Người dùng truy cập trang "Yêu thích" → Hệ thống trả về danh sách qua `GET /api/favorites`. |
| 8 | Người dùng nhấn Xóa → Hệ thống `$pull` sản phẩm khỏi mảng (theo name + platform). |

**Ngoại lệ**

| Mã | Mô tả |
|----|-------|
| **E1** | **Chưa đăng nhập**: Tại Bước 2, nếu không có token → Hệ thống trả lỗi 401 "Chưa đăng nhập", yêu cầu đăng nhập trước. |
| **E2** | **Sản phẩm đã có trong yêu thích**: Tại Bước 4, nếu trùng → Hệ thống trả lỗi 400 "Sản phẩm đã có trong danh sách yêu thích". |
| **E3** | **Không tìm thấy sản phẩm khi xóa**: Nếu sản phẩm không tồn tại trong favorites → Hệ thống trả lỗi 404 "Không tìm thấy sản phẩm yêu thích". |

---

### 3.4.1.10. Use Case Xem Thông Báo Giá

**Bảng 3-14: Bảng đặc tả use case xem thông báo giá**

| Thuộc tính | Mô tả |
|-----------|-------|
| **Tên use case** | Xem thông báo giá (In-App Notification) |
| **Tác nhân chính** | Người dùng (Khách hàng đã đăng nhập) |
| **Mô tả tóm tắt** | Hệ thống theo dõi các sản phẩm yêu thích của người dùng và tạo thông báo khi có biến động: giá giảm, giá giảm sâu (≥10%), giá thấp hơn trung bình, dự báo tăng giá, PQS tăng, xuất hiện nhiều bình luận tiêu cực. |
| **Điều kiện tiên quyết** | - Người dùng đã đăng nhập.<br>- Người dùng có ít nhất 1 sản phẩm trong danh sách yêu thích. |
| **Điều kiện thành công** | - Hiển thị danh sách thông báo mới nhất.<br>- Đánh dấu thông báo đã đọc. |

**Luồng sự kiện chính**

| Bước | Mô tả |
|------|-------|
| 1 | Người dùng mở trang "Thông báo". |
| 2 | Hệ thống gửi yêu cầu `GET /api/notifications`. |
| 3 | Backend lấy danh sách `favorites` của user. |
| 4 | For mỗi sản phẩm yêu thích, hệ thống tìm sản phẩm mới nhất trong collection sàn tương ứng. |
| 5 | Hệ thống tính các chỉ số hiện tại: `current_price`, `current_pqs`, `price_stats`, `forecast`. |
| 6 | Hệ thống kiểm tra 6 loại thông báo: |
| 7 | - Giá giảm so với lúc thêm (price_drop 📉). |
| 8 | - Giá giảm sâu ≥10% (deep_drop 🚨). |
| 9 | - Giá thấp hơn trung bình ≥3% (below_avg 💯). |
| 10 | - Dự báo tăng ≥2% (forecast_up 📈). |
| 11 | - PQS tăng ≥5 điểm (pqs_up ⭐). |
| 12 | - ≥5 bình luận & tỷ lệ tiêu cực ≥40% (negative_comments 😞). |
| 13 | Hệ thống lưu thông báo mới vào collection `notifications` (upsert theo key). |
| 14 | Hệ thống gửi push notification qua Firebase (nếu user có fcm_tokens). |
| 15 | Frontend hiển thị danh sách thông báo, đánh dấu đã đọc khi người dùng click. |

**Ngoại lệ**

| Mã | Mô tả |
|----|-------|
| **E1** | **Không có sản phẩm yêu thích**: Hệ thống trả danh sách rỗng và hiển thị "Chưa có thông báo". |
| **E2** | **Lỗi Firebase push**: Nếu gửi push notification thất bại, hệ thống vẫn lưu thông báo in-app và tiếp tục hoạt động bình thường. |

---

### 3.4.1.11. Use Case Crawl Dữ Liệu (Hệ Thống)

**Bảng 3-15: Bảng đặc tả use case crawl dữ liệu**

| Thuộc tính | Mô tả |
|-----------|-------|
| **Tên use case** | Crawl dữ liệu (Crawl Data) |
| **Tác nhân chính** | System / Scheduler (APScheduler) |
| **Mô tả tóm tắt** | Hệ thống tự động thu thập dữ liệu sản phẩm, giá, bình luận từ 8 website TMĐT bằng Playwright + BeautifulSoup. Dữ liệu được chuẩn hóa (tên, giá) và lưu/upsert vào MongoDB theo collection từng sàn. |
| **Điều kiện tiên quyết** | - Hệ thống đang chạy.<br>- Scheduler được cấu hình (chu kỳ 4-6 giờ).<br>- Kết nối Internet và MongoDB hoạt động. |
| **Điều kiện thành công** | - Dữ liệu sản phẩm, giá, bình luận mới được cập nhật vào MongoDB.<br>- Sản phẩm trùng URL được cập nhật (upsert), sản phẩm mới được thêm.<br>- Lịch sử giá được ghi nhận hàng ngày trong `price_history`. |

**Luồng sự kiện chính**

| Bước | Mô tả |
|------|-------|
| 1 | Scheduler kích hoạt task crawl theo chu kỳ. |
| 2 | Crawler khởi chạy Playwright (headless browser). |
| 3 | Trình duyệt điều hướng đến trang danh mục sản phẩm của sàn TMĐT (ví dụ: FPT Shop). |
| 4 | Trình duyệt cuộn trang để kích hoạt lazy-load và tải toàn bộ danh sách sản phẩm. |
| 5 | Crawler trích xuất HTML và dùng BeautifulSoup phân tích: tên, giá, hình ảnh, URL, bình luận. |
| 6 | Hệ thống chuẩn hóa dữ liệu qua `normalize_product()`: |
| 7 | - `clean_product_name()`: lowercase, chuẩn hóa "ip"→"iphone", bỏ "điện thoại". |
| 8 | - `extract_model_base()`: loại bỏ dung lượng GB/TB và từ bổ trợ. |
| 9 | - `parse_price()`: chuyển chuỗi "29.990.000₫" thành số nguyên 29990000. |
| 10 | Hệ thống upsert vào MongoDB qua `upsert_product()`: |
| 11 | - Nếu sản phẩm có `url` trùng → cập nhật giá, thêm vào `price_history` nếu giá đổi. |
| 12 | - Nếu sản phẩm mới → insert document mới. |
| 13 | Hệ thống lặp lại Bước 2-12 cho các sàn còn lại (TGDĐ, CellphoneS, ...). |
| 14 | Hệ thống ghi log kết quả crawl và kết thúc task. |

**Ngoại lệ**

| Mã | Mô tả |
|----|-------|
| **E1** | **Website thay đổi cấu trúc**: Nếu Playwright không tìm thấy selector → Crawler ghi log lỗi và chuyển sang sàn tiếp theo, không dừng toàn bộ hệ thống. |
| **E2** | **Mất kết nối Internet**: Crawler thử lại (retry) và ghi log lỗi, task được chạy lại ở chu kỳ sau. |
| **E3** | **Anti-bot/Cloudflare**: Nếu bị chặn → Crawler tạm dừng sàn đó, tiếp tục các sàn khác, thử lại sau. |

---

### 3.4.1.12. Use Case Phân Tích Cảm Xúc Tự Động (Hệ Thống)

**Bảng 3-16: Bảng đặc tả use case phân tích cảm xúc tự động**

| Thuộc tính | Mô tả |
|-----------|-------|
| **Tên use case** | Phân tích cảm xúc tự động (Sentiment Analysis) |
| **Tác nhân chính** | System (AI Service) |
| **Mô tả tóm tắt** | Khi có bình luận mới được crawl, hệ thống chạy mô hình PhoBERT (kết hợp rule-based) để phân loại sentiment (positive/neutral/negative), trích xuất khía cạnh (10 loại) và tính điểm RQS cho từng bình luận. |
| **Điều kiện tiên quyết** | - Dữ liệu bình luận mới đã được crawl vào MongoDB.<br>- Sentiment Model và Aspect Model PhoBERT đã được tải trên server. |
| **Điều kiện thành công** | - Mỗi bình luận mới được gán nhãn sentiment, khía cạnh và điểm RQS.<br>- Kết quả được dùng để tính PQS và hiển thị phân tích cảm xúc. |

**Luồng sự kiện chính**

| Bước | Mô tả |
|------|-------|
| 1 | Hệ thống lấy danh sách bình luận từ document sản phẩm. |
| 2 | Nếu số lượng > 12, hệ thống lấy mẫu ngẫu nhiên 12 bình luận (đảm bảo tốc độ API). |
| 3 | For mỗi bình luận, hệ thống: |
| 4 | - Tiền xử lý: lowercase, loại bỏ dấu câu. |
| 5 | - Tokenize bằng PhoBERT Tokenizer (max_length=128, padding). |
| 6 | - Dự đoán sentiment index qua Sentiment Model (0=Positive, 1=Neutral, 2=Negative). |
| 7 | - Dự đoán aspect index qua Aspect Model (10 labels). |
| 8 | - Áp dụng rule-based ưu tiên cao: |
| 9 | - Câu hỏi (có không, bao nhiêu...) → NEUTRAL. |
| 10 | - Có từ negative mạnh (hỏng, lỗi, tệ, lag...) → NEGATIVE. |
| 11 | - Có từ positive (rất tốt, chất lượng, mượt...) → POSITIVE. |
| 12 | - Aspect khớp từ khóa (SẮP XẾP theo độ dài giảm dần để ưu tiên cụm từ) → gán aspect. |
| 13 | - Nếu không khớp rule aspect → dùng kết quả model PhoBERT. |
| 14 | Hệ thống tính RQS = min(5, sentiment_score + length_score). |
| 15 | Hệ thống tổng hợp % pos/neu/neg và trả về danh sách kết quả. |

**Ngoại lệ**

| Mã | Mô tả |
|----|-------|
| **E1** | **Không có bình luận**: Trả về mặc định `{pos:0, neu:100, neg:0, list:[]}`. |
| **E2** | **Lỗi model trên 1 bình luận**: Bỏ qua bình luận đó, tiếp tục xử lý các bình luận khác (try/except). |

---

### 3.4.1.13. Use Case Dự Báo Giá Tự Động (Hệ Thống)

**Bảng 3-17: Bảng đặc tả use case dự báo giá tự động**

| Thuộc tính | Mô tả |
|-----------|-------|
| **Tên use case** | Dự báo giá tự động (Price Forecasting) |
| **Tác nhân chính** | System (AI Service) |
| **Mô tả tóm tắt** | Hệ thống sử dụng mô hình LSTM tổng quát (đã huấn luyện trên toàn bộ dữ liệu MongoD） để dự báo giá tương lai cho sản phẩm dựa trên chuỗi lịch sử giá 5 ngày (LOOK_BACK=5). |
| **Điều kiện tiên quyết** | - LSTM Model (`general_lstm_best.keras`) và Scaler (`general_scaler.pkl`) đã được tải.<br>- Sản phẩm có lịch sử giá. |
| **Điều kiện thành công** | - Trả về giá dự báo tương lai và hướng biến động giá.<br>- Tính được các chỉ số đánh giá độ chính xác (MAE, RMSE, MAPE, Direction Accuracy). |

**Luồng sự kiện chính**

| Bước | Mô tả |
|------|-------|
| 1 | Hệ thống lấy `price_history` của sản phẩm. |
| 2 | Hệ thống extract giá trị số từ từng entry (hỗ trợ `price_value` hoặc `price` string). |
| 3 | Hệ thống gom giá theo ngày (`scraped_at` → `YYYY-MM-DD`), giữ giá cuối cùng trong ngày. |
| 4 | Hệ thống sắp xếp giá theo ngày tăng dần. |
| 5 | Hệ thống chuẩn hóa bằng `MinMaxScaler` (đã fit trên toàn bộ dữ liệu lúc train). |
| 6 | Hệ thống tạo chuỗi đầu vào 5 giá gần nhất (LOOK_BACK=5). |
| 7 | Hệ thống gọi `model.predict()` với input shape `(1, 5, 1)`. |
| 8 | Hệ thống inverse scale để khôi phục giá thực. |
| 9 | Hệ thống tính trend qua `get_price_trend()` (Giảm mạnh/Giảm nhẹ/Ổn định/Tăng nhẹ/Tăng mạnh). |
| 10 | Hệ thống tính `calculate_lstm_metrics()`: MAE, RMSE, MAPE, Direction Accuracy (naive baseline). |
| 11 | Hệ thống trả về `forecast_price` và các metrics. |

**Ngoại lệ**

| Mã | Mô tả |
|----|-------|
| **E1** | **Ít hơn LOOK_BACK điểm dữ liệu**: Hệ thống padding bằng giá đầu tiên để đủ 5 ngày. |
| **E2** | **Ít hơn 3 điểm dữ liệu**: Hệ thống trả `lstm_metrics: null`, forecast = current price. |
| **E3** | **Lỗi predict**: Ghi log lỗi và dùng `current_price` làm forecast dự phòng. |

---

### 3.4.1.14. Use Case Đăng Ký FCM Token / Nhận Push Notification

**Bảng 3-18: Bảng đặc tả use case đăng ký FCM token**

| Thuộc tính | Mô tả |
|-----------|-------|
| **Tên use case** | Đăng ký FCM Token / Nhận Push Notification |
| **Tác nhân chính** | Người dùng (Khách hàng đã đăng nhập) |
| **Mô tả tóm tắt** | Cho phép người dùng đăng ký thiết bị (FCM token) để nhận push notification qua Firebase Cloud Messaging khi có biến động giá của sản phẩm yêu thích. |
| **Điều kiện tiên quyết** | - Người dùng đã đăng nhập.<br>- Trình duyệt/ứng dụng tạo được FCM token từ Firebase. |
| **Điều kiện thành công** | - FCM token được lưu vào mảng `fcm_tokens` của user.<br>- Người dùng nhận được push notification khi có giá giảm/khuyến nghị. |

**Luồng sự kiện chính**

| Bước | Mô tả |
|------|-------|
| 1 | Ứng dụng khởi tạo Firebase và nhận FCM token từ thiết bị. |
| 2 | Frontend gửi `POST /api/fcm-token` với token. |
| 3 | Hệ thống xác thực người dùng qua JWT. |
| 4 | Hệ thống `$addToSet` token vào mảng `fcm_tokens` của user (tránh trùng lặp). |
| 5 | Khi có thông báo mới (giá giảm...), hệ thống gọi Firebase Admin để gửi push notification đến các token. |

**Ngoại lệ**

| Mã | Mô tả |
|----|-------|
| **E1** | **Token rỗng**: Hệ thống trả lỗi 400 "Thiếu FCM token". |
| **E2** | **Lỗi gửi push**: Hệ thống vẫn lưu thông báo in-app và bỏ qua lỗi push (không làm gián đoạn). |

---

### 3.4.1.15. Use Case Đánh Dấu Thông Báo Đã Đọc

**Bảng 3-19: Bảng đặc tả use case đánh dấu thông báo đã đọc**

| Thuộc tính | Mô tả |
|-----------|-------|
| **Tên use case** | Đánh dấu thông báo đã đọc |
| **Tác nhân chính** | Người dùng (Khách hàng đã đăng nhập) |
| **Mô tả tóm tắt** | Cho phép người dùng đánh dấu một hoặc tất cả thông báo là đã đọc để quản lý trạng thái theo dõi. |
| **Điều kiện tiên quyết** | - Người dùng đã đăng nhập.<br>- Có ít nhất 1 thông báo. |
| **Điều kiện thành công** | - Trường `read` của thông báo được cập nhật thành `true`. |

**Luồng sự kiện chính**

| Bước | Mô tả |
|------|-------|
| 1 | Người dùng mở trang thông báo. |
| 2 | Người dùng click vào một thông báo hoặc nút "Đánh dấu tất cả đã đọc". |
| 3 | Frontend gửi `POST /api/notifications/mark-read` với danh sách keys hoặc `{all: true}`. |
| 4 | Hệ thống cập nhật `read: true` cho các notification khớp (theo user_id + key). |
| 5 | Frontend cập nhật giao diện, bỏ badge chưa đọc. |

**Ngoại lệ**

| Mã | Mô tả |
|----|-------|
| **E1** | **Không có thông báo**: Hệ thống trả về `{ok: true}` mà không thực hiện cập nhật nào. |

---

## 3.4.2. Tổng Kết

| Mã | Use Case | Tác nhân | Phân Loại |
|----|----------|----------|-----------|
| **UC-A1** | Đăng nhập | Người dùng | Chức năng xác thực |
| **UC-A2** | Đăng ký tài khoản | Khách hàng | Chức năng xác thực |
| **UC1** | Tìm kiếm sản phẩm | Người dùng | Chức năng chính |
| **UC7** | So sánh giá đa nền tảng | Người dùng | Chức năng chính |
| **UC4** | Xem phân tích cảm xúc | Người dùng | Chức năng chính |
| **UC5** | Xem dự báo giá | Người dùng | Chức năng chính |
| **UC2** | Xem điểm chất lượng (PQS) | Người dùng | Chức năng chính |
| **UC6** | Nhận khuyến nghị mua | Người dùng | Chức năng chính |
| **UC-A3** | Quản lý yêu thích | Người dùng (đã đăng nhập) | Chức năng cá nhân |
| **UC-A4** | Xem thông báo giá | Người dùng (đã đăng nhập) | Chức năng cá nhân |
| **UC-A5** | Đăng ký FCM / Push notification | Người dùng (đã đăng nhập) | Chức năng cá nhân |
| **UC-A6** | Đánh dấu thông báo đã đọc | Người dùng (đã đăng nhập) | Chức năng cá nhân |
| **UC8** | Crawl dữ liệu | System / Scheduler | Chức năng hệ thống |
| **UC9** | Phân tích cảm xúc tự động | System | Chức năng hệ thống |
| **UC10** | Dự báo giá tự động | System | Chức năng hệ thống |