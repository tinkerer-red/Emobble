from __future__ import annotations

from pathlib import Path

from PIL import Image


def main() -> int:
    base = Path(__file__).resolve().parent / "output" / "fonts"
    rels = [
        "fnt_emojidex_16/fnt_emojidex_16.png",
        "fnt_twemoji_16/fnt_twemoji_16.png",
        "fnt_openmoji_16/fnt_openmoji_16.png",
        "fnt_googleNoto_16/fnt_googleNoto_16.png",
        "fnt_microsoftWindows10_16/fnt_microsoftWindows10_16.png",
        "fnt_twemoji_64/fnt_twemoji_64.png",
    ]

    for rel in rels:
        path = base / rel
        if not path.exists():
            print(f"MISSING {path}")
            continue

        with Image.open(path) as im:
            width, height = im.size

        megabytes = path.stat().st_size / 1024 / 1024
        print(f"{rel}: {width}x{height}  {megabytes:.2f} MB")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
