from PIL import Image, ImageDraw, ImageFont
import os

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

# Create a simple icon with letter "S" on colored background
def make_icon(path, size, bg_color, text="S"):
    img = Image.new("RGB", (size, size), bg_color)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", size // 2)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) / 2
    y = (size - text_h) / 2
    draw.text((x, y), text, fill="white", font=font)
    img.save(path, "PNG")

# Android adaptive icon (foreground)
make_icon(os.path.join(ASSETS_DIR, "adaptive-icon.png"), 1024, (99, 102, 241))

# iOS/Android icon
make_icon(os.path.join(ASSETS_DIR, "icon.png"), 1024, (99, 102, 241))

# Splash screen (width x height for modern phones)
splash = Image.new("RGB", (1284, 2778), (99, 102, 241))
draw = ImageDraw.Draw(splash)
try:
    font = ImageFont.truetype("arial.ttf", 200)
except Exception:
    font = ImageFont.load_default()
text = "Smart Shopping"
bbox = draw.textbbox((0, 0), text, font=font)
text_w = bbox[2] - bbox[0]
text_h = bbox[3] - bbox[1]
x = (1284 - text_w) / 2
y = (2778 - text_h) / 2
draw.text((x, y), text, fill="white", font=font)
splash.save(os.path.join(ASSETS_DIR, "splash-icon.png"), "PNG")

# Notification icon (small white on transparent)
notif = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
draw = ImageDraw.Draw(notif)
try:
    font = ImageFont.truetype("arial.ttf", 48)
except Exception:
    font = ImageFont.load_default()
bbox = draw.textbbox((0, 0), "S", font=font)
text_w = bbox[2] - bbox[0]
text_h = bbox[3] - bbox[1]
x = (96 - text_w) / 2
y = (96 - text_h) / 2
draw.text((x, y), "S", fill=(255, 255, 255, 255), font=font)
notif.save(os.path.join(ASSETS_DIR, "notification-icon.png"), "PNG")

print("Done")
