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
FONT_INCLUDE_SPACE = False

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

def calculate_image_cropping_bounds(images):
    """
    Calculates per-image bounding box and size from alpha channel.
    Returns:
        List of tuples: (left, top, right, bottom, width, height)
        (If keys are given, aligns 1:1 with them)
    """
    bounds = []

    for i, img in enumerate(images):
        alpha = img.split()[-1].point(lambda p: 255 if p > 127 else 0, "1")
        bbox = alpha.getbbox()

        if bbox:
            left, top, right, bottom = bbox
            width = right - left
            height = bottom - top
            bounds.append((left, top, right, bottom, width, height))
        else:
            bounds.append(None)

    return bounds

def crop_images_to_box(images, crop_box):
    """
    Crop all images to the same shared box.
    """
    return [img.crop(crop_box) for img in images]

def resize_cropped_images(images, bounds, scale):
    """
    Resizes each image by a constant scale factor, preserving aspect ratio.
    Proportionally scales each bounding box as well.

    Args:
        images (List[Image]): The input cropped images.
        bounds (List[Tuple|None]): Bounding boxes in (left, top, right, bottom, width, height).
        scale (float): Scale factor to apply to width/height.

    Returns:
        Tuple[List[Image], List[Tuple|None]]: (resized images, scaled bounds)
    """
    resized_images = []
    resized_bounds = []

    for img, bbox in zip(images, bounds):
        original_width, original_height = img.width, img.height
        new_width = int(math.ceil(original_width * scale))
        new_height = int(math.ceil(original_height * scale))

        resized_img = img.resize((new_width, new_height), Image.LANCZOS)
        resized_images.append(resized_img)

        if bbox is not None:
            left, top, right, bottom, width, height = bbox
            scaled_bbox = (
                left * scale,
                top * scale,
                right * scale,
                bottom * scale,
                width * scale,
                height * scale
            )
        else:
            scaled_bbox = None

        resized_bounds.append(scaled_bbox)

    return resized_images, resized_bounds


def calculate_global_cropping_bounds(images, outlier_percentile=95):
    """
    Determines a shared cropping box for all images, removing outliers.
    """
    bbox_data = calculate_image_cropping_bounds(images)
    bbox_data = [b for b in bbox_data if b is not None]

    if not bbox_data:
        log.debug("No bounding boxes found.")
        return None

    widths = [b[4] for b in bbox_data]
    heights = [b[5] for b in bbox_data]

    width_thresh = np.percentile(widths, outlier_percentile)
    height_thresh = np.percentile(heights, outlier_percentile)

    filtered = [b for b in bbox_data if b[4] <= width_thresh and b[5] <= height_thresh]
    if not filtered:
        filtered = bbox_data

    min_left = min(b[0] for b in filtered)
    min_top = min(b[1] for b in filtered)
    max_right = max(b[2] for b in filtered)
    max_bottom = max(b[3] for b in filtered)

    return (min_left, min_top, max_right, max_bottom)

def crop_images_to_individual_boxes(images, bounds):
    """
    Crop each image using its own bounding box.
    If the bounding box is None (fully transparent), a copy of the original image is returned.
    
    Args:
        images (List[Image]): List of PIL Image objects.
        bounds (List[Tuple|None]): List of bounding boxes in the format 
            (left, top, right, bottom, width, height) or None if fully transparent.
    
    Returns:
        List[Image]: List of cropped images.
    """
    cropped_images = []

    for img, bbox in zip(images, bounds):
        if bbox is not None:
            left, top, right, bottom, _, _ = bbox
            cropped = img.crop((left, top, right, bottom))
        else:
            cropped = img.copy()

        cropped_images.append(cropped)

    return cropped_images

def resize_images(images, final_size):
    """Resize each image to a square of final_size × final_size."""
    return [img.resize((final_size, final_size), Image.LANCZOS) for img in images]

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
    if FONT_INCLUDE_SPACE:
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
        "name":"Emobble",
        "path":"Emobble.yyp",
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

#region -- Texture Map ---------------------------------------------------------------------------------------------------------

def get_largest_image_dimension(images, padding):
    """
    Compute the largest single image dimension (width or height), including padding.
    This ensures the atlas is at least large enough to fit the largest image.
    """
    max_dim = 0
    for img in images:
        padded_width = img.width + padding * 2
        padded_height = img.height + padding * 2
        max_dim = max(max_dim, padded_width, padded_height)

    return max_dim

def estimate_initial_atlas_size(images, padding):
    """
    Estimates the initial square atlas size based on total pixel volume.
    Uses sqrt(total_area) as the side length.
    """
    total_area = 0
    for img in images:
        w = img.width + padding * 2
        h = img.height + padding * 2
        total_area += w * h

    return int(math.ceil(math.sqrt(total_area)))

def pack_texture_images(images, keys, padding=1):
    """
    Packs a list of variable-sized images into a square texture atlas.
    Returns:
        (Image, dict): composite image and metadata {key: {x, y, w, h}}
    """
    assert len(images) == len(keys)

    # Sort images by area (width * height), largest first
    sortable = sorted(
        zip(images, keys),
        key=lambda pair: pair[0].width * pair[0].height,
        reverse=True
    )
    sorted_images, sorted_keys = zip(*sortable)

    initial_guess_size = estimate_initial_atlas_size(sorted_images, padding)
    largest_dim = get_largest_image_dimension(sorted_images, padding)
    atlas_size = max(64, initial_guess_size)  # start at 64x64 minimum

    while True:
        atlas = Image.new("RGBA", (atlas_size, atlas_size), (0, 0, 0, 0))
        metadata = {}
        placement_plan = []

        x = y = row_height = 0
        success = True

        for image, key in zip(sorted_images, sorted_keys):
            padded_w = image.width + padding * 2
            padded_h = image.height + padding * 2

            if x + padded_w > atlas_size:
                x = 0
                y += row_height
                row_height = 0

            if y + padded_h > atlas_size:
                success = False
                break

            placement_plan.append((image, key, x + padding, y + padding))
            metadata[key] = {
                "x": x + padding,
                "y": y + padding,
                "w": image.width,
                "h": image.height
            }

            x += padded_w
            row_height = max(row_height, padded_h)

        if success:
            for image, key, px, py in placement_plan:
                atlas.paste(image, (px, py), mask=image)
            return atlas, metadata
        else:
            #extremely slow, but this produces the best possible fit.
            atlas_size += 1

def generate_gml_lookup_script_text(category_slug, mode, size, key_metadata):
    """
    Generates the GML source code for a lookup function using key metadata.
    Returns the GML function as a string.
    """
    function_name = f"emj_lt_{category_slug}_{mode}_{size}"
    sprite_name = f"emj_spr_{category_slug}_{mode}_{size}"

    # Convert to JSON and escape for GML string
    raw_json = json.dumps(key_metadata, ensure_ascii=True)
    escaped_json = raw_json.replace("\\", "\\\\").replace("\"", "\\\"")

    # Generate the final GML function text
    gml_code = f"""//lt stands for Lookup Table
function {function_name}() {{
\t////////////////////////////////////////////////////////////////////////////////
\t//This is a generated file from `generate_lookup_scripts.py` please dont modify.
\t////////////////////////////////////////////////////////////////////////////////
\tstatic lookup = undefined
\tif is_undefined(lookup) {{
\t\tlookup = json_parse("{escaped_json}");
\t\t__emj_build_format_tags_for_lookup_table(lookup, "{sprite_name}")
\t}}
\treturn lookup;
}}"""
    
    return gml_code



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
    resource_order_lines = []
    resources_lines = []
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
                    resource_order_lines.append(f'{{"name":"{name}","order":{order},"path":"{rel_path}",}},')
                    resources_lines.append(f'{{"name":"{name}","path":"{rel_path}",}},')
                    order += 1

    resource_order_path = os.path.join(FONT_SHEETS_DIR, "resource_order.txt")
    with open(resource_order_path, "w", encoding="utf-8") as f:
        f.write("\n".join(resource_order_lines))
    log.info(f"📄 Saved resource order: {resource_order_path}")

    resources_path = os.path.join(FONT_SHEETS_DIR, "resources.txt")
    with open(resources_path, "w", encoding="utf-8") as f:
        f.write("\n".join(resources_lines))
    log.info(f"📄 Saved resource order: {resources_path}")

    log.info("🎉 Font texture generation complete!")

def generate_texture_map(data_map):
    """
    Generate tightly packed texture maps (PNG) and GML lookup scripts for all categories.
    PNGs are tightly cropped and saved alongside a generated GML script.
    """
    texture_sheet_output_root = os.path.join(ASSETS_DIR, "Texture Sheets")
    os.makedirs(texture_sheet_output_root, exist_ok=True)

    for category_name, category_data in data_map.items():
        for mode_name, mode_group in category_data["tight_processed"].items():
            for size_value, size_entry in mode_group.items():
                emoji_images = size_entry["images"]
                emoji_keys = size_entry["keys"]
                emoji_bounds = size_entry["bounds"]

                # Pack the texture sheet
                packed_image, key_metadata = pack_texture_images(
                    emoji_images,
                    emoji_keys,
                    PADDING,
                )

                # ✂️ Crop empty borders from final atlas (with padding)
                crop_box = packed_image.getbbox()
                if crop_box:
                    left = max(0, crop_box[0] - PADDING)
                    top = max(0, crop_box[1] - PADDING)
                    right = min(packed_image.width, crop_box[2] + PADDING)
                    bottom = min(packed_image.height, crop_box[3] + PADDING)
                    packed_image = packed_image.crop((left, top, right, bottom))

                # Folder path: Texture Sheets\Mode\Size\Category
                output_folder = os.path.join(
                    texture_sheet_output_root,
                    mode_name.capitalize(),
                    str(size_value),
                    category_name
                )
                os.makedirs(output_folder, exist_ok=True)

                filename_slug = f"{category_data['slug']}_{mode_name}_{size_value}"
                sprite_name = f"emj_spr_{filename_slug}"
                gml_function_name = f"emj_lt_{filename_slug}"

                # Final output paths
                png_output_path = os.path.join(output_folder, f"{sprite_name}.png")
                gml_output_path = os.path.join(output_folder, f"{gml_function_name}.gml")

                # Save cropped sprite sheet
                packed_image.save(png_output_path)

                # Generate and save GML script with inline lookup metadata
                gml_script = generate_gml_lookup_script_text(
                    category_slug=category_data["slug"],
                    mode=mode_name,
                    size=size_value,
                    key_metadata=key_metadata
                )
                with open(gml_output_path, "w", encoding="utf-8") as gml_file:
                    gml_file.write(gml_script)

                log.info(f"✅ Saved cropped atlas and GML for {filename_slug}")


#endregion

def build_category_data_map(modes=MODES, sizes=TEXTURE_SIZES, outlier_percentile=95):
    """
    Builds a fully processed data map for all emoji categories, organized by mode and size.
    Includes original images, center-cropped + tight-cropped versions, and resized variants.
    """
    data_map = {}

    for category in os.listdir(PNG_DIR):
        category_path = os.path.join(PNG_DIR, category)
        if not os.path.isdir(category_path):
            continue

        images, keys = load_png_images(category)
        if not images or not keys:
            log.warning(f"⚠️ No valid images found in category: {category}")
            continue
        
        images, keys = sort_emojis_by_key(images, keys)
        slug = to_camel_case(category)

        # --- CENTER CROPPING ---
        crop_box = calculate_global_cropping_bounds(images, outlier_percentile)
        if crop_box is None:
            log.warning(f"⚠️ Skipping category '{category}' due to missing crop box.")
            continue

        center_cropped = crop_images_to_box(images, crop_box)

        # --- TIGHT CROPPING ---
        tight_bounds = calculate_image_cropping_bounds(images)
        tight_cropped = crop_images_to_individual_boxes(images, tight_bounds)

        # --- Initialize category entry ---
        category_data = {
            "name": category,
            "slug": slug,
            "path": category_path,
            "image_count": len(images),
            "original": {
                "images": images,
                "keys": keys
            },
            "cropping": {
                "tight_cropped_images": tight_cropped,
                "center_cropped_images": center_cropped,
                "bounding_box": crop_box
            },
            "processed": {},
            "tight_processed": {}
        }

        for mode in modes:
            # Center-cropped variants (square uniform)
            mode_images, mode_keys = filter_sprite_inputs(center_cropped, keys, mode)
            if mode_images:
                category_data["processed"][mode] = {}
                for size in sizes:
                    resized = resize_images(mode_images, size)
                    category_data["processed"][mode][size] = {
                        "images": resized,
                        "keys": mode_keys
                    }

            # Tight-cropped variants (preserve aspect ratio, scale per size)
            tight_mode_images, _unsued = filter_sprite_inputs(tight_cropped, keys, mode)
            if tight_mode_images:
                category_data["tight_processed"][mode] = {}

                for size in sizes:
                    scale_factors = [size / img.height for img in images]
                    tight_resized, scaled_bounds = resize_cropped_images(
                        tight_mode_images,
                        tight_bounds,
                        scale=scale_factors[0] if len(set(scale_factors)) == 1 else 1.0  # fallback safety
                    )

                    # If mixed scales (i.e., per-image scaling), override with per-image scaling loop
                    if len(set(scale_factors)) > 1:
                        tight_resized = []
                        scaled_bounds = []
                        for img, bbox, scale in zip(tight_mode_images, tight_bounds, scale_factors):
                            img_list, bound_list = resize_cropped_images([img], [bbox], scale)
                            tight_resized.append(img_list[0])
                            scaled_bounds.append(bound_list[0])

                    category_data["tight_processed"][mode][size] = {
                        "images": tight_resized,
                        "keys": mode_keys,
                        "bounds": scaled_bounds
                    }

        data_map[category] = category_data
        log.info(f"📦 Preprocessed category '{category}' with {category_data['image_count']} emojis.")

    return data_map


if __name__ == "__main__":
    data_map = build_category_data_map()
    generate_texture_map(data_map)
    #generate_sprite_textures(data_map)
    #generate_font_textures(data_map)
    
    log.info("🎉 Texture generation complete!")


