import os
import json
import logging
from PIL import Image, ImageDraw, ImageFont, ImageChops
from fontTools.ttLib import TTFont
import unicodedata
import math
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# Project directory structure
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "scr")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "Assets")

TEXTURE_SHEETS_DIR = os.path.join(ASSETS_DIR, "Texture Sheets")
FULL_TEXTURE_DIR = os.path.join(TEXTURE_SHEETS_DIR, "Full")
LITE_TEXTURE_DIR = os.path.join(TEXTURE_SHEETS_DIR, "Lite")

SPRITE_SHEETS_DIR = os.path.join(ASSETS_DIR, "Sprites")
FULL_SPRITE_DIR = os.path.join(SPRITE_SHEETS_DIR, "Full")
LITE_SPRITE_DIR = os.path.join(SPRITE_SHEETS_DIR, "Lite")

PNG_DIR = os.path.join(ASSETS_DIR, "PNGs")
FONTS_DIR = os.path.join(ASSETS_DIR, "Fonts")

# Texture sizes
TEXTURE_SIZES = [16, 24, 32]
PADDING = 1  # 1px padding on each side (total 2px margin)

# Ensure required directories exist
os.makedirs(FULL_TEXTURE_DIR, exist_ok=True)
os.makedirs(LITE_TEXTURE_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)

# Load emoji metadata
DB_FILE = os.path.join(PROJECT_ROOT, "db", "emoji.json")
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        emoji_metadata = json.load(f)
else:
    emoji_metadata = {}

def crop_images(images, keys, final_size=64):
    """Crops all images to the tightest bounding box and centers them in a square canvas."""
    if not images:
        return []

    # Step 1: Collect bounding boxes for all images
    bbox_data = []
    
    for image, key in zip(images, keys):
        # Extract alpha channel and threshold at 50% transparency
        alpha = image.split()[-1].point(lambda p: 255 if p > 127 else 0, "1")  # Convert to binary mask
        bbox = alpha.getbbox()  # Get bounding box from thresholded alpha

        if bbox:
            left, top, right, bottom = bbox
            width, height = right - left, bottom - top
            bbox_data.append((key, left, top, right, bottom, width, height))

    # Ensure we have valid bounding boxes
    if not bbox_data:
        log.debug("No valid bounding boxes found! Returning original images.")
        return images  # Return original images if no valid bounding boxes are found

    # Step 2: Remove the top 1% of largest emojis (outliers)
    widths = [entry[5] for entry in bbox_data]
    heights = [entry[6] for entry in bbox_data]

    width_threshold = np.percentile(widths, 95)  # Get the 99th percentile
    height_threshold = np.percentile(heights, 95)

    filtered_bboxes = [entry for entry in bbox_data if entry[5] <= width_threshold and entry[6] <= height_threshold]

    if not filtered_bboxes:
        log.debug("After removing outliers, no valid emojis remain! Using original bounding boxes.")
        filtered_bboxes = bbox_data  # Fallback to all data if filtering removed everything

    # Step 3: Find the optimal crop dimensions after filtering
    min_left = min(entry[1] for entry in filtered_bboxes)
    min_top = min(entry[2] for entry in filtered_bboxes)
    max_right = max(entry[3] for entry in filtered_bboxes)
    max_bottom = max(entry[4] for entry in filtered_bboxes)

    crop_width = max_right - min_left
    crop_height = max_bottom - min_top
    max_dim = max(crop_width, crop_height)  # Ensure a square canvas

    log.debug(f"Final bounding box (after outlier removal): {crop_width}x{crop_height}")

    cropped_images = []

    # Step 4: Crop and center images into the new bounding box
    for image in images:
        cropped = image.crop((min_left, min_top, max_right, max_bottom))

        # Create a new square canvas
        square_crop = Image.new("RGBA", (max_dim, max_dim), (0, 0, 0, 0))

        # Compute centering offsets
        offset_x = (max_dim - crop_width) // 2
        offset_y = (max_dim - crop_height) // 2

        # Paste the cropped emoji into the center of the square canvas
        square_crop.paste(cropped, (offset_x, offset_y), mask=cropped)  # Preserve transparency

        # Resize to the final ideal size
        final_image = square_crop.resize((final_size, final_size), Image.LANCZOS)
        cropped_images.append(final_image)

    return cropped_images

def get_square_layout(count):
    """Compute the best column-first layout (width, height) based on the number of items."""
    cols = math.ceil(math.sqrt(count))  # Favor width
    rows = math.ceil(count / cols)  # Calculate exact height based on columns
    return cols, rows

def filter_lite_emojis(images, keys):
    """Filters out emojis with ZWJ (Zero Width Joiner) for the Lite version."""
    filtered_images = []
    filtered_keys = []
    
    for img, key in zip(images, keys):
        normalized_key = unicodedata.normalize("NFC", key)  # Normalize Unicode composition
        if "\u200d" not in normalized_key and len(normalized_key) == 1 and ord(normalized_key) > 127:
            filtered_images.append(img)
            filtered_keys.append(key)
    
    return filtered_images, filtered_keys

# -- PNG Emojis  ----------------------------------------------------------------------------------------------------------

def get_png_categories():
    """Retrieve all emoji type folders inside PNGs directory."""
    return [name for name in os.listdir(PNG_DIR) if os.path.isdir(os.path.join(PNG_DIR, name))]

def get_png_images(category):
    """Retrieve all emoji images and create a key mapping."""
    category_path = os.path.join(PNG_DIR, category)
    filenames = sorted(
        [f for f in os.listdir(category_path) if f.endswith(".png")],
        key=lambda x: [int(part, 16) for part in x.replace(".png", "").split("-")]
    )
    
    images = []
    keys = []
    
    for filename in filenames:
        try:
            img_path = os.path.join(category_path, filename)
            img = Image.open(img_path).convert("RGBA")  # Ensure correct format
            images.append(img)
            
            key = "".join(chr(int(part, 16)) for part in filename.replace(".png", "").split("-"))
            keys.append(key)
        except Exception as e:
            log.debug(f"Failed to load image {filename}: {e}")

    images = crop_images(images, keys)
    return images, keys

# -- FONTS ----------------------------------------------------------------------------------------------------------

def get_font_names():
    """Retrieve all font names from the Fonts directory."""
    return [name for name in os.listdir(FONTS_DIR) if name.endswith(".ttf")]

def is_significant_glyph(image):
    """Check if the glyph has changed more than 5% of the pixels."""
    bbox = image.getbbox()
    if not bbox:
        return False  # Image is fully transparent
    total_pixels = image.width * image.height
    non_transparent_pixels = sum(1 for pixel in image.getdata() if pixel[3] > 0)
    return (non_transparent_pixels / total_pixels) > 0.001

def get_font_glyphs(font_path):
    """Retrieve all emoji glyphs from a font file, excluding unwanted Unicode ranges."""
    try:
        font = TTFont(font_path)
        glyphs = set()
        for table in font['cmap'].tables:
            for cp in table.cmap.keys():
                # Exclude ASCII (<= 127)
                if cp <= 127:
                    continue  
                # Exclude Extended Latin (128 - 591)
                if 128 <= cp <= 591:
                    continue  
                # Exclude Greek (880 - 1023)
                if 880 <= cp <= 1023:
                    continue  
                # Exclude Cyrillic (1024 - 1279)
                if 1024 <= cp <= 1279:
                    continue  
                # Exclude Hebrew (1424 - 1535)
                if 1424 <= cp <= 1535:
                    continue  

                glyphs.add(chr(cp))
        
        return sorted(glyphs)
    
    except Exception as e:
        log.error(f"Error reading font {font_path}: {e}")
        return []

def get_font_emojis(font_path):
    """Render all emoji glyphs from a font as images, ensuring appropriate scaling and centering."""
    upscale_factor = 4
    ideal_size = 64  # Target render resolution for best quality

    font = ImageFont.truetype(font_path, ideal_size * upscale_factor)

    # Step 1: Collect bounding box sizes for EMOJIS ONLY
    widths = []
    heights = []
    emoji_bboxes = {}

    for emoji_char in get_font_glyphs(font_path):
        if ord(emoji_char) < 0x1F300:  # Ignore non-emoji glyphs when sizing
            continue

        bbox = font.getbbox(emoji_char, anchor="mm")
        if bbox:
            width = bbox[2] - bbox[0]  # x_max - x_min
            height = bbox[3] - bbox[1]  # y_max - y_min
            widths.append(width)
            heights.append(height)
            emoji_bboxes[emoji_char] = (width, height)

    # Ensure valid emoji glyphs exist
    if not widths or not heights:
        log.debug(f"No valid emoji glyphs found for font {font_path}.")
        return [], []

    # Step 2: Remove the top 3% of outlier emoji sizes
    width_threshold = np.percentile(widths, 97)  # Get 97th percentile
    height_threshold = np.percentile(heights, 97)

    filtered_bboxes = {char: (w, h) for char, (w, h) in emoji_bboxes.items() if w <= width_threshold and h <= height_threshold}

    # Step 3: Set canvas size based on cleaned emoji data
    max_width = max(w for w, _ in filtered_bboxes.values()) if filtered_bboxes else max(widths)
    max_height = max(h for _, h in filtered_bboxes.values()) if filtered_bboxes else max(heights)
    canvas_size = max(max_width, max_height)

    images = []
    keys = []

    for emoji_char in get_font_glyphs(font_path):  # Retrieve ALL glyphs
        temp_canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_canvas)

        # Automatically center the text
        temp_draw.text((canvas_size // 2 + 1, canvas_size // 2), emoji_char, font=font, fill=(255, 255, 255, 255), anchor="mm")
        temp_draw.text((canvas_size // 2 - 1, canvas_size // 2), emoji_char, font=font, fill=(255, 255, 255, 255), anchor="mm")
        temp_draw.text((canvas_size // 2, canvas_size // 2 + 1), emoji_char, font=font, fill=(255, 255, 255, 255), anchor="mm")
        temp_draw.text((canvas_size // 2, canvas_size // 2 - 1), emoji_char, font=font, fill=(255, 255, 255, 255), anchor="mm")

        # Check if the glyph is significant and resize
        if is_significant_glyph(temp_canvas):
            images.append(temp_canvas)
            keys.append(emoji_char)
        else:
            log.debug(f"Skipping non-significant glyph: {emoji_char} ({emoji_char.encode('unicode_escape').decode()})")

    images = crop_images(images, keys)
    return images, keys  # Return high-res images and their Unicode keys

# -- Texture Sheet  ----------------------------------------------------------------------------------------------------------

def generate_texture_sheet(category, images, keys, size, lite=False):
    """Generate a texture sheet with mapped keys and spacing."""
    base_dir = LITE_TEXTURE_DIR if lite else FULL_TEXTURE_DIR
    category_folder = os.path.join(base_dir, category)
    os.makedirs(category_folder, exist_ok=True)
    output_texture_path = os.path.join(category_folder, f"{category}_{"Lite" if lite else "Full"}_{size}.png")
    metadata_path = os.path.join(category_folder, "metadata.json")

    if os.path.exists(output_texture_path):
        log.debug(f"Skipping {output_texture_path}, already exists.")
        return {}

    # If lite, filter only single characters (that do not contain multi-codepoints)
    if lite:
        filtered_images, filtered_keys = filter_lite_emojis(images, keys)
    else:
        filtered_images, filtered_keys = images, keys  # Keep all for full version

    # Compute square-like dimensions (including space character at index 0)
    total_count = len(filtered_images) + 1  # +1 for space char
    cols, rows = get_square_layout(total_count)

    # Final sheet dimensions with padding included
    sheet_width = cols * (size + (PADDING * 2))
    sheet_height = rows * (size + (PADDING * 2))
    composite_sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))

    metadata = {" ": 0}  # Ensure the space character is explicitly mapped to index 0

    for index, (image, key) in enumerate(zip(filtered_images, filtered_keys), start=1):  # Start at 1 (skip index 0)
        if image is None:
            continue  # Skip empty images

        # Resize without shrinking (keep exact size)
        resized_img = image.resize((size, size), Image.LANCZOS)

        # Compute position with padding
        col = index % cols
        row = index // cols
        x_pos = col * (size + PADDING * 2) + PADDING
        y_pos = row * (size + PADDING * 2) + PADDING

        # Paste the resized glyph directly onto the composite sheet
        composite_sheet.paste(resized_img, (x_pos, y_pos))

        metadata[key] = index

    # Save sheet and metadata
    composite_sheet.save(output_texture_path)
    log.debug(f"Saved {output_texture_path} ({'Lite' if lite else 'Full'})")

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
    log.debug(f"Saved metadata: {metadata_path}")

    return metadata

# -- Sprite Strips  ----------------------------------------------------------------------------------------------------------

def generate_sprite_strip(category, images, keys, size, lite=False):
    """Generate a single-row sprite strip."""
    base_dir = LITE_SPRITE_DIR if lite else FULL_SPRITE_DIR
    category_folder = os.path.join(base_dir, category)
    os.makedirs(category_folder, exist_ok=True)
    output_sprite_path = os.path.join(category_folder, f"{category}_{'Lite' if lite else 'Full'}_{size}.png")
    metadata_path = os.path.join(category_folder, "metadata.json")

    if os.path.exists(output_sprite_path):
        log.debug(f"Skipping {output_sprite_path}, already exists.")
        return {}

    # If lite, filter only single characters (that do not contain multi-codepoints)
    if lite:
        filtered_images, filtered_keys = filter_lite_emojis(images, keys)
    else:
        filtered_images, filtered_keys = images, keys  # Keep all for full version

    if not filtered_images:
        log.debug(f"No valid images for category {category}. Skipping sprite strip.")
        return {}
    
    # Compute square-like dimensions (including space character at index 0)
    total_count = len(filtered_images) + 1  # +1 for space char
    cols, rows = get_square_layout(total_count)
    
    # Final sheet dimensions with padding included
    sheet_width = cols * (size + (PADDING * 2))
    sheet_height = rows * (size + (PADDING * 2))
    composite_sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))

    metadata = {}

    for index, (image, key) in enumerate(zip(filtered_images, filtered_keys)):
        if image is None:
            continue  # Skip empty images

        # Resize without shrinking (keep exact size)
        resized_img = image.resize((size, size), Image.LANCZOS)

        # Compute position with padding
        col = index % cols
        row = index // cols
        x_pos = col * (size + PADDING * 2) + PADDING
        y_pos = row * (size + PADDING * 2) + PADDING

        # Paste the resized glyph directly onto the composite sheet
        composite_sheet.paste(resized_img, (x_pos, y_pos))

        metadata[key] = index
    
    composite_sheet.save(output_sprite_path)
    log.debug(f"Saved sprite strip {output_sprite_path}")

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
    log.debug(f"Saved metadata: {metadata_path}")
    
    # Save blank text file with dimensions as filename
    blank_filename = os.path.join(category_folder, f"{cols}x{rows}_{total_count}.txt")
    with open(blank_filename, "w") as f:
        pass  # Just create an empty file
    log.debug(f"Saved blank file {blank_filename}")

    return metadata

# -- Sprite Strips  ----------------------------------------------------------------------------------------------------------

def generate_all_textures():
    """Generate texture sheets for all categories and fonts."""
    for category in os.listdir(PNG_DIR):
        category_path = os.path.join(PNG_DIR, category)
        if not os.path.isdir(category_path):
            continue

        # Check if all texture sheets exist before processing
        texture_check = all(
            os.path.exists(os.path.join(TEXTURE_SHEETS_DIR, tag, category, f"{category}_{tag}_{size}.png"))
            for tag in ["Full", "Lite"] for size in TEXTURE_SIZES
        )

        sprite_check = all(
            os.path.exists(os.path.join(SPRITE_SHEETS_DIR, category, f"{category}_{size}.png"))
            for size in TEXTURE_SIZES
        )

        if texture_check and sprite_check:
            log.debug(f"Skipping {category} - All texture and sprite sheets already exist.")
            continue

        images, keys = get_png_images(category)
        image_count = len(images)  # Track count per category

        for size in TEXTURE_SIZES:
            generate_texture_sheet(category, images, keys, size, lite=False)
            generate_texture_sheet(category, images, keys, size, lite=True)
            generate_sprite_strip(category, images, keys, size, lite=False)
            generate_sprite_strip(category, images, keys, size, lite=True)
            
        log.info(f"✅ Processed {image_count} images for category '{category}'.")

    for font_name in os.listdir(FONTS_DIR):
        if not font_name.endswith(".ttf"):
            continue

        category = f"Font_{os.path.splitext(font_name)[0]}"
        
        # Check if all font texture sheets exist before processing
        if all(os.path.exists(os.path.join(TEXTURE_SHEETS_DIR, tag, category, f"{category}_{size}.png"))
               for tag in ["Full", "Lite"] for size in TEXTURE_SIZES):
            log.debug(f"Skipping {category} - All texture sheets already exist.")
            continue

        font_path = os.path.join(FONTS_DIR, font_name)
        images, keys = get_font_emojis(font_path)
        mage_count = len(images)  # Track count per category
        for size in TEXTURE_SIZES:
            generate_texture_sheet(category, images, keys, size, lite=False)
            generate_texture_sheet(category, images, keys, size, lite=True)
            generate_sprite_strip(category, images, keys, size, lite=False)
            generate_sprite_strip(category, images, keys, size, lite=True)
        
        log.info(f"✅ Processed {image_count} images for category '{category}'.")
    
    log.info("🎉 Texture generation complete!")


if __name__ == "__main__":
    generate_all_textures()