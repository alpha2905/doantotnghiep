# 📐 Hướng Dẫn Vẽ Sơ Đồ Ngữ Cảnh Bằng Draw.io

## 🚀 **Cách 1: Mở File .drawio (Dễ Nhất)**

### Bước 1: Mở Draw.io
```bash
# Online (không cần cài):
https://app.diagrams.net/

# Hoặc cài Desktop app:
https://github.com/jgraph/drawio-desktop/releases
```

### Bước 2: Mở file
```bash
# Trên Draw.io website:
File → Open → Chọn file "context_diagram.drawio"

# Hoặc kéo thả file vào draw.io
```

### Bước 3: Edit & Save
```bash
# Sau khi chỉnh sửa:
File → Save (hoặc Ctrl+S)
```

---

## 📝 **Cách 2: Tạo Sơ Đồ Từ Đầu**

### **Các Bước Chi Tiết:**

#### 1️⃣ **Vẽ Box Người Dùng**
```
Chọn: Insert → Shape → Rounded Rectangle
- Màu: #FFB84D (Cam)
- Text: "👤 Người Dùng (User)"
- Vị trí: Top-left (x=50, y=100)
```

#### 2️⃣ **Vẽ Box Frontend**
```
Chọn: Insert → Shape → Rounded Rectangle
- Màu: #4A90E2 (Xanh)
- Text: "🌐 Frontend (React + Vite)"
- Vị trí: x=350, y=80
- Size: 160x120
```

#### 3️⃣ **Vẽ Box Backend**
```
Chọn: Insert → Shape → Rounded Rectangle
- Màu: #7B68EE (Tím)
- Text: "🔧 Backend API (FastAPI)"
- Vị trí: x=650, y=80
- Size: 160x120
```

#### 4️⃣ **Vẽ MongoDB (Elip)**
```
Chọn: Insert → Shape → Ellipse
- Màu: #50C878 (Xanh lá)
- Text: "🗄️ MongoDB"
- Vị trí: x=900, y=100
```

#### 5️⃣ **Vẽ AI/ML Box**
```
Chọn: Insert → Shape → Rounded Rectangle
- Màu: #FF6B6B (Đỏ)
- Text: "🤖 AI/ML Engine"
- Vị trí: x=650, y=280
- Size: 160x120
```

#### 6️⃣ **Vẽ Firebase**
```
Chọn: Insert → Shape → Rounded Rectangle
- Màu: #FFA500 (Cam sáng)
- Text: "🔐 Firebase"
- Vị trí: x=350, y=280
```

#### 7️⃣ **Vẽ 8 Scrapers (Nhỏ)**
```
Chọn: Insert → Shape → Rounded Rectangle
- Màu: #E8E8E8 (Xám nhạt)
- Text: "🕷️ TGDD", "🕷️ FPT Shop", etc.
- Size: 90x60
- Vị trí: Sắp xếp theo lưới 2 cột
  
Các scrapers:
1. 🕷️ TGDD (x=50, y=280)
2. 🕷️ FPT Shop (x=50, y=360)
3. 🕷️ Cellphones (x=160, y=280)
4. 🕷️ Hoàng Hà (x=160, y=360)
5. 🕷️ DidongViet (x=50, y=440)
6. 🕷️ ViettelStore (x=160, y=440)
7. 🕷️ ClickBuy (x=50, y=520)
8. 🕷️ MobileCity (x=160, y=520)
```

---

## 🔗 **Vẽ Các Đường Nối (Arrows)**

### **Cách Vẽ Arrow:**
```
1. Chọn 2 box (Shift + Click)
2. Insert → Connection → Straight / Curved / Orthogonal
3. Hoặc kéo từ điểm kết nối của box này sang box khác
```

### **Các Arrow Chính:**

| Từ | Đến | Label |
|----|----|-------|
| User | Frontend | "Search, View, Compare" |
| Frontend | Backend | "HTTP/WebSocket REST API" |
| Backend | MongoDB | "CRUD Operations" |
| Backend | AI/ML | "Raw Data, Predictions" |
| Backend | Firebase | "Verify Login, JWT Token" |
| Backend | All Scrapers | "Trigger/Manage" |
| All Scrapers | Backend | "Extract Data" |

---

## 🎨 **Mẹo Trang Trí**

### **Màu Sắc Recommended:**
```css
/* Thành phần chính */
Frontend:    #4A90E2 (Xanh)
Backend:     #7B68EE (Tím)
Database:    #50C878 (Xanh lá)
AI/ML:       #FF6B6B (Đỏ)
User:        #FFB84D (Cam)
Firebase:    #FFA500 (Cam sáng)
Scrapers:    #E8E8E8 (Xám)
```

### **Font & Style:**
```
- Font size: 11pt cho main boxes, 10pt cho scrapers
- Font: Segoe UI hoặc Arial
- Bold: Title chính
- Stroke width: 2px cho main boxes, 1px cho scrapers
```

### **Layout:**
```
Top Layer:     User → Frontend → Backend → Database
Middle Layer:  Firebase ← Backend → AI/ML
Bottom Layer:  8 Scrapers ← Backend
```

---

## 💾 **Export Sơ Đồ**

### **Export PNG/SVG:**
```
File → Export as → PNG (hoặc SVG, PDF, JPG)
```

### **Export PDF:**
```
File → Export as → PDF
- Full page hoặc Selection
```

### **Chia Sẻ Online:**
```
File → Publish → Lấy link
- Chia sẻ link công khai
```

---

## 🔄 **Workflow Nhanh (Copy-Paste)**

Nếu bạn muốn tạo nhanh, hãy:

1. **Mở file drawio đã có:**
```bash
https://app.diagrams.net/
File → Open → Chọn context_diagram.drawio
```

2. **Edit các text/màu:**
   - Double-click vào box → Edit text
   - Right-click → Edit style → Đổi màu

3. **Thêm box mới:**
   - Ctrl+D để duplicate box
   - Hoặc Insert → Shape → ...

4. **Thêm arrow:**
   - Click trái + Shift, kéo sang box khác
   - Hoặc Edit → Connect

5. **Save:**
   - Ctrl+S hoặc File → Save

---

## 📋 **Lệnh Terminal (Nếu Dùng CLI)**

### **Convert Mermaid → DrawIO (Dùng Mermaid CLI):**
```bash
# Cài mermaid-cli
npm install -g @mermaid-js/mermaid-cli

# Export SVG từ markdown
mmdc -i CONTEXT_DIAGRAM.md -o diagram.svg

# Mở SVG trong draw.io
File → Import from → SVG file
```

### **Convert DrawIO → Image:**
```bash
# Cài drawio CLI
npm install -g drawio

# Export PNG
drawio -x context_diagram.drawio -o context_diagram.png --width 1200

# Export PDF
drawio -x context_diagram.drawio -o context_diagram.pdf
```

---

## 🎯 **Quick Links**

| Link | Mô Tả |
|------|-------|
| https://app.diagrams.net/ | Draw.io Online (Free) |
| https://github.com/jgraph/drawio-desktop | Desktop App |
| https://www.diagrams.net/doc | Documentation |
| https://mermaid.live/ | Mermaid Live (Alternative) |

---

## ✅ **Checklist Khi Vẽ Xong**

- ✅ 1 box Người Dùng (Cam)
- ✅ 1 box Frontend (Xanh)
- ✅ 1 box Backend (Tím)
- ✅ 1 box Database (Xanh lá)
- ✅ 1 box AI/ML (Đỏ)
- ✅ 1 box Firebase (Cam sáng)
- ✅ 8 box Scrapers (Xám)
- ✅ Tất cả arrow nối với label
- ✅ Màu sắc consistent
- ✅ Layout sạch sẽ & dễ đọc

---

## 🎓 **Ví Dụ Layout ASCII:**

```
┌─────────────┐
│   User 👤   │
└──────┬──────┘
       │ Search
       ↓
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ Frontend 🌐  │      │  Firebase 🔐 │      │  AI/ML 🤖    │
│  React+Vite  │──→   │  Auth        │  ←───│  PhoBERT     │
└──────┬───────┘      └──────────────┘      │  LSTM        │
       │ HTTP                                └──────────────┘
       ↓                                            ↑
┌──────────────────────────────────────────────────┘
│         Backend 🔧 (FastAPI)
├──────────────────────────────────────────────────┐
│                                                  ↓
│                                          ┌────────────────┐
│                                          │ MongoDB 🗄️     │
│                                          │ Products, Price│
└──────────────┬───────────────────────────┴────────────────┘
               │
    ┌──────────┴──────────┐
    ↓          ↓          ↓
  Scrapers (8 sàn):
  ┌─────┬──────┬─────┬──────┐
  │TGDD │  FPT │Cell │Hoàng │ ...
  └─────┴──────┴─────┴──────┘
```

---

**Tạo bởi:** GitHub Copilot  
**Ngôn ngữ:** Tiếng Việt  
**Ngày:** 2026-08-13
