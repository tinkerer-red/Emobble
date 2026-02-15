from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from PIL import Image

TOOLS_ROOT = Path(__file__).resolve().parent


def project_root() -> Path:
    return TOOLS_ROOT


def _default_cleanup_source_dir() -> Path:
    """Choose a sensible PNG source directory for cleanup.

    Important: this should prefer *raw* sources (scraped/manual) and must NOT
    default to the cleaned output directory (Assets/PNGs_Clean), otherwise we'd
    end up rewriting files in place.
    """
    root = project_root()

    scraped = root / "db" / "PNGs"
    if scraped.exists():
        return scraped

    # Fall back to manual temp inputs (for fresh runs).
    manual = root / "temp" / "manual_pngs" / "PNGs"
    if manual.exists():
        return manual

    return root / "Assets" / "PNGs"


def _hexcode_to_unicode(hexcode: str) -> str:
    # Accept both '-' and '_' separators.
    parts = str(hexcode).strip().upper().replace("_", "-").split("-")
    chars = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        try:
            chars.append(chr(int(p, 16)))
        except Exception:
            return ""
    return "".join(chars)


def build_pruned_emoji_db(locale: str = "en") -> dict:
    """Build a minimal emoji DB keyed by unicode char/sequence.

    Output schema matches what `generate_ord_map_and_get_ord_gml.py` expects:
    { "😀": {"char":"😀","name":"grinning face","aliases":[],"shortcodes":[...],"emoticons":[]}, ... }
    """
    root = project_root()
    db_dir = root / "db"
    data_path = db_dir / "Data" / f"{locale}.json"
    shortcodes_path = db_dir / "Shortcodes" / f"{locale}.json"

    if not data_path.exists():
        raise FileNotFoundError(f"Missing emojibase compact data: {data_path}")

    data_entries = json.loads(data_path.read_text(encoding="utf-8"))
    shortcodes = {}
    if shortcodes_path.exists():
        shortcodes = json.loads(shortcodes_path.read_text(encoding="utf-8"))

    out: dict[str, dict] = {}

    for entry in data_entries:
        if not isinstance(entry, dict):
            continue
        hexcode = entry.get("hexcode")
        label = entry.get("label") or ""
        unicode_str = entry.get("unicode")

        # Some entries may omit the literal string; derive it.
        if not unicode_str and hexcode:
            unicode_str = _hexcode_to_unicode(hexcode)

        if not unicode_str:
            continue

        sc = []
        if hexcode and isinstance(shortcodes, dict):
            sc_val = shortcodes.get(str(hexcode).upper())
            if isinstance(sc_val, list):
                sc = [str(x) for x in sc_val]
            elif isinstance(sc_val, str):
                sc = [sc_val]

        out[unicode_str] = {
            "char": unicode_str,
            "name": str(label),
            "aliases": [],
            "shortcodes": sc,
            "emoticons": [],
        }

    return out


def write_pruned_outputs(locale: str = "en") -> None:
    root = project_root()
    db_dir = root / "db"
    db_dir.mkdir(parents=True, exist_ok=True)

    pruned = build_pruned_emoji_db(locale=locale)
    (db_dir / "pruned_emoji.json").write_text(
        json.dumps(pruned, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )


def ensure_empty_pruned_db_exists() -> None:
    """Ensure db/pruned_emoji.json exists.

    When running cleanup with --skip-db we don't rebuild the pruned DB, but other
    stages (notably build_gml.py) still expect the file to exist.
    """
    root = project_root()
    db_dir = root / "db"
    db_dir.mkdir(parents=True, exist_ok=True)
    path = db_dir / "pruned_emoji.json"
    if not path.exists():
        path.write_text("{}\n", encoding="utf-8", newline="\n")


def _parse_hex_parts(stem: str) -> list[str]:
    # Accept both '_' and '-' separators.
    raw_parts = stem.replace("-", "_").split("_")
    parts: list[str] = []
    for p in raw_parts:
        p = p.strip().upper()
        if not p:
            continue
        # Pad to 4+ chars: keep existing long codepoints, but pad short ones.
        if all(c in "0123456789ABCDEF" for c in p):
            parts.append(p.zfill(4))
    return parts


def _normalize_png_filename(path: Path) -> Path:
    parts = _parse_hex_parts(path.stem)
    if not parts:
        return path
    new_name = "_".join(parts) + path.suffix.lower()
    return path.with_name(new_name)


def _tight_crop_image(img: Image.Image) -> Image.Image:
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    alpha = img.split()[-1]
    bbox = alpha.getbbox()
    if not bbox:
        return img
    return img.crop(bbox)


def _resize_to_height(img: Image.Image, height: int) -> Image.Image:
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    w, h = img.size
    if w <= 0 or h <= 0:
        return img

    # Resize to a fixed height, preserving aspect ratio.
    # This may upscale small inputs; we do it for consistency.
    if h == int(height):
        return img

    scale = float(height) / float(h)
    new_w = max(1, int(round(w * scale)))
    new_h = int(height)
    return img.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)


def _atomic_replace(path: Path, img: Image.Image) -> None:
    """Write image to a temp file then replace the original path."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    img.save(tmp, optimize=True, compress_level=9)
    tmp.replace(path)


def clean_png_tree_in_place(src_dir: Path, max_height: int, log_every: int = 0) -> tuple[int, int, int]:
    """Cleans PNGs in-place under src_dir.

    Returns: (written, skipped, renamed)
    """
    written = 0
    skipped = 0
    renamed = 0
    processed = 0
    started = time.perf_counter()

    for input_path in src_dir.rglob("*.png"):
        processed += 1
        # Normalize filename (optional rename in-place).
        normalized = _normalize_png_filename(input_path)
        target_path = input_path
        if normalized.name != input_path.name:
            candidate = input_path.with_name(normalized.name)
            # Only rename when it won't clobber an existing different file.
            if not candidate.exists():
                try:
                    input_path.replace(candidate)
                    target_path = candidate
                    renamed += 1
                except Exception:
                    target_path = input_path

        try:
            with Image.open(target_path) as img:
                cropped = _tight_crop_image(img)
                final = _resize_to_height(cropped, height=int(max_height))
            _atomic_replace(target_path, final)
            written += 1
        except Exception:
            skipped += 1

        if int(log_every) > 0 and processed % int(log_every) == 0:
            elapsed = max(0.001, time.perf_counter() - started)
            rate = processed / elapsed
            print(
                f"  … processed {processed:,} PNGs "
                f"({written:,} written, {skipped:,} skipped, {renamed:,} renamed) "
                f"[{rate:,.1f}/s]"
            )

    return written, skipped, renamed


def clean_png_tree(src_dir: Path, dest_dir: Path, max_size: int, log_every: int = 0) -> tuple[int, int]:
    written = 0
    skipped = 0
    processed = 0
    started = time.perf_counter()

    for input_path in src_dir.rglob("*.png"):
        processed += 1
        rel = input_path.relative_to(src_dir)
        normalized_name = _normalize_png_filename(input_path)
        rel = rel.with_name(normalized_name.name)
        out_path = dest_dir / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with Image.open(input_path) as img:
                cropped = _tight_crop_image(img)
                final = _resize_to_height(cropped, height=int(max_size))
                final.save(out_path, optimize=True, compress_level=9)
            written += 1
        except Exception:
            skipped += 1

        if int(log_every) > 0 and processed % int(log_every) == 0:
            elapsed = max(0.001, time.perf_counter() - started)
            rate = processed / elapsed
            print(
                f"  … processed {processed:,} PNGs "
                f"({written:,} written, {skipped:,} skipped) "
                f"[{rate:,.1f}/s]"
            )

    return written, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize data + crop PNG emoji sources.")
    parser.add_argument("--output", default=str(TOOLS_ROOT / "output"), help="Output root (unused)")
    parser.add_argument("--locale", default="en", help="Locale used to build pruned emoji DB (default: en)")
    parser.add_argument("--skip-db", action="store_true", help="Skip building db/pruned_emoji.json")
    parser.add_argument(
        "--src",
        default=str(_default_cleanup_source_dir()),
        help="Source PNG directory",
    )
    parser.add_argument(
        "--dest",
        default=str(project_root() / "Assets" / "PNGs_Clean"),
        help="Destination directory for cleaned PNGs",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=64,
        help="Target emoji PNG height in pixels (default: 64). Images are cropped then resized to this height (aspect ratio preserved).",
    )
    parser.add_argument(
        "--log-every",
        type=int,
        default=1000,
        help="Print progress every N PNGs while cleaning (0 = disable; default: 1000)",
    )
    parser.add_argument("--clean-dest", action="store_true", help="Delete destination directory before writing")
    parser.add_argument(
        "--in-place",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="If enabled (default), edits PNGs in the source directory instead of writing duplicates into --dest.",
    )
    args = parser.parse_args(argv)

    if not args.skip_db:
        try:
            print(f"🧼 Building db/pruned_emoji.json from emojibase ({args.locale})")
            write_pruned_outputs(locale=args.locale)
            print("✅ Wrote db/pruned_emoji.json")
        except Exception as e:
            print(f"❌ Failed building pruned emoji DB: {e}")
            return 1
    else:
        ensure_empty_pruned_db_exists()

    src_dir = Path(args.src)
    dest_dir = Path(args.dest)
    started = time.perf_counter()

    if not src_dir.exists():
        print(f"ℹ️ PNG source dir missing; skipping PNG cleanup: {src_dir}")
        return 0

    if args.in_place:
        print(f"🧹 Cleaning PNGs in-place: {src_dir}")
        written, skipped, renamed = clean_png_tree_in_place(
            src_dir,
            max_height=int(args.max_size),
            log_every=int(args.log_every),
        )
        elapsed = max(0.001, time.perf_counter() - started)
        print(f"✅ Cleaned {written} PNGs ({skipped} skipped, {renamed} renamed) in {elapsed:,.2f}s")
        return 0

    # Copy-mode (optional)
    try:
        same_dir = src_dir.resolve().samefile(dest_dir.resolve())
    except Exception:
        same_dir = str(src_dir.resolve()).lower() == str(dest_dir.resolve()).lower()
    if same_dir:
        print(f"❌ PNG cleanup source and destination are the same directory: {src_dir}")
        print("   Use --in-place (default), or choose a different --dest.")
        return 2

    if args.clean_dest and dest_dir.exists():
        import shutil

        shutil.rmtree(dest_dir)

    print(f"🧹 Cleaning PNGs: {src_dir} -> {dest_dir}")
    written, skipped = clean_png_tree(
        src_dir,
        dest_dir,
        max_size=int(args.max_size),
        log_every=int(args.log_every),
    )
    elapsed = max(0.001, time.perf_counter() - started)
    print(f"✅ Cleaned {written} PNGs ({skipped} skipped) in {elapsed:,.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
