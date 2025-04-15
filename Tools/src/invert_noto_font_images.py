import os
from PIL import Image

# Set the folder containing your Noto-style emoji PNGs
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "Assets")
PNG_DIR = os.path.join(PROJECT_ROOT, "PNGs")
NOTO_DIR = os.path.join(PROJECT_ROOT, "Noto Emoji Font")
INPUT_DIR = NOTO_DIR
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "Noto Emoji Font - Converted")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def convert_black_white_to_white_transparent(img):
    img = img.convert("RGBA")
    datas = img.getdata()
    new_data = []

    for pixel in datas:
        r, g, b, a = pixel

        # Detect white background
        if r > 250 and g > 250 and b > 250:
            new_data.append((255, 255, 255, 0))  # transparent
        else:
            new_data.append((255, 255, 255, 255))  # full white

    img.putdata(new_data)
    return img

for file in os.listdir(INPUT_DIR):
    if file.lower().endswith(".png"):
        img_path = os.path.join(INPUT_DIR, file)
        img = Image.open(img_path)
        converted = convert_black_white_to_white_transparent(img)
        converted.save(os.path.join(OUTPUT_DIR, file))

        print(f"Converted: {file}")
