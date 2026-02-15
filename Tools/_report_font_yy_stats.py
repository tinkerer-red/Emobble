from __future__ import annotations

import json
from pathlib import Path


def font_stats(yy_path: Path) -> tuple[int, int, int]:
    data = json.loads(yy_path.read_text(encoding="utf-8"))
    glyphs = data.get("glyphs", {})
    keys = [int(k) for k in glyphs.keys()]
    if not keys:
        return 0, 0, 0
    return len(keys), min(keys), max(keys)


def main() -> int:
    base = Path(__file__).resolve().parent / "output" / "fonts"
    font_dirs = sorted([p for p in base.iterdir() if p.is_dir()])

    for d in font_dirs:
        yy = d / f"{d.name}.yy"
        if not yy.exists():
            continue
        count, min_cp, max_cp = font_stats(yy)
        print(f"{d.name}: glyphs={count} min={min_cp} max={max_cp}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
