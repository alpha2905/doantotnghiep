import sys
import zlib
import base64
import urllib.request
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Bảng chữ cái PlantUML
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"

def encode_plantuml(text: str) -> str:
    """Encode PlantUML text theo định dạng đặc biệt (deflate + base64 custom)."""
    # Nén bằng zlib (deflate)
    compressed = zlib.compress(text.encode("utf-8"))
    # Bỏ 2 byte header zlib (0x78 0x9C)
    compressed = compressed[2:]
    # Base64 với bảng chữ cái tùy chỉnh
    result = []
    buffer = 0
    bits = 0
    for byte in compressed:
        buffer = (buffer << 8) | byte
        bits += 8
        while bits >= 6:
            bits -= 6
            result.append(ALPHABET[(buffer >> bits) & 0x3F])
    if bits > 0:
        result.append(ALPHABET[(buffer << (6 - bits)) & 0x3F])
    return "".join(result)

def render_puml(puml_path, out_path):
    """Render một file .puml thành PNG."""
    with open(puml_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    encoded = encode_plantuml(content)
    url = f"https://www.plantuml.com/plantuml/png/{encoded}"
    
    print(f"Đang tải hình từ: {url[:80]}...")
    
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
        with open(out_path, "wb") as f:
            f.write(data)
    
    print(f"✅ Đã lưu hình: {out_path} ({len(data)} bytes)")

def main():
    # Tạo thư mục images nếu chưa có
    img_dir = os.path.join("diagrams", "images")
    os.makedirs(img_dir, exist_ok=True)
    
    # Render data model
    render_puml(
        os.path.join("diagrams", "data_model.puml"),
        os.path.join(img_dir, "data_model.png")
    )
    
    # Render AI architecture
    render_puml(
        os.path.join("diagrams", "ai_architecture.puml"),
        os.path.join(img_dir, "ai_architecture.png")
    )

if __name__ == "__main__":
    main()