from __future__ import annotations

import argparse
from dataclasses import dataclass
import itertools
import json
import logging
import math
import os
from pathlib import Path
import re
import shutil
import uuid
import unicodedata

from PIL import Image

TOOLS_ROOT = Path(__file__).resolve().parent


# -------------------------------------------------------------------------------------------------
# Minimal shared pipeline helpers (inlined to keep the project to 5 scripts).
# -------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class OutputPaths:
    root: Path
    fonts: Path
    sprites: Path
    scripts: Path


def project_root() -> Path:
    return TOOLS_ROOT


def output_paths(output_root: str | Path | None = None) -> OutputPaths:
    root = Path(output_root) if output_root else project_root() / "output"
    return OutputPaths(
        root=root,
        fonts=root / "fonts",
        sprites=root / "sprites",
        scripts=root / "scripts",
    )


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def ensure_output_dirs(paths: OutputPaths, clean: bool = False) -> None:
    if clean:
        ensure_clean_dir(paths.root)
    paths.fonts.mkdir(parents=True, exist_ok=True)
    paths.sprites.mkdir(parents=True, exist_ok=True)
    paths.scripts.mkdir(parents=True, exist_ok=True)


def default_png_source_dir() -> Path:
    root = project_root()

    scraped = root / "db" / "PNGs"
    if scraped.exists():
        return scraped

    manual = root / "temp" / "manual_pngs" / "PNGs"
    if manual.exists():
        return manual

    return root / "Assets" / "PNGs"


# -------------------------------------------------------------------------------------------------
# Font + variant atlas builder (trimmed from the old src/texturesheet_builder.py).
# -------------------------------------------------------------------------------------------------


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

PADDING = 1

# Trim only left/right transparent columns to produce tighter bounding boxes.
# This is intentionally applied without changing any pixel alpha values.
ALPHA_CULL_THRESHOLD = 0.1


def _parent_for_set_size(set_slug: str, size: int) -> dict:
    # Desired IDE structure: _Libraries/Emobble/<set>/<set>_<size>
    folder_name = f"{set_slug}_{size}"
    return {
        "name": folder_name,
        "path": f"folders/_Libraries/Emobble/{set_slug}/{folder_name}.yy",
    }


def _det_uuid(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))


def save_sprite_resource_from_atlas(
    *,
    sprite_name: str,
    atlas_png_path: str,
    sprites_out_dir: str,
    parent: dict,
) -> None:
    out_dir = Path(sprites_out_dir) / sprite_name
    out_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(atlas_png_path) as im:
        width, height = im.size

    frame_id = _det_uuid(f"{sprite_name}:frame")
    layer_id = _det_uuid(f"{sprite_name}:layer")
    keyframe_id = _det_uuid(f"{sprite_name}:keyframe")

    # GameMaker stores the actual image under:
    #   sprites/<spr>/layers/<frameGuid>/<layerGuid>.png
    # (Project Health warnings reference this exact layout.)
    layers_dir = out_dir / "layers" / frame_id
    layers_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(atlas_png_path, layers_dir / f"{layer_id}.png")

    # GameMaker also expects a root-level per-frame image:
    #   sprites/<spr>/<frameGuid>.png
    # (Project Health warnings reference this exact path.)
    frame_png = out_dir / f"{frame_id}.png"
    src = Path(atlas_png_path)
    try:
        if src.resolve() != frame_png.resolve():
            shutil.copyfile(src, frame_png)
    except FileNotFoundError:
        raise

    # Some GameMaker workflows/tools also expect a root-level PNG alongside the .yy.
    # Keep a duplicate here as requested: sprites/<spr>/<spr>.png
    dst = out_dir / f"{sprite_name}.png"
    try:
        if src.resolve() != dst.resolve():
            shutil.copyfile(src, dst)
    except FileNotFoundError:
        # If the source is missing, let later operations fail naturally.
        raise

    yy_path = out_dir / f"{sprite_name}.yy"

    yy = {
        "$GMSprite": "",
        "%Name": sprite_name,
        "bboxMode": 0,
        "bbox_bottom": max(0, height - 1),
        "bbox_left": 0,
        "bbox_right": max(0, width - 1),
        "bbox_top": 0,
        "collisionKind": 1,
        "collisionTolerance": 0,
        "DynamicTexturePage": False,
        "edgeFiltering": False,
        "For3D": False,
        "frames": [
            {
                "$GMSpriteFrame": "",
                "%Name": frame_id,
                "name": frame_id,
                "resourceType": "GMSpriteFrame",
                "resourceVersion": "2.0",
            }
        ],
        "gridX": 0,
        "gridY": 0,
        "height": height,
        "HTile": False,
        "layers": [
            {
                "$GMImageLayer": "",
                "%Name": layer_id,
                "blendMode": 0,
                "displayName": "default",
                "isLocked": False,
                "name": layer_id,
                "opacity": 100.0,
                "resourceType": "GMImageLayer",
                "resourceVersion": "2.0",
                "visible": True,
            }
        ],
        "name": sprite_name,
        "nineSlice": None,
        "origin": 0,
        "parent": parent,
        "preMultiplyAlpha": False,
        "resourceType": "GMSprite",
        "resourceVersion": "2.0",
        "sequence": {
            "$GMSequence": "",
            "%Name": sprite_name,
            "autoRecord": True,
            "backdropHeight": 768,
            "backdropImageOpacity": 0.5,
            "backdropImagePath": "",
            "backdropWidth": 1366,
            "backdropXOffset": 0.0,
            "backdropYOffset": 0.0,
            "events": {
                "$KeyframeStore<MessageEventKeyframe>": "",
                "Keyframes": [],
                "resourceType": "KeyframeStore<MessageEventKeyframe>",
                "resourceVersion": "2.0",
            },
            "eventStubScript": None,
            "eventToFunction": {},
            "length": 1.0,
            "lockOrigin": False,
            "moments": {
                "$KeyframeStore<MomentsEventKeyframe>": "",
                "Keyframes": [],
                "resourceType": "KeyframeStore<MomentsEventKeyframe>",
                "resourceVersion": "2.0",
            },
            "name": sprite_name,
            "playback": 1,
            "playbackSpeed": 0.0,
            "playbackSpeedType": 0,
            "resourceType": "GMSequence",
            "resourceVersion": "2.0",
            "showBackdrop": True,
            "showBackdropImage": False,
            "timeUnits": 1,
            "tracks": [
                {
                    "$GMSpriteFramesTrack": "",
                    "builtinName": 0,
                    "events": [],
                    "inheritsTrackColour": True,
                    "interpolation": 1,
                    "isCreationTrack": False,
                    "keyframes": {
                        "$KeyframeStore<SpriteFrameKeyframe>": "",
                        "Keyframes": [
                            {
                                "$Keyframe<SpriteFrameKeyframe>": "",
                                "Channels": {
                                    "0": {
                                        "$SpriteFrameKeyframe": "",
                                        "Id": {
                                            "name": frame_id,
                                            "path": f"sprites/{sprite_name}/{sprite_name}.yy",
                                        },
                                        "resourceType": "SpriteFrameKeyframe",
                                        "resourceVersion": "2.0",
                                    }
                                },
                                "Disabled": False,
                                "id": keyframe_id,
                                "IsCreationKey": False,
                                "Key": 0.0,
                                "Length": 1.0,
                                "resourceType": "Keyframe<SpriteFrameKeyframe>",
                                "resourceVersion": "2.0",
                                "Stretch": False,
                            }
                        ],
                        "resourceType": "KeyframeStore<SpriteFrameKeyframe>",
                        "resourceVersion": "2.0",
                    },
                    "modifiers": [],
                    "name": "frames",
                    "resourceType": "GMSpriteFramesTrack",
                    "resourceVersion": "2.0",
                    "spriteId": None,
                    "trackColour": 0,
                    "tracks": [],
                    "traits": 0,
                }
            ],
            "visibleRange": None,
            "volume": 1.0,
            "xorigin": 0,
            "yorigin": 0,
        },
        "swatchColours": None,
        "swfPrecision": 0.5,
        "tags": _tags_for_sprite(),
        "textureGroupId": {"name": "Default", "path": "texturegroups/Default"},
        "type": 0,
        "VTile": False,
        "width": width,
    }

    yy_path.write_text(json.dumps(yy, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
FONT_INCLUDE_SPACE = True

EMOBBLE_SPECIAL_SIZE = 20

# Emit a special 20px asset as requested.
EMOBBLE_FONT_SIZES = [16, EMOBBLE_SPECIAL_SIZE, 24, 32, 48, 64]
EMOBBLE_ATLAS_SIZES = [16, EMOBBLE_SPECIAL_SIZE, 24, 32, 48, 64]


def _tags_for_font_size(size: int) -> list[str]:
    tags = ["emoji"]
    if int(size) == int(EMOBBLE_SPECIAL_SIZE):
        tags.append("font_size:2")
    return tags


def _tags_for_sprite() -> list[str]:
    return ["emoji"]


def to_camel_case(name: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9 ]+", "", str(name))
    parts = clean.strip().split()
    if not parts:
        return ""
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


# Output set naming overrides (requested).
# Keys are the *previous* slugs produced by to_camel_case().
SET_SLUG_OVERRIDES: dict[str, str] = {
    "microsoftWindows10": "SegoeUI",
    "microsoftFluentFlat": "FluentFlat",
    "microsoftFluent3d": "Fluent3D",
    "googleNoto": "googleNotoColored",
    "noto": "googleNotoMono",
}


def _to_asset_slug(name: str) -> str:
    base = to_camel_case(name)
    return SET_SLUG_OVERRIDES.get(base, base)


def _is_single_codepoint_emoji(emoji: str) -> bool:
    return isinstance(emoji, str) and len(emoji) == 1


def _has_non_bmp_codepoint(s: str) -> bool:
    return isinstance(s, str) and any(ord(ch) > 0xFFFF for ch in s)


def _fit_image_to_square(img: Image.Image, size: int) -> Image.Image:
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    w, h = img.size
    if w <= 0 or h <= 0:
        return Image.new("RGBA", (size, size), (0, 0, 0, 0))

    scale = min(float(size) / float(w), float(size) / float(h))
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    if (new_w, new_h) != (w, h):
        img = img.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    off_x = (size - img.size[0]) // 2
    off_y = (size - img.size[1]) // 2
    canvas.paste(img, (off_x, off_y), mask=img)
    return canvas


def _cull_alpha_lr(img: Image.Image, *, alpha_threshold: float = ALPHA_CULL_THRESHOLD) -> Image.Image:
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    w, h = img.size
    if w <= 1 or h <= 0:
        return img

    # Keep columns that have any pixel with alpha > threshold.
    # Threshold is in 0..1 alpha space (0.1 requested).
    thr = float(alpha_threshold) * 255.0
    alpha = img.getchannel("A")
    a = alpha.load()

    left: int | None = None
    for x in range(w):
        for y in range(h):
            if a[x, y] > thr:
                left = x
                break
        if left is not None:
            break

    # Fully transparent: nothing to cull.
    if left is None:
        return img

    right: int = left
    for x in range(w - 1, -1, -1):
        for y in range(h):
            if a[x, y] > thr:
                right = x
                break
        else:
            continue
        break

    if left <= 0 and right >= (w - 1):
        return img
    if right <= left:
        return img.crop((left, 0, left + 1, h))

    # Vertical bounds are intentionally untouched.
    return img.crop((left, 0, right + 1, h))


_MICRO_SEQUENCE_MODIFIERS: set[int] = {0xFE0E, 0xFE0F, 0x20E3}


def _micro_sequence_base_codepoint(seq: str) -> int | None:
    if not isinstance(seq, str) or len(seq) <= 1:
        return None
    cps = [ord(c) for c in seq]
    if 0x200D in cps:
        return None
    non_mod = [cp for cp in cps if cp not in _MICRO_SEQUENCE_MODIFIERS]
    if len(non_mod) != 1:
        return None
    return non_mod[0]


def _build_micro_sequence_font_overrides(keys: list[str]) -> dict[str, int]:
    GM_FONT_MAX_CODEPOINT = 0xFFFF
    used_codepoints: set[int] = {
        ord(k) for k in keys if _is_single_codepoint_emoji(k) and ord(k) <= GM_FONT_MAX_CODEPOINT
    }
    overrides: dict[str, int] = {}
    for k in keys:
        if _is_single_codepoint_emoji(k):
            continue
        base = _micro_sequence_base_codepoint(k)
        if base is None or base in used_codepoints:
            continue
        if base > GM_FONT_MAX_CODEPOINT:
            continue
        if base in overrides.values():
            continue
        overrides[k] = base
        used_codepoints.add(base)
    return overrides


def get_grid_layout(count: int) -> tuple[int, int]:
    cols = math.ceil(math.sqrt(count))
    rows = math.ceil(count / cols) if cols else 0
    return cols, rows


def _parse_hex_parts_from_filename(filename: str) -> list[str]:
    stem = filename
    if stem.lower().endswith(".png"):
        stem = stem[:-4]
    stem = stem.replace("-", "_")
    parts: list[str] = []
    for p in stem.split("_"):
        p = p.strip().upper()
        if not p:
            continue
        if all(c in "0123456789ABCDEF" for c in p):
            parts.append(p)
    return parts


def load_png_images(set_name: str, png_dir: str) -> tuple[list[Image.Image], list[str]]:
    set_path = os.path.join(png_dir, set_name)
    filenames = [f for f in os.listdir(set_path) if f.lower().endswith(".png")]
    filenames = sorted(filenames, key=lambda x: [int(part, 16) for part in _parse_hex_parts_from_filename(x)])

    images: list[Image.Image] = []
    keys: list[str] = []
    for filename in filenames:
        try:
            img_path = os.path.join(set_path, filename)
            img = Image.open(img_path)
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            images.append(img)
            hex_parts = _parse_hex_parts_from_filename(filename)
            key = "".join(chr(int(part, 16)) for part in hex_parts)
            keys.append(key)
        except Exception as e:
            log.debug(f"Failed to load image {filename}: {e}")
    return images, keys


def sort_emojis_by_key(images: list[Image.Image], keys: list[str]) -> tuple[list[Image.Image], list[str]]:
    SKINTONE_RANGE = range(0x1F3FB, 0x1F400)

    def tier_weight(key: str) -> int:
        normalized = unicodedata.normalize("NFC", key)
        codepoints = [ord(c) for c in normalized]
        has_zwj = "\u200d" in normalized
        has_skintone = any(cp in SKINTONE_RANGE for cp in codepoints)

        if not has_zwj and not has_skintone:
            return 0
        elif has_skintone and len(codepoints) == 1:
            return 0
        elif not has_zwj:
            return 1
        else:
            return 2

    combined = sorted(zip(keys, images), key=lambda x: (tier_weight(x[0]), [ord(c) for c in x[0]]))
    if not combined:
        return [], []
    sorted_keys, sorted_images = zip(*combined)
    return list(sorted_images), list(sorted_keys)


def get_font_output_paths(set_name: str, size: int, fonts_out_dir: str) -> tuple[str, str]:
    slug = _to_asset_slug(set_name)
    asset_name = f"fnt_{slug}_{size}"
    out_root = fonts_out_dir
    out_dir = os.path.join(out_root, asset_name)
    os.makedirs(out_dir, exist_ok=True)
    image_output = os.path.join(out_dir, f"{asset_name}.png")
    yy_output = os.path.join(out_dir, f"{asset_name}.yy")
    return image_output, yy_output


def create_composite_font_sheet(
    images: list[Image.Image],
    keys: list[str],
    size: int,
    override_char_codes: dict[str, int] | None = None,
):
    override_char_codes = override_char_codes or {}

    # GMFont glyph codepoints should be BMP-only.
    GM_FONT_MAX_CODEPOINT = 0xFFFF

    items: list[tuple[Image.Image, str]] = []
    for img, key in zip(images, keys):
        if _is_single_codepoint_emoji(key):
            if ord(key) <= GM_FONT_MAX_CODEPOINT:
                items.append((img, key))
            continue

        if key in override_char_codes and int(override_char_codes[key]) <= GM_FONT_MAX_CODEPOINT:
            items.append((img, key))

    total_count = len(items)
    cols, rows = get_grid_layout(max(total_count, 1))
    sheet_width = cols * (size + PADDING * 2)
    sheet_height = rows * (size + PADDING * 2)
    composite_sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))
    glyph_data: dict[str, dict] = {}

    if FONT_INCLUDE_SPACE:
        glyph_data["32"] = {
            "character": 32,
            "h": size + (PADDING * 2),
            "offset": 0,
            "shift": max(1, size // 2),
            "w": 0,
            "x": 0,
            "y": 0,
        }

    for index, (image, key) in enumerate(items):
        if image is None:
            continue

        ord_value = override_char_codes.get(key)
        if ord_value is None:
            ord_value = ord(key)

        if int(ord_value) > GM_FONT_MAX_CODEPOINT:
            continue

        if str(ord_value) in glyph_data:
            continue

        resized_img = _cull_alpha_lr(_fit_image_to_square(image, size))

        col = index % cols
        row = index // cols
        x_pos = col * (size + PADDING * 2) + PADDING
        y_pos = row * (size + PADDING * 2) + PADDING

        composite_sheet.paste(resized_img, (x_pos, y_pos), mask=resized_img)

        w, h = resized_img.size
        glyph_data[str(ord_value)] = {
            "character": ord_value,
            "h": h + (PADDING * 2),
            "offset": 0,
            "shift": w,
            "w": w + (PADDING * 2),
            "x": x_pos - PADDING,
            "y": y_pos - PADDING,
        }

    return composite_sheet, cols, rows, total_count, glyph_data


def save_font_yy_file(
    path: str,
    asset_name: str,
    glyph_data: dict,
    size: int,
    *,
    face_name: str = "Segoe UI Emoji",
    parent: dict | None = None,
) -> None:
    glyph_indexes = sorted(int(k) for k in glyph_data.keys())
    lines: list[str] = []
    for i in range(0, len(glyph_indexes), 40):
        lines.append(" ".join(str(idx) for idx in glyph_indexes[i : i + 40]))
    glyph_list_string = "\n".join(lines)

    grouped = []
    for _, group in itertools.groupby(enumerate(glyph_indexes), lambda x: x[1] - x[0]):
        group = list(group)
        start = group[0][1]
        end = group[-1][1]
        grouped.append({"lower": start, "upper": end})

    yy_data = {
        "$GMFont": "",
        "%Name": asset_name,
        "AntiAlias": 1,
        "applyKerning": 0,
        "ascender": size,
        "ascenderOffset": 0,
        "bold": False,
        "canGenerateBitmap": True,
        "charset": 0,
        "first": 0,
        # GameMaker treats `fontName` as a system font face name in the editor.
        # If we put a non-existent face here (like the resource name), it tends to
        # fall back to a default (often Consolas), which is confusing.
        "fontName": face_name,
        "glyphOperations": 0,
        "glyphs": glyph_data,
        "hinting": 0,
        "includeTTF": False,
        "interpreter": 0,
        "italic": False,
        "kerningPairs": [],
        "last": 0,
        "lineHeight": size,
        "maintainGms1Font": False,
        "name": asset_name,
        "parent": parent or {"name": "Emobble", "path": "Emobble.yyp"},
        "pointRounding": 0,
        "ranges": grouped,
        "regenerateBitmap": False,
        "resourceType": "GMFont",
        "resourceVersion": "2.0",
        "sampleText": glyph_list_string,
        "sdfSpread": 8,
        "size": float(size),
        "styleName": "Regular",
        "tags": _tags_for_font_size(size),
        "textureGroupId": {"name": "Default", "path": "texturegroups/Default"},
        "TTFName": "",
        "usesSDF": False,
    }
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(yy_data, f, ensure_ascii=False, indent=4)


def generate_font_sheet(
    set_name: str,
    images: list[Image.Image],
    keys: list[str],
    size: int,
    fonts_out_dir: str,
    promote_micro_sequences: bool = True,
):
    image_path, yy_path = get_font_output_paths(set_name, size, fonts_out_dir=fonts_out_dir)
    slug = _to_asset_slug(set_name)
    asset_name = f"fnt_{slug}_{size}"
    parent = _parent_for_set_size(slug, size)

    # If outputs already exist, we still want to be able to update the .yy schema
    # (e.g., font face name) without re-packing the atlas image.
    if os.path.exists(image_path) and os.path.exists(yy_path):
        try:
            existing = json.loads(Path(yy_path).read_text(encoding="utf-8"))

            existing_glyphs = existing.get("glyphs") or {}
            try:
                existing_keys = [int(k) for k in existing_glyphs.keys()]
            except Exception:
                existing_keys = []
            if any(k > 0xFFFF for k in existing_keys):
                log.info(f"♻️ Regenerating GMFont '{asset_name}' to drop non-BMP glyphs (> 0xFFFF).")
                raise RuntimeError("existing font contains non-BMP glyphs")

            existing["%Name"] = asset_name
            existing["name"] = asset_name
            existing["fontName"] = "Segoe UI Emoji"
            existing["size"] = float(size)
            existing["parent"] = parent
            existing["tags"] = _tags_for_font_size(size)
            Path(yy_path).write_text(json.dumps(existing, ensure_ascii=False, indent=4), encoding="utf-8", newline="\n")
            log.debug(f"Updated {yy_path}")
        except Exception:
            # Fall back to full regeneration below if the existing file isn't readable.
            pass
        else:
            return

    overrides = _build_micro_sequence_font_overrides(keys) if promote_micro_sequences else {}
    composite_sheet, _cols, _rows, _total_count, glyph_data = create_composite_font_sheet(
        images,
        keys,
        size,
        override_char_codes=overrides,
    )

    if len(glyph_data) <= (1 if FONT_INCLUDE_SPACE else 0):
        log.info(f"ℹ️ No glyphs for '{set_name}' at {size}px; skipping font.")
        return

    composite_sheet.save(image_path)
    save_font_yy_file(yy_path, asset_name, glyph_data, size, parent=parent)
    promoted = len(overrides)
    if promoted:
        log.info(f"✅ Generated GMFont '{asset_name}' with {len(glyph_data)} glyphs (promoted micro sequences: {promoted}).")
    else:
        log.info(f"✅ Generated GMFont '{asset_name}' with {len(glyph_data)} glyphs.")


def _estimate_initial_atlas_size(images: list[Image.Image], padding: int) -> int:
    total_area = 0
    for img in images:
        w = img.width + padding * 2
        h = img.height + padding * 2
        total_area += w * h
    return int(math.ceil(math.sqrt(total_area))) if total_area else 64


def _pack_variant_images(images: list[Image.Image], keys: list[str], padding: int = 1):
    assert len(images) == len(keys)
    sortable = sorted(zip(images, keys), key=lambda pair: pair[0].width * pair[0].height, reverse=True)
    sorted_images, sorted_keys = zip(*sortable) if sortable else ([], [])
    if not sorted_images:
        return None, {}

    atlas_size = max(64, _estimate_initial_atlas_size(list(sorted_images), padding))

    while True:
        atlas = Image.new("RGBA", (atlas_size, atlas_size), (0, 0, 0, 0))
        meta: dict[str, dict[str, int]] = {}
        placement: list[tuple[Image.Image, str, int, int]] = []
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

            px = x + padding
            py = y + padding
            placement.append((image, key, px, py))
            meta[key] = {"x": px, "y": py, "w": image.width, "h": image.height}

            x += padded_w
            row_height = max(row_height, padded_h)

        if success:
            for image, _key, px, py in placement:
                atlas.paste(image, (px, py), mask=image)
            return atlas, meta

        atlas_size += 1


def generate_variant_atlas(
    set_name: str,
    images: list[Image.Image],
    keys: list[str],
    size: int,
    sprites_out_dir: str,
    skip_keys: set[str] | None = None,
):
    skip_keys = skip_keys or set()
    slug = _to_asset_slug(set_name)
    sprite_asset_name = f"spr_{slug}_{size}"

    # IMPORTANT: Do not generate intermediate set folders like:
    #   output/sprites/<set>/<size>/...
    # Instead, write directly into the GameMaker sprite folder:
    #   output/sprites/spr_<set>_<size>/spr_<set>_<size>.png
    out_dir = os.path.join(sprites_out_dir, sprite_asset_name)
    os.makedirs(out_dir, exist_ok=True)
    png_out = os.path.join(out_dir, f"{sprite_asset_name}.png")
    json_out = os.path.join(out_dir, f"{sprite_asset_name}.json")

    # Sprites/atlases are intended to cover non-BMP emoji (and sequences that include non-BMP codepoints).
    # BMP-only emoji should be handled by GMFonts/fallback fonts.
    items = [
        (img, key)
        for img, key in zip(images, keys)
        if isinstance(key, str) and key not in skip_keys and _has_non_bmp_codepoint(key)
    ]
    if not items:
        return False

    atlas_images: list[Image.Image] = []
    atlas_keys: list[str] = []
    for img, key in items:
        try:
            atlas_images.append(_cull_alpha_lr(_fit_image_to_square(img, size)))
            atlas_keys.append(key)
        except OSError as e:
            log.warning(f"⚠️ Skipping broken PNG for '{set_name}' size {size} key '{key}': {e}")
        except Exception as e:
            log.warning(
                f"⚠️ Skipping unreadable PNG for '{set_name}' size {size} key '{key}': {type(e).__name__}: {e}"
            )

    if not atlas_images:
        log.warning(f"⚠️ No valid variant images for '{set_name}' size {size}; skipping atlas.")
        return False

    atlas, meta = _pack_variant_images(atlas_images, atlas_keys, padding=PADDING)
    if atlas is None:
        return False

    # IMPORTANT:
    # Do NOT crop using `atlas.getbbox()` (alpha bbox). Many emoji PNGs include
    # transparent padding within the square, which can cause the alpha bbox to start
    # below/after the placement padding. Cropping to that bbox would then shift
    # metadata into negative coordinates (e.g. y = -1).
    if meta:
        min_x = min(v["x"] for v in meta.values())
        min_y = min(v["y"] for v in meta.values())
        max_x = max(v["x"] + v["w"] for v in meta.values())
        max_y = max(v["y"] + v["h"] for v in meta.values())

        left = max(0, min_x - PADDING)
        top = max(0, min_y - PADDING)
        right = min(atlas.width, max_x + PADDING)
        bottom = min(atlas.height, max_y + PADDING)

        if left or top or right != atlas.width or bottom != atlas.height:
            atlas = atlas.crop((left, top, right, bottom))
            for v in meta.values():
                v["x"] -= left
                v["y"] -= top

    atlas.save(png_out)
    with open(json_out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, ensure_ascii=False)

    # Also emit a real GameMaker sprite resource for runtime lookup scripts.
    # The resource is a single-frame sprite whose texture is the atlas itself.
    try:
        parent = _parent_for_set_size(slug, size)
        save_sprite_resource_from_atlas(
            sprite_name=sprite_asset_name,
            atlas_png_path=png_out,
            sprites_out_dir=sprites_out_dir,
            parent=parent,
        )
    except Exception as e:
        log.warning(f"⚠️ Failed to write GameMaker sprite resource for '{sprite_asset_name}': {type(e).__name__}: {e}")

    log.info(f"✅ Generated variant atlas '{sprite_asset_name}' ({len(meta)} entries)")
    return True


def generate_emobble_fonts_and_variant_atlases(
    png_dir: str,
    fonts_out_dir: str,
    sprites_out_dir: str,
    promote_micro_sequences: bool = True,
):
    os.makedirs(fonts_out_dir, exist_ok=True)
    os.makedirs(sprites_out_dir, exist_ok=True)

    seen_slugs: set[str] = set()

    for set_name in os.listdir(png_dir):
        set_path = os.path.join(png_dir, set_name)
        if not os.path.isdir(set_path):
            continue

        slug = _to_asset_slug(set_name)
        if slug in seen_slugs:
            log.warning(f"⚠️ Skipping duplicate PNG set folder '{set_name}' (slug '{slug}' already processed)")
            continue
        seen_slugs.add(slug)

        images, keys = load_png_images(set_name, png_dir=png_dir)
        if not images or not keys:
            continue

        images, keys = sort_emojis_by_key(images, keys)
        micro_overrides = _build_micro_sequence_font_overrides(keys) if promote_micro_sequences else {}

        for size in EMOBBLE_FONT_SIZES:
            generate_font_sheet(
                set_name,
                images,
                keys,
                size,
                fonts_out_dir=fonts_out_dir,
                promote_micro_sequences=promote_micro_sequences,
            )

        for size in EMOBBLE_ATLAS_SIZES:
            generate_variant_atlas(
                set_name,
                images,
                keys,
                size,
                sprites_out_dir=sprites_out_dir,
                skip_keys=set(micro_overrides.keys()) if promote_micro_sequences else set(),
            )

    log.info("🎉 Emobble font/atlas generation complete!")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build GMFonts + sprite atlases into the output folder.")
    parser.add_argument("--output", default=str(TOOLS_ROOT / "output"), help="Output directory root")
    parser.add_argument("--clean", action="store_true", help="Delete output/fonts and output/sprites before writing")
    parser.add_argument("--pngs", default=None, help="Override PNG source directory")
    parser.add_argument(
        "--promote-micro-sequences",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="If enabled, promote certain micro emoji sequences (VS16/keycaps) into the font when the base codepoint slot is free.",
    )
    args = parser.parse_args(argv)

    out = output_paths(args.output)
    ensure_output_dirs(out)

    if args.clean:
        import shutil

        if out.fonts.exists():
            shutil.rmtree(out.fonts)
        if out.sprites.exists():
            shutil.rmtree(out.sprites)
        out.fonts.mkdir(parents=True, exist_ok=True)
        out.sprites.mkdir(parents=True, exist_ok=True)

    png_dir = Path(args.pngs) if args.pngs else default_png_source_dir()
    if not png_dir.exists():
        print(f"❌ Missing PNG directory: {png_dir}")
        return 1

    print(f"🔨 Building fonts+atlases from: {png_dir}")
    generate_emobble_fonts_and_variant_atlases(
        png_dir=str(png_dir),
        fonts_out_dir=str(out.fonts),
        sprites_out_dir=str(out.sprites),
        promote_micro_sequences=bool(args.promote_micro_sequences),
    )

    print("✅ Atlas build complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
