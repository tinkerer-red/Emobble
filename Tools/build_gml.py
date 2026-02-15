from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import re
from pathlib import Path
import shutil

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


def _script_parent_for_name(script_name: str) -> tuple[str, str]:
    """Return (parent_name, parent_path) for a script resource.

    We follow the requested hierarchy when possible:
      type/size/(asset type isn't a folder)

    For variant lookup scripts named like `__lt_<set>_<size>`,
    we put them under folders/_Libraries/Emobble/<set>/<set>_<size>.yy.
    All other scripts attach to project root.
    """
    m = re.fullmatch(r"__lt_([a-zA-Z0-9]+)_(\d+)", script_name)
    if not m:
        return ("Emobble", "Emobble.yyp")
    set_slug = m.group(1)
    size = m.group(2)
    folder_name = f"{set_slug}_{size}"
    return (folder_name, f"folders/_Libraries/Emobble/{set_slug}/{folder_name}.yy")


def _write_gmscript_resource(script_name: str, gml_source: str, scripts_root: Path) -> None:
    out_dir = scripts_root / script_name
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / f"{script_name}.gml").write_text(gml_source, encoding="utf-8", newline="\n")

    parent_name, parent_path = _script_parent_for_name(script_name)
    yy = {
        "$GMScript": "v1",
        "%Name": script_name,
        "isCompatibility": False,
        "isDnD": False,
        "name": script_name,
        "parent": {"name": parent_name, "path": parent_path},
        "resourceType": "GMScript",
        "resourceVersion": "2.0",
    }
    (out_dir / f"{script_name}.yy").write_text(
        json.dumps(yy, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )


# -------------------------------------------------------------------------------------------------
# Variant lookup script writer (was src/emobble_pipeline/gml_variants.py)
# -------------------------------------------------------------------------------------------------


def _to_asset_slug(name: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9 ]+", "", str(name))
    parts = clean.strip().split()
    if not parts:
        return ""
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


def _generate_variant_lookup_gml(set_name: str, size: int, sprite_asset_name: str, key_metadata: dict) -> str:
    raw_json = json.dumps(key_metadata, ensure_ascii=True, separators=(",", ":"))
    escaped_json = raw_json.replace("\\", "\\\\").replace('"', '\\"')

    # The lookup function name is intentionally short and stable.
    # It must match the script asset name.
    fn_name = f"__lt_{set_name}_{size}"
    return (
        f"// This is a generated file from `build_gml.py` — do not modify.\n"
        f"/// @ignore\n"
        f"function {fn_name}() {{\n"
        f"\tstatic __ = json_parse(\"{escaped_json}\");\n"
        f"\treturn __;\n"
        f"}}\n"
    )


def write_variant_lookup_scripts(sprites_root: Path, scripts_out: Path) -> int:
    count = 0
    for json_path in sprites_root.rglob("spr_*_*.json"):
        try:
            meta = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        sprite_asset_name = json_path.stem

        # Current layout writes variant metadata alongside the sprite resource:
        #   sprites/spr_<set>_<size>/spr_<set>_<size>.json
        # So infer set+size from the filename rather than directory names.
        m = re.fullmatch(r"spr_([a-zA-Z0-9]+)_(\d+)", sprite_asset_name)
        if not m:
            continue
        set_name = m.group(1)
        size = int(m.group(2))

        # Script asset name matches the runtime function name.
        script_name = f"__lt_{set_name}_{size}"
        gml = _generate_variant_lookup_gml(set_name=set_name, size=size, sprite_asset_name=sprite_asset_name, key_metadata=meta)
        _write_gmscript_resource(script_name, gml, scripts_out)
        count += 1
    return count


# -------------------------------------------------------------------------------------------------
# emobble_get_ord generator (was src/generate_ord_map_and_get_ord_gml.py)
# -------------------------------------------------------------------------------------------------


def _normalize_name(name: str) -> str:
    name = str(name).strip().lower()
    name = name.replace(" ", "_").replace("-", "_")
    name = re.sub(r"[^a-z0-9_]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


def _build_name_to_ord_map(emoji_db: dict) -> dict[str, int]:
    candidates: dict[str, list[tuple[str, bool]]] = {}

    for emoji, meta in emoji_db.items():
        if not (isinstance(emoji, str) and len(emoji) == 1):
            continue
        canonical_raw = (meta or {}).get("name") or ""
        canonical_norm = _normalize_name(canonical_raw) if canonical_raw else ""

        names: list[str] = []
        if (meta or {}).get("name"):
            names.append(str(meta["name"]))
        for alias in (meta or {}).get("aliases") or []:
            names.append(str(alias))

        for raw in set(names):
            norm = _normalize_name(raw)
            if not norm:
                continue
            is_canonical_for_name = (norm == canonical_norm) and bool(canonical_norm)
            candidates.setdefault(norm, []).append((emoji, is_canonical_for_name))

    out: dict[str, int] = {}
    for norm_name, items in candidates.items():
        if len(items) == 1:
            emoji, _ = items[0]
            out[norm_name] = ord(emoji)
            continue
        canonical_items = [it for it in items if it[1]]
        if len(canonical_items) == 1:
            emoji, _ = canonical_items[0]
            out[norm_name] = ord(emoji)
    return out


def _build_name_to_emoji_map(emoji_db: dict) -> dict[str, str]:
    """Build a mapping of normalized names/aliases -> emoji string.

    Unlike `_build_name_to_ord_map`, this includes multi-codepoint sequences
    (ZWJ, VS16, skin tone modifiers, etc.) since those are needed for atlas lookup.
    """

    candidates: dict[str, list[tuple[str, bool]]] = {}

    for emoji, meta in emoji_db.items():
        if not isinstance(emoji, str) or not emoji:
            continue
        canonical_raw = (meta or {}).get("name") or ""
        canonical_norm = _normalize_name(canonical_raw) if canonical_raw else ""

        names: list[str] = []
        if (meta or {}).get("name"):
            names.append(str(meta["name"]))
        for alias in (meta or {}).get("aliases") or []:
            names.append(str(alias))

        for raw in set(names):
            norm = _normalize_name(raw)
            if not norm:
                continue
            is_canonical_for_name = (norm == canonical_norm) and bool(canonical_norm)
            candidates.setdefault(norm, []).append((emoji, is_canonical_for_name))

    out: dict[str, str] = {}
    for norm_name, items in candidates.items():
        if len(items) == 1:
            emoji, _ = items[0]
            out[norm_name] = emoji
            continue
        canonical_items = [it for it in items if it[1]]
        if len(canonical_items) == 1:
            emoji, _ = canonical_items[0]
            out[norm_name] = emoji
    return out


def _escape_for_gml(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def write_get_ord_gml(scripts_root: Path) -> None:
    db_file = project_root() / "db" / "pruned_emoji.json"
    if not db_file.exists():
        raise FileNotFoundError(f"Missing DB file: {db_file}")
    emoji_db = json.loads(db_file.read_text(encoding="utf-8"))
    name_to_ord = _build_name_to_ord_map(emoji_db)
    json_blob = json.dumps(name_to_ord, ensure_ascii=True, separators=(",", ":"))
    escaped = _escape_for_gml(json_blob)

    gml = (
        "// This is a generated file from `build_gml.py` — do not modify.\n"
        "function emobble_get_ord(_name) {\n"
        "\tif (is_undefined(_name)) return -1;\n"
        "\tstatic __map = json_parse(\"{escaped}\");\n"
        "\tvar key = string_lower(string(_name));\n"
        "\tkey = string_replace_all(key, \" \", \"_\");\n"
        "\tkey = string_replace_all(key, \"-\", \"_\");\n"
        "\tif (variable_struct_exists(__map, key)) return __map[$ key];\n"
        "\treturn -1;\n"
        "}\n"
    )
    _write_gmscript_resource("emobble_get_ord", gml, scripts_root)


def write_get_emoji_gml(scripts_root: Path) -> None:
    db_file = project_root() / "db" / "pruned_emoji.json"
    if not db_file.exists():
        raise FileNotFoundError(f"Missing DB file: {db_file}")
    emoji_db = json.loads(db_file.read_text(encoding="utf-8"))
    name_to_emoji = _build_name_to_emoji_map(emoji_db)
    json_blob = json.dumps(name_to_emoji, ensure_ascii=True, separators=(",", ":"))
    escaped = _escape_for_gml(json_blob)

    gml = (
        "// This is a generated file from `build_gml.py` — do not modify.\n"
        "function emobble_get_emoji(_name) {\n"
        f"\tstatic __map = json_parse(\"{escaped}\");\n"
        "\tvar key = string_lower(_name);\n"
        "\tkey = string_replace_all(key, \" \", \"_\");\n"
        "\tkey = string_replace_all(key, \"-\", \"_\");\n"
        "\treturn __map[$ key] ?? \"\";\n"
        "}\n"
    )
    _write_gmscript_resource("emobble_get_emoji", gml, scripts_root)


def _write_emobble_font_has_glyph(scripts_root: Path) -> None:
    gml = (
        "// This is a generated file from `build_gml.py` — do not modify.\n"
        "function __emobble_font_has_glyph(_font, _chr) {\n"
        "\tstatic __cache = {};\n"
        "\t\n"
        "\tvar _font_name = font_get_name(_font);\n"
        "\t\n"
        "\tvar _glyphs = __cache[$ _font_name];\n"
        "\tif (_glyphs == undefined) {\n"
        "\t\tvar _info = font_get_info(_font);\n"
        "\t\t_glyphs = _info.glyphs;\n"
        "\t\t__cache[$ _font_name] = _glyphs;\n"
        "\t}\n"
        "\t\n"
        "\treturn (_glyphs[$ _chr] != undefined);\n"
        "}\n"
    )
    _write_gmscript_resource("emobble_font_has_glyph", gml, scripts_root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build all runtime GML scripts into output/scripts.")
    parser.add_argument("--output", default=str(TOOLS_ROOT / "output"), help="Output directory root")
    args = parser.parse_args(argv)

    out = output_paths(args.output)
    ensure_output_dirs(out)

    # Clean scripts dir so we don't accumulate stale folders.
    ensure_clean_dir(out.scripts)

    # Name -> emoji string (includes ZWJ sequences for atlas lookup)
    write_get_emoji_gml(out.scripts)

    # Name -> codepoint (single-codepoint emoji only; kept for compatibility)
    write_get_ord_gml(out.scripts)

    # 2) emobble_font_has_glyph
    _write_emobble_font_has_glyph(out.scripts)

    # 3) variant lookup scripts from atlas metadata
    variant_count = write_variant_lookup_scripts(out.sprites, out.scripts)

    print(f"✅ Wrote scripts to: {out.scripts} (variants: {variant_count})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
