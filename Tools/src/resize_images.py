import os
from PIL import Image

# Define directories
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IMAGE_DIR = os.path.join(PROJECT_ROOT, "Assets", "PNGs")  # Adjust as needed

# Define max dimensions
MAX_SIZE = (60, 60)

def resize_image(image_path):
    """Resizes an image to fit within 60x60 while maintaining aspect ratio."""
    with Image.open(image_path) as img:
        width, height = img.size

        # ✅ Skip resizing if already within 60x60
        if width <= 60 and height <= 60:
            print(f"✅ Skipping (already within limits): {image_path}")
            return

        # ✅ Resize while maintaining aspect ratio
        img.thumbnail(MAX_SIZE, Image.LANCZOS)

        # ✅ Overwrite the original file with the resized image
        img.save(image_path)
        print(f"🔄 Resized: {image_path} ({width}x{height} → {img.size[0]}x{img.size[1]})")

def resize_all_images():
    """Recursively finds and resizes all images in the PNGs directory."""
    for root, _, files in os.walk(IMAGE_DIR):
        for filename in files:
            if filename.endswith(".png"):
                image_path = os.path.join(root, filename)
                resize_image(image_path)

if __name__ == "__main__":
    resize_all_images()
