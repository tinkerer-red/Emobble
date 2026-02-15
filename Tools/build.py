from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
import shutil
from datetime import datetime
import re

# Make `src/` importable when running from Tools/
TOOLS_ROOT = Path(__file__).resolve().parent


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


def ensure_output_has_yyp(output_root: Path) -> Path:
    """Ensure output_root contains a .yyp so GameMaker can import .yy resources from it.

    GameMaker's resource importer expects the resource file to belong to a project
    (i.e., a parent directory containing a .yyp). Without it, it shows:
    "Could not find a project for the resource file".
    """
    # Our generated .yy resources use parent.path == "Emobble.yyp".
    # GameMaker's importer appears to validate that file name when importing.
    # So we always ensure `Emobble.yyp` exists in the output root.
    yyp_path = output_root / "Emobble.yyp"
    if yyp_path.exists():
        return yyp_path

    name = "Emobble"
    yyp_path.write_text(
        "{\n"
        "  \"$GMProject\":\"v1\",\n"
        f"  \"%Name\":\"{name}\",\n"
        "  \"AudioGroups\":[\n"
        "    {\"$GMAudioGroup\":\"v1\",\"%Name\":\"audiogroup_default\",\"exportDir\":\"\",\"name\":\"audiogroup_default\",\"resourceType\":\"GMAudioGroup\",\"resourceVersion\":\"2.0\",\"targets\":-1,}\n"
        "  ],\n"
        "  \"Folders\":[],\n"
        "  \"resources\":[],\n"
        "  \"resourceType\":\"GMProject\",\n"
        "  \"resourceVersion\":\"2.0\",\n"
        "  \"defaultScriptType\":1\n"
        "}\n",
        encoding="utf-8",
        newline="\n",
    )
    return yyp_path


def cleanup_output_sprite_intermediates(sprites_root: Path) -> None:
    """Remove build intermediates that should not persist in output.

    We keep GameMaker-required sprite files (.yy + GUID frame/layer PNGs), but remove:
      - sprites/<spr>/<spr>.png  (atlas convenience copy)
      - sprites/<spr>/<spr>.json (variant rect metadata)
    """

    if not sprites_root.exists():
        return

    spr_dir_re = re.compile(r"^spr_[a-zA-Z0-9]+_\d+$")
    for spr_dir in sprites_root.iterdir():
        if not spr_dir.is_dir():
            continue
        if not spr_dir_re.fullmatch(spr_dir.name):
            continue

        for ext in (".png", ".json"):
            p = spr_dir / f"{spr_dir.name}{ext}"
            if p.exists():
                try:
                    p.unlink()
                except Exception:
                    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full Emobble asset pipeline end-to-end.")
    parser.add_argument("--output", default=str(TOOLS_ROOT / "output"), help="Output directory root")
    parser.add_argument("--clean", action="store_true", help="Delete output directory before building")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Back up PNG inputs to temp/ and delete current db/ + generated Assets/ outputs",
    )
    parser.add_argument("--skip-scrape", action="store_true")
    parser.add_argument("--skip-cleanup", action="store_true")
    parser.add_argument("--skip-atlas", action="store_true")
    parser.add_argument("--skip-gml", action="store_true")
    parser.add_argument(
        "--keep-intermediates",
        action="store_true",
        help="Keep intermediate sprite atlas .png/.json files in output/ (useful for debugging).",
    )

    parser.add_argument(
        "--promote-micro-sequences",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="If enabled, promote certain micro emoji sequences (VS16/keycaps) into the font when the base codepoint slot is free.",
    )

    # Pass-through scrape options (so build can be a real end-to-end run).
    parser.add_argument(
        "--sets",
        default=None,
        help=(
            "Comma-separated sets to download during scrape stage. "
            "If omitted, scrape.py uses its default sets. "
            "If provided, ONLY those sets are downloaded. Use 'none' to skip images."
        ),
    )
    # Legacy passthrough flags (hidden)
    parser.add_argument("--with-image", "--with-images", dest="with_images", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--emojipedia-vendors", dest="emojipedia_vendors", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--all-locales", action="store_true", help="Scrape all locales (emojibase data/shortcodes)")
    parser.add_argument(
        "--locales",
        default="en",
        help="Comma-separated locales when not using --all-locales (default: en)",
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=0.2,
        help="Delay between scrape requests (default: 0.2)",
    )
    parser.add_argument(
        "--image-limit",
        type=int,
        default=0,
        help="Limit image downloads for testing (0 = no limit)",
    )
    args = parser.parse_args()

    print(f"🐍 Python: {sys.executable}")
    effective_sets = str(args.sets) if args.sets is not None else "twemoji,google,noto-emoji,microsoft-windows-10,microsoft-fluent-flat,microsoft-3D-fluent,openmoji,emojidex,icons8"
    likely_emojipedia = any(s.strip() and s.strip().lower() not in ("none", "twemoji", "twitter") for s in effective_sets.split(","))
    if likely_emojipedia and not str(sys.executable).lower().replace("\\", "/").endswith("/tools/.venv/scripts/python.exe"):
        venv_py = TOOLS_ROOT / ".venv" / "Scripts" / "python.exe"
        if venv_py.exists():
            print("⚠️ You're not running the Tools/.venv Python interpreter.")
            print("   Emojipedia scraping (revisions) requires Playwright + Chromium installed in THIS Python env.")
            print(f"   Recommended: {venv_py} build.py --fresh --clean --all-locales")

    if args.fresh and args.skip_scrape:
        print("❌ Cannot use --fresh with --skip-scrape.")
        print("   --fresh deletes db/ (including db/Data/*.json), but --skip-scrape prevents re-downloading it.")
        print("   Remove --skip-scrape, or remove --fresh.")
        return 2

    if args.fresh:
        root = TOOLS_ROOT
        assets_dir = root / "Assets"
        pngs_dir = assets_dir / "PNGs"

        temp_root = root / "temp" / "manual_pngs"
        temp_root.mkdir(parents=True, exist_ok=True)
        manual_pngs = temp_root / "PNGs"

        # If there are existing PNGs, move them into temp/manual_pngs/PNGs (keep a timestamped backup if needed).
        if pngs_dir.exists() and any(pngs_dir.iterdir()):
            if manual_pngs.exists() and any(manual_pngs.iterdir()):
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup = temp_root / f"PNGs_backup_{stamp}"
                shutil.move(str(manual_pngs), str(backup))
            shutil.move(str(pngs_dir), str(manual_pngs))

        # Wipe DB (will be re-scraped)
        db_dir = root / "db"
        if db_dir.exists():
            shutil.rmtree(db_dir)
        db_dir.mkdir(parents=True, exist_ok=True)

        # Wipe generated asset outputs (keep Assets/Fonts)
        for rel in [
            Path("Assets") / "Atlases",
            Path("Assets") / "Sprites",
            Path("Assets") / "Texture Sheets",
            Path("Assets") / "PNGs_Clean",
        ]:
            p = root / rel
            if p.exists():
                shutil.rmtree(p)

        # Optionally wipe output directory (regenerated)
        out_dir = Path(args.output)
        if out_dir.exists():
            shutil.rmtree(out_dir)

    out = output_paths(args.output)
    ensure_output_dirs(out, clean=args.clean)

    # Make output importable by GameMaker (it requires a parent .yyp for .yy imports).
    yyp_path = ensure_output_has_yyp(out.root)
    print(f"ℹ️ GameMaker import root: {yyp_path}")

    if not args.skip_scrape:
        import scrape

        print("▶ Stage: scrape")

        scrape_argv = [
            "--output",
            str(out.root),
            "--request-delay",
            str(float(args.request_delay)),
        ]
        if args.sets is not None:
            scrape_argv.extend(["--sets", str(args.sets)])
        elif getattr(args, "with_images", None) is not None:
            scrape_argv.extend(["--with-images", str(getattr(args, "with_images"))])
        if args.all_locales:
            scrape_argv.append("--all-locales")
        else:
            scrape_argv.extend(["--locales", str(args.locales)])
        if getattr(args, "emojipedia_vendors", None):
            scrape_argv.extend(["--emojipedia-vendors", str(getattr(args, "emojipedia_vendors"))])
        if int(args.image_limit) > 0:
            scrape_argv.extend(["--image-limit", str(int(args.image_limit))])

        if scrape.main(scrape_argv) != 0:
            return 1

    if not args.skip_cleanup:
        import cleanup

        print("▶ Stage: cleanup")
        cleanup_argv = ["--output", str(out.root)]
        if args.clean:
            cleanup_argv.append("--clean-dest")

        # If we didn't scrape this run, emojibase data may be absent. In that case,
        # don't fail the build just because db/pruned_emoji.json can't be rebuilt.
        if args.skip_scrape:
            en_compact = TOOLS_ROOT / "db" / "Data" / "en.json"
            if not en_compact.exists():
                print(f"ℹ️ Missing emojibase data ({en_compact}); running cleanup with --skip-db")
                cleanup_argv.append("--skip-db")

        if cleanup.main(cleanup_argv) != 0:
            return 1

    if not args.skip_atlas:
        import build_atlas

        print("▶ Stage: build_atlas")
        atlas_argv = ["--output", str(out.root)]
        if args.clean:
            atlas_argv.append("--clean")
        atlas_argv.append(f"--{'promote' if args.promote_micro_sequences else 'no-promote'}-micro-sequences")
        if build_atlas.main(atlas_argv) != 0:
            return 1

    if not args.skip_gml:
        import build_gml

        print("▶ Stage: build_gml")
        if build_gml.main(["--output", str(out.root)]) != 0:
            return 1

    # Emit copy/paste snippets for integrating output into a real project.
    try:
        import build_copy_snippets

        print("▶ Stage: build_copy_snippets")
        if build_copy_snippets.main(["--output", str(out.root)]) != 0:
            return 1
    except Exception as e:
        print(f"⚠️ Skipping copy snippet generation: {type(e).__name__}: {e}")

    if not args.keep_intermediates:
        cleanup_output_sprite_intermediates(out.sprites)

    # Ensure the project file still exists at the end (some stages may clean output subfolders).
    ensure_output_has_yyp(out.root)

    print(f"✅ Build complete: {out.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
