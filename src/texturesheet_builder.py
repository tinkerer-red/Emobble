import os
import json
import logging
from PIL import Image, ImageDraw, ImageFont, ImageChops
from fontTools.ttLib import TTFont
import unicodedata
import math
import numpy as np
import re
import itertools

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# Project directory structure
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(PROJECT_ROOT, "scr")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "Assets")

SPRITE_SHEETS_DIR = os.path.join(ASSETS_DIR, "Sprites")
DELUXE_SPRITE_DIR = os.path.join(SPRITE_SHEETS_DIR, "Deluxe")
FULL_SPRITE_DIR = os.path.join(SPRITE_SHEETS_DIR, "Full")
LITE_SPRITE_DIR = os.path.join(SPRITE_SHEETS_DIR, "Lite")

FONT_SHEETS_DIR = os.path.join(ASSETS_DIR, "GMFonts")
DELUXE_FONT_DIR = os.path.join(FONT_SHEETS_DIR, "Deluxe")
FULL_FONT_DIR = os.path.join(FONT_SHEETS_DIR, "Full")
LITE_FONT_DIR = os.path.join(FONT_SHEETS_DIR, "Lite")

PNG_DIR = os.path.join(ASSETS_DIR, "PNGs")
FONTS_DIR = os.path.join(ASSETS_DIR, "Fonts")

# Texture sizes
TEXTURE_SIZES = [16, 24, 32]
MODES = ["deluxe", "full", "lite"]
PADDING = 1  # 1px padding on each side (total 2px margin)

FONT_OFFSET_KEY = 33 # Which codepoint to start counting for font texture sheet generation
FONT_INLUDE_SPACE = False

# Ensure required directories exist
os.makedirs(FONTS_DIR, exist_ok=True)

# Load emoji metadata
DB_FILE = os.path.join(PROJECT_ROOT, "db", "emoji.json")
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        emoji_metadata = json.load(f)
else:
    emoji_metadata = {}

#region -- Helper Functions ----------------------------------------------------------------------------------------

def get_grid_layout(count):
    """Compute the best column-first layout (width, height) based on the number of items."""
    cols = math.ceil(math.sqrt(count))  # Favor width
    rows = math.ceil(count / cols)  # Calculate exact height based on columns
    return cols, rows

def filter_sprite_inputs(images, keys, mode):
    """
    Filter image/key pairs based on sprite tier:
    - 'delux': all emojis
    - 'full': exclude emojis with both skin tones and other codepoints
    - 'lite': exclude emojis with skin tones or ZWJ
    """
    SKINTONE_RANGE = range(0x1F3FB, 0x1F400)  # U+1F3FB to U+1F3FF

    filtered_images = []
    filtered_keys = []

    for img, key in zip(images, keys):
        normalized = unicodedata.normalize("NFC", key)
        codepoints = [ord(c) for c in normalized]

        has_zwj = "\u200d" in normalized
        has_skintone = any(cp in SKINTONE_RANGE for cp in codepoints)

        if mode == "lite":
            if has_zwj or (has_skintone and len(codepoints) > 1):
                continue

        elif mode == "full":
            if has_skintone and len(codepoints) > 1:
                continue

        filtered_images.append(img)
        filtered_keys.append(key)

    return filtered_images, filtered_keys

def sort_emojis_by_key(images, keys):
    """Sort images and keys prioritizing Lite → Full → Delux tier order, then by Unicode."""
    SKINTONE_RANGE = range(0x1F3FB, 0x1F400)

    def tier_weight(key):
        normalized = unicodedata.normalize("NFC", key)
        codepoints = [ord(c) for c in normalized]

        has_zwj = "\u200d" in normalized
        has_skintone = any(cp in SKINTONE_RANGE for cp in codepoints)

        if not has_zwj and not has_skintone:
            return 0  # Lite
        elif has_skintone and len(codepoints) == 1:
            return 0  # Also Lite (standalone swatch)
        elif not has_zwj:
            return 1  # Full
        else:
            return 2  # Delux

    combined = sorted(
        zip(keys, images),
        key=lambda x: (tier_weight(x[0]), [ord(c) for c in x[0]])
    )

    sorted_keys, sorted_images = zip(*combined) if combined else ([], [])
    return list(sorted_images), list(sorted_keys)

def to_camel_case(name):
    """Convert category name to camelCase with only alphanumeric characters."""
    # Remove anything not a-zA-Z0-9 or space
    clean = re.sub(r"[^a-zA-Z0-9 ]+", "", name)
    parts = clean.strip().split()

    if not parts:
        return ""

    return parts[0].lower() + ''.join(p.capitalize() for p in parts[1:])

def all_output_files_exist(base_dir, category, modes, sizes):
    category_slug = to_camel_case(category)
    all_exist = True
    for mode in modes:
        for size in sizes:
            path = os.path.join(
                base_dir,
                mode.capitalize(),
                category,
                f"__emj_{category_slug}_{mode}_{size}.png"
            )
            exists = os.path.exists(path)
            #print(f"[{'✔' if exists else '✘'}] {path}")
            if not exists:
                all_exist = False
    return all_exist

#endregion

#region -- Crop Images ------------------------------------------------------------------------------

def calculate_cropping_bounds(images, keys, outlier_percentile=95):
    """Determine the tightest bounding box across images after removing outliers."""
    bbox_data = []

    for image, key in zip(images, keys):
        alpha = image.split()[-1].point(lambda p: 255 if p > 127 else 0, "1")
        bbox = alpha.getbbox()

        if bbox:
            left, top, right, bottom = bbox
            width, height = right - left, bottom - top
            bbox_data.append((left, top, right, bottom, width, height))

    if not bbox_data:
        log.debug("No bounding boxes found.")
        return None

    widths = [entry[4] for entry in bbox_data]
    heights = [entry[5] for entry in bbox_data]

    width_thresh = np.percentile(widths, outlier_percentile)
    height_thresh = np.percentile(heights, outlier_percentile)

    filtered = [entry for entry in bbox_data if entry[4] <= width_thresh and entry[5] <= height_thresh]
    if not filtered:
        filtered = bbox_data

    min_left = min(entry[0] for entry in filtered)
    min_top = min(entry[1] for entry in filtered)
    max_right = max(entry[2] for entry in filtered)
    max_bottom = max(entry[3] for entry in filtered)

    return (min_left, min_top, max_right, max_bottom)

def crop_and_center_images(images, crop_box):
    """Crop all images to the given bounding box and center them in square canvases."""
    min_left, min_top, max_right, max_bottom = crop_box
    crop_width = max_right - min_left
    crop_height = max_bottom - min_top
    max_dim = max(crop_width, crop_height)

    result = []

    for image in images:
        cropped = image.crop((min_left, min_top, max_right, max_bottom))
        square = Image.new("RGBA", (max_dim, max_dim), (0, 0, 0, 0))

        offset_x = (max_dim - crop_width) // 2
        offset_y = (max_dim - crop_height) // 2

        square.paste(cropped, (offset_x, offset_y), mask=cropped)
        result.append(square)

    return result

def resize_images(images, final_size):
    """Resize each image to a square of final_size × final_size."""
    return [img.resize((final_size, final_size), Image.LANCZOS) for img in images]

def crop_images(images, keys, final_size=64, outlier_percentile=95):
    """Crops all images to the tightest bounding box and centers them in a square canvas."""
    crop_box = calculate_cropping_bounds(images, keys, outlier_percentile)
    if crop_box:
        cropped = crop_and_center_images(images, crop_box)
        cropped_images = resize_images(cropped, final_size)
    else:
        cropped_images = images  # fallback to originals if bounding box fails

    return cropped_images

#endregion

#region -- PNG Emojis  ----------------------------------------------------------------------------------------------------------

def get_png_categories():
    """Retrieve all emoji type folders inside PNGs directory."""
    return [name for name in os.listdir(PNG_DIR) if os.path.isdir(os.path.join(PNG_DIR, name))]

def load_png_images(category):
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
            img = Image.open(img_path)
            
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            
            images.append(img)
            
            hex_parts = filename.replace(".png", "").split("_")
            key = "".join(chr(int(part, 16)) for part in hex_parts)
            keys.append(key)
        except Exception as e:
            log.debug(f"Failed to load image {filename}: {e}")

    return images, keys

#endregion

#region -- FONT Emojis ----------------------------------------------------------------------------------------------------------

def get_font_names():
    """Retrieve all font names from the Fonts directory."""
    return [name for name in os.listdir(FONTS_DIR) if name.endswith(".ttf")]

def is_significant_glyph(image):
    """Check if the glyph has more than 0.1% visible pixels (non-transparent)."""
    bbox = image.getbbox()
    if not bbox:
        return False  # Image is fully transparent
    total_pixels = image.width * image.height
    non_transparent_pixels = sum(1 for pixel in image.getdata() if pixel[3] > 0)
    return (non_transparent_pixels / total_pixels) > 0.001

def get_font_glyphs(font_path):
    """Retrieve emoji and symbol glyphs from a font, skipping Latin letters but keeping special symbols."""
    try:
        font = TTFont(font_path)
        glyphs = set()

        for table in font['cmap'].tables:
            for cp in table.cmap.keys():
                char = chr(cp)
                category = unicodedata.category(char)

                # Exclude standard Latin letters only (A-Z, a-z)
                if 'LATIN' in unicodedata.name(char, '') and category.startswith("L"):
                    continue

                # Exclude control characters (like newline, tabs)
                if category.startswith("C"):
                    continue

                # Include everything else (symbols, punctuation, numbers, emojis)
                glyphs.add(char)

        return sorted(glyphs)

    except Exception as e:
        print(f"Error reading font {font_path}: {e}")
        return []

def extract_font_codepoint_glyphs(font_path):
    """Return all codepoints in the font cmap as single-character strings."""
    try:
        font = TTFont(font_path)
        glyphs = set()

        for table in font['cmap'].tables:
            for cp in table.cmap.keys():
                glyphs.add(chr(cp))

        return sorted(glyphs)

    except Exception as e:
        log.error(f"Error reading font {font_path}: {e}")
        return []

def load_glyph_images(font_path):
    """Render all supported glyphs from a font as images, ensuring appropriate scaling and centering."""
    upscale_factor = 4
    ideal_size = 64  # Render resolution for quality

    font = ImageFont.truetype(font_path, ideal_size * upscale_factor)
    emoji_chars = extract_font_codepoint_glyphs(font_path)

    widths, heights = [], []
    emoji_bboxes = {}

    # Step 1: Measure bounding boxes
    for emoji_char in emoji_chars:
        bbox = font.getbbox(emoji_char, anchor="mm")
        if bbox:
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            widths.append(width)
            heights.append(height)
            emoji_bboxes[emoji_char] = (width, height)

    if not widths or not heights:
        log.debug(f"No valid glyphs found for font {font_path}.")
        return [], []

    # Step 2: Remove outliers (top 3%)
    width_thresh = np.percentile(widths, 97)
    height_thresh = np.percentile(heights, 97)
    filtered_chars = {
        char: (w, h)
        for char, (w, h) in emoji_bboxes.items()
        if w <= width_thresh and h <= height_thresh
    }

    max_width = max(w for w, _ in filtered_chars.values()) if filtered_chars else max(widths)
    max_height = max(h for _, h in filtered_chars.values()) if filtered_chars else max(heights)
    canvas_size = max(max_width, max_height)

    images = []
    keys = []

    for emoji_char in emoji_chars:
        if emoji_char not in filtered_chars:
            continue

        temp_canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(temp_canvas)

        # Anti-aliasing via 4-pass render
        cx = canvas_size // 2
        draw.text((cx + 1, cx), emoji_char, font=font, fill=(255, 255, 255, 255), anchor="mm")
        draw.text((cx - 1, cx), emoji_char, font=font, fill=(255, 255, 255, 255), anchor="mm")
        draw.text((cx, cx + 1), emoji_char, font=font, fill=(255, 255, 255, 255), anchor="mm")
        draw.text((cx, cx - 1), emoji_char, font=font, fill=(255, 255, 255, 255), anchor="mm")

        if is_significant_glyph(temp_canvas):
            images.append(temp_canvas)
            keys.append(emoji_char)
        else:
            log.debug(f"Skipping non-significant glyph: {emoji_char.encode('unicode_escape').decode()}")

    return images, keys

#endregion

#region -- Sprite Strips  ----------------------------------------------------------------------------------------------------------

def get_sprite_output_paths(category, size, mode):
    """Determine folder and file paths for sprite output based on sprite tier mode."""
    base_dir = {
        "deluxe": DELUXE_SPRITE_DIR,
        "full": FULL_SPRITE_DIR,
        "lite": LITE_SPRITE_DIR
    }[mode]

    category_folder = os.path.join(base_dir, category)
    os.makedirs(category_folder, exist_ok=True)

    slug = f"{to_camel_case(category)}_{mode.lower()}_{size}"
    
    output_sprite_path = os.path.join(category_folder, f"__emj_{slug}.png")
    metadata_path = os.path.join(category_folder, "metadata.json")

    return category_folder, output_sprite_path, metadata_path

def create_composite_sprite_sheet(images, keys, size):
    """Builds and returns the composite sprite sheet and metadata dictionary."""
    total_count = len(images)
    cols, rows = get_grid_layout(total_count)

    sheet_width = cols * (size + PADDING * 2)
    sheet_height = rows * (size + PADDING * 2)
    composite_sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))
    metadata = {}

    for index, (image, key) in enumerate(zip(images, keys)):
        if image is None:
            continue
        resized_img = image.resize((size, size), Image.LANCZOS)

        col = index % cols
        row = index // cols
        x_pos = col * (size + PADDING * 2) + PADDING
        y_pos = row * (size + PADDING * 2) + PADDING

        composite_sheet.paste(resized_img, (x_pos, y_pos))
        metadata[key] = index

    return composite_sheet, metadata, cols, rows, total_count

def save_sprite_metadata_file(path, metadata):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
    log.debug(f"Saved metadata: {path}")

def save_layout_hint_file(folder, cols, rows, total_count):
    filename = os.path.join(folder, f"{cols}x{rows}_{total_count}.txt")
    with open(filename, "w") as f:
        pass
    log.debug(f"Saved layout hint file {filename}")

def generate_sprite_strip(category, images, keys, size, mode="deluxe"):
    """Generate a sprite strip and metadata file for a given emoji category."""
    category_folder, output_sprite_path, metadata_path = get_sprite_output_paths(category, size, mode)

    if os.path.exists(output_sprite_path):
        log.debug(f"Skipping {output_sprite_path}, already exists.")
        return {}

    filtered_images, filtered_keys = filter_sprite_inputs(images, keys, mode)
    if not filtered_images:
        log.debug(f"No valid images for category {category}. Skipping sprite strip.")
        return {}

    composite_sheet, metadata, cols, rows, total_count = create_composite_sprite_sheet(filtered_images, filtered_keys, size)
    composite_sheet.save(output_sprite_path)
    log.debug(f"Saved sprite strip {output_sprite_path}")

    save_sprite_metadata_file(metadata_path, metadata)
    save_layout_hint_file(category_folder, cols, rows, total_count)

    return metadata

#endregion

#region -- Font Sheet Builder ----------------------------------------------------------------------------------

def get_font_output_paths(category, size, mode):
    """Determine output paths for the font sheet, .yy file, and lookup table."""
    base_dir = {
        "deluxe": DELUXE_FONT_DIR,
        "full": FULL_FONT_DIR,
        "lite": LITE_FONT_DIR
    }[mode]

    category_folder = os.path.join(base_dir, category)
    os.makedirs(category_folder, exist_ok=True)

    slug = f"{to_camel_case(category)}_{mode.lower()}_{size}"
    
    image_output = os.path.join(category_folder, f"__emj_fnt_{slug}.png")
    yy_output = os.path.join(category_folder, f"__emj_fnt_{slug}.yy")
    lookup_output = os.path.join(category_folder, f"lookup.json")

    return image_output, yy_output, lookup_output

def create_composite_font_sheet(images, keys, size):
    """
    Builds and returns the composite sprite sheet and metadata dictionary.
    """
    total_count = len(images)
    cols, rows = get_grid_layout(total_count)

    sheet_width = cols * (size + PADDING * 2)
    sheet_height = rows * (size + PADDING * 2)
    composite_sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))
    metadata = {}
    glyph_data = {}

    current_ord = FONT_OFFSET_KEY
    def get_next_font_glyph_index(current: int) -> int:
        """
        Returns the next valid index, skipping over known problematic glyph ranges.
        - Skips formatting characters (C format category)
        - Skips right-to-left ranges (like Hebrew)
        """
        while True:
            current += 1
            # Skip control characters (formatting, non-visible, etc.)
            if unicodedata.category(chr(current)).startswith("C"):
                continue
            # Skip Hebrew block (U+0590–U+05FF)
            if 0x0590 <= current <= 0x05FF:
                current = 0x05FF
                continue
            # Skip ZWJ (U+200D)
            if current == 0x200D:
                continue
            # Enforce max glyph index limit for GameMaker
            if current > 0xFFFF:
                raise ValueError("Exceeded GameMaker's max glyph index limit (0xFFFF).")
            return current

    # Optionally insert space glyph
    if FONT_INLUDE_SPACE:
        glyph_data[32] = {
            "character": 32,
            "x": 0,
            "y": 0,
            "width": 0,
            "height": 0,
            "shift": 0,
            "offset": 0
        }
        current_ord = max(current_ord, 32)  # ensure following glyphs skip space

    for index, (image, key) in enumerate(zip(images, keys)):
        if image is None:
            continue
        resized_img = image.resize((size, size), Image.LANCZOS)
        
        current_ord = get_next_font_glyph_index(current_ord)
        
        col = index % cols
        row = index // cols
        x_pos = col * (size + PADDING * 2) + PADDING
        y_pos = row * (size + PADDING * 2) + PADDING

        composite_sheet.paste(resized_img, (x_pos, y_pos))
        metadata[key] = index

        w, h = resized_img.size
        glyph_data[index] = {
            "character": current_ord,
            "x": x_pos,
            "y": y_pos,
            "width": w,
            "height": h,
            "shift": w,
            "offset": 0  # customizable later
        }
        

    return composite_sheet, metadata, cols, rows, index, glyph_data

def save_font_metadata_file(path, metadata):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
    log.debug(f"Saved metadata: {path}")

def save_font_yy_file(path, font_name, glyph_data, size):
    """Saves a GameMaker .yy font asset file."""

    # Generate formatted string with every character index, 40 per line
    glyph_indexes = sorted(g["character"] for g in glyph_data.values())
    lines = []
    for i in range(0, len(glyph_indexes), 40):
        line = " ".join(str(idx) for idx in glyph_indexes[i:i+40])
        lines.append(line)
    glyph_list_string = "\n".join(lines)

    ranges = []
    grouped = []
    for _, group in itertools.groupby(enumerate(glyph_indexes), lambda x: x[1] - x[0]):
        group = list(group)
        start = group[0][1]
        end = group[-1][1]
        grouped.append({"lower": start, "upper": end})
    ranges = grouped

    yy_data = {
    "$GMFont":"",
    "%Name":font_name,
    "AntiAlias":1,
    "applyKerning":0,
    "ascender":size,
    "ascenderOffset":0,
    "bold":False,
    "canGenerateBitmap":True,
    "charset":0,
    "first":0,
    "fontName":f"{font_name} Emojis",
    "glyphOperations":0,
    "glyphs": list(glyph_data.values()),
    "hinting":0,
    "includeTTF":False,
    "interpreter":0,
    "italic":False,
    "kerningPairs":[],
    "last":0,
    "lineHeight":size,
    "maintainGms1Font":False,
    "name":"Font1",
    "parent":{
        "name":"EmojiFonts",
        "path":"EmojiFonts.yyp",
    },
    "pointRounding":0,
    "ranges": ranges,
    "regenerateBitmap":False,
    "resourceType":"GMFont",
    "resourceVersion":"2.0",
    "sampleText":glyph_list_string,
    "sdfSpread":8,
    "size":size,
    "styleName":"Regular",
    "textureGroupId":{
        "name":"Default",
        "path":"texturegroups/Default",
    },
    "TTFName":f"{font_name} Emojis",
    "usesSDF":False,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(yy_data, f, ensure_ascii=False, indent=4)
    log.debug(f"Saved .yy font file: {path}")

def generate_font_sheet(category, images, keys, size, mode="deluxe"):
    """
    Creates a GameMaker-compatible bitmap font and supporting lookup table.
    - `images` is a list of pre-rendered glyph images (e.g. from load_glyph_images).
    - `emoji_lookup` is a dict like {"😀": 33, "🎉": 34, ...}
    """
    image_path, yy_path, metadata_path = get_font_output_paths(category, size, mode)

    if os.path.exists(image_path):
        log.debug(f"Skipping {image_path}, already exists.")
        return {}
    
    filtered_images, filtered_keys = filter_sprite_inputs(images, keys, mode)
    if not filtered_images:
        log.debug(f"No valid images for category {category}. Skipping sprite strip.")
        return {}

    composite_sheet, metadata, cols, rows, total_count, glyph_data = create_composite_font_sheet(filtered_images, filtered_keys, size)
    composite_sheet.save(image_path)
    log.debug(f"Saved font texture: {image_path}")

    save_font_yy_file(yy_path, category, glyph_data, size)
    save_font_metadata_file(metadata_path, metadata)

    log.info(f"✅ Generated font sheet '{category}' with {len(glyph_data)} glyphs.")

#endregion

#region -- Generation Main Function  ----------------------------------------------------------------------------------------------------------

def generate_all_sprite_textures():
    """Generate texture sheets for all categories and fonts."""
    for category in os.listdir(PNG_DIR):
        category_path = os.path.join(PNG_DIR, category)
        if not os.path.isdir(category_path):
            continue

        # Check and print all sprite sheet output paths
        if all_output_files_exist(SPRITE_SHEETS_DIR, category, MODES, TEXTURE_SIZES):
            print(f"Skipping {category} - All sprite sheets for all tiers already exist.")
            continue

        images, keys = load_png_images(category)
        images = crop_images(images, keys)
        images, keys = sort_emojis_by_key(images, keys)
        image_count = len(images)  # Track count per category

        for size in TEXTURE_SIZES:
            for mode in MODES:
                #generate_sprite_strip(category, images, keys, size, mode)
                continue
            
        log.info(f"✅ Processed {image_count} images for category '{category}'.")

    for font_name in os.listdir(FONTS_DIR):
        if not font_name.endswith(".ttf"):
            continue
        
        font_path = os.path.join(FONTS_DIR, font_name)
        category = os.path.splitext(font_name)[0]

        # Check and print all sprite sheet output paths
        category_slug = to_camel_case(category)
        if all_output_files_exist(SPRITE_SHEETS_DIR, category, MODES, TEXTURE_SIZES):
            print(f"Skipping {category} - All sprite sheets for all tiers already exist.")
            continue
        
        images, keys = load_glyph_images(font_path)
        images = crop_images(images, keys)
        images, keys = sort_emojis_by_key(images, keys)
        image_count = len(images)  # Track count per category
        
        for size in TEXTURE_SIZES:
            for mode in MODES:
                generate_sprite_strip(category, images, keys, size, mode)
        
        log.info(f"✅ Processed {image_count} images for category '{category}'.")


def generate_all_font_textures():
    """Generate font texture sheets for all fonts with all tiers and sizes."""

    for category in os.listdir(PNG_DIR):
        category_path = os.path.join(PNG_DIR, category)
        if not os.path.isdir(category_path):
            continue

        # Check and print all sprite sheet output paths
        if all_output_files_exist(FONT_SHEETS_DIR, category, MODES, TEXTURE_SIZES):
            print(f"Skipping {category} - All sprite sheets for all tiers already exist.")
            continue

        images, keys = load_png_images(category)
        images = crop_images(images, keys)
        images, keys = sort_emojis_by_key(images, keys)
        image_count = len(images)  # Track count per category

        for size in TEXTURE_SIZES:
            for mode in MODES:
                generate_font_sheet(category, images, keys, size, mode)
                continue
            
        log.info(f"✅ Processed {image_count} images for category '{category}'.")

    # Dont handle font based emoji sets, because those could simply be included in a GML since they are already valid
    
    # Generate resource_order file
    resource_lines = []
    order = 0
    for mode in MODES:
        base_dir = {
            "deluxe": DELUXE_FONT_DIR,
            "full": FULL_FONT_DIR,
            "lite": LITE_FONT_DIR
        }[mode]
        for font_name in os.listdir(base_dir):
            folder_path = os.path.join(base_dir, font_name)
            if not os.path.isdir(folder_path):
                continue
            for file in os.listdir(folder_path):
                if file.endswith(".yy"):
                    name = os.path.splitext(file)[0]
                    rel_path = os.path.relpath(os.path.join("fonts", name, font_name, file)).replace("\\", "/")
                    resource_lines.append(f'{{"name":"{name}","order":{order},"path":"{rel_path}",}},')
                    order += 1

    resource_path = os.path.join(FONT_SHEETS_DIR, "resource_order.txt")
    with open(resource_path, "w", encoding="utf-8") as f:
        f.write("\n".join(resource_lines))
    log.info(f"📄 Saved resource order: {resource_path}")

    log.info("🎉 Font texture generation complete!")
    
#endregion

if __name__ == "__main__":
    generate_all_sprite_textures()
    generate_all_font_textures()

    log.info("🎉 Texture generation complete!")