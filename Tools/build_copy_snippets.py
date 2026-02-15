from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ResourceRef:
    name: str
    path: str  # GameMaker-relative path like "sprites/foo/foo.yy"
    parent_path: str | None  # e.g. "folders/twemoji/16.yy"


def _iter_yy_files(root: Path) -> Iterable[Path]:
    yield from root.rglob("*.yy")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_resource_yy(data: dict) -> bool:
    # GM resources are dicts with resourceType and resourceVersion.
    return isinstance(data, dict) and isinstance(data.get("resourceType"), str)


def _discover_resources(output_root: Path) -> list[ResourceRef]:
    resources: list[ResourceRef] = []

    # Only include the well-known resource directories we generate.
    for base in [
        output_root / "fonts",
        output_root / "sprites",
        output_root / "scripts",
    ]:
        if not base.exists():
            continue
        for yy_path in _iter_yy_files(base):
            try:
                data = _load_json(yy_path)
            except Exception:
                continue
            if not _is_resource_yy(data):
                continue

            resource_name = data.get("name") or data.get("%Name")
            if not isinstance(resource_name, str) or not resource_name:
                continue

            # Compute project-relative path from output root.
            rel = yy_path.relative_to(output_root).as_posix()
            parent_path = None
            parent = data.get("parent")
            if isinstance(parent, dict):
                pp = parent.get("path")
                if isinstance(pp, str) and pp:
                    parent_path = pp

            resources.append(ResourceRef(name=resource_name, path=rel, parent_path=parent_path))

    # De-dupe by (name,path)
    uniq: dict[tuple[str, str], ResourceRef] = {}
    for r in resources:
        uniq[(r.name, r.path)] = r
    return sorted(uniq.values(), key=lambda r: (r.path, r.name))


def _folder_parents(folder_path: str) -> list[str]:
    # Input example: "folders/twemoji/16.yy"
    # Output: ["folders/twemoji.yy", "folders/twemoji/16.yy"]
    if not folder_path.startswith("folders/") or not folder_path.endswith(".yy"):
        return []

    rel = folder_path[len("folders/") :]
    if not rel:
        return []

    segs = rel.split("/")
    if not segs:
        return []

    out: list[str] = []
    # For each directory component, add its folder .yy (parents).
    # folders/A/B/C.yy -> folders/A.yy, folders/A/B.yy
    for i in range(0, len(segs) - 1):
        out.append("folders/" + "/".join(segs[: i + 1]) + ".yy")
    # Add the leaf
    out.append(folder_path)
    return out


def _discover_folder_paths(resources: list[ResourceRef]) -> list[str]:
    needed: set[str] = set()
    for r in resources:
        if r.parent_path and r.parent_path.startswith("folders/"):
            for fp in _folder_parents(r.parent_path):
                needed.add(fp)

    # Sort folders by depth then name (parents first)
    return sorted(needed, key=lambda p: (p.count("/"), p.lower()))


def _folder_display_name(folder_yy_path: str) -> str:
    # folders/twemoji/16.yy -> 16
    name = Path(folder_yy_path).stem
    return name


def _folder_parent_path(folder_yy_path: str) -> str | None:
    # folders/twemoji/16.yy -> folders/twemoji.yy
    p = Path(folder_yy_path)
    if p.parent.as_posix() == "folders":
        return None

    # Parent folder file lives one level up and is named by the directory.
    parent_folder_name = p.parent.name
    parent_file = p.parent.parent / f"{parent_folder_name}.yy"
    return parent_file.as_posix().replace("\\", "/")


def _load_relaxed_json(path: Path) -> dict:
    # GameMaker project files allow trailing commas; strip them.
    txt = path.read_text(encoding="utf-8")
    # Remove // comments (snippets may have them)
    txt = re.sub(r"^\s*//.*$", "", txt, flags=re.MULTILINE)
    # Remove trailing commas before } or ]
    txt = re.sub(r",\s*(?=[}\]])", "", txt)
    return json.loads(txt)


def _safe_folder_id_from_path(folder_path: str) -> str:
    # GameMaker appears to treat %Name as an identifier; duplicates can cause weirdness.
    # Use a stable, path-derived id while keeping `name` as the display label.
    # Example: folders/twemoji/16.yy -> folders_twemoji_16
    stem = folder_path
    if stem.endswith(".yy"):
        stem = stem[:-3]
    stem = stem.replace("/", "_")
    stem = re.sub(r"[^A-Za-z0-9_]+", "_", stem)
    stem = re.sub(r"_+", "_", stem).strip("_")
    if not stem:
        stem = "folder"
    return stem


@dataclass(frozen=True)
class ExistingTargets:
    yyp_folder_paths: set[str]
    yyp_resource_paths: set[str]
    ro_folder_paths: set[str]
    ro_resource_paths: set[str]
    ro_max_order: int


def _read_existing_targets(yyp_path: Path | None, resource_order_path: Path | None) -> ExistingTargets:
    yyp_folder_paths: set[str] = set()
    yyp_resource_paths: set[str] = set()
    ro_folder_paths: set[str] = set()
    ro_resource_paths: set[str] = set()
    ro_max_order = 0

    if yyp_path and yyp_path.exists():
        try:
            yyp = _load_relaxed_json(yyp_path)
            folders = yyp.get("Folders")
            if isinstance(folders, list):
                for f in folders:
                    if isinstance(f, dict) and isinstance(f.get("folderPath"), str):
                        yyp_folder_paths.add(f["folderPath"])
            resources = yyp.get("resources")
            if isinstance(resources, list):
                for r in resources:
                    if not isinstance(r, dict):
                        continue
                    rid = r.get("id")
                    if isinstance(rid, dict) and isinstance(rid.get("path"), str):
                        yyp_resource_paths.add(rid["path"])
        except Exception:
            pass

    if resource_order_path and resource_order_path.exists():
        try:
            ro = _load_relaxed_json(resource_order_path)
            fo = ro.get("FolderOrderSettings")
            if isinstance(fo, list):
                for f in fo:
                    if isinstance(f, dict) and isinstance(f.get("path"), str):
                        ro_folder_paths.add(f["path"])
                    if isinstance(f, dict) and isinstance(f.get("order"), int):
                        ro_max_order = max(ro_max_order, int(f["order"]))
            rs = ro.get("ResourceOrderSettings")
            if isinstance(rs, list):
                for r in rs:
                    if isinstance(r, dict) and isinstance(r.get("path"), str):
                        ro_resource_paths.add(r["path"])
                    if isinstance(r, dict) and isinstance(r.get("order"), int):
                        ro_max_order = max(ro_max_order, int(r["order"]))
        except Exception:
            pass

    return ExistingTargets(
        yyp_folder_paths=yyp_folder_paths,
        yyp_resource_paths=yyp_resource_paths,
        ro_folder_paths=ro_folder_paths,
        ro_resource_paths=ro_resource_paths,
        ro_max_order=ro_max_order,
    )


def _write_folder_yy_files(output_root: Path, folder_paths: list[str]) -> None:
    for fp in folder_paths:
        target = output_root / fp
        target.parent.mkdir(parents=True, exist_ok=True)

        parent_path = _folder_parent_path(fp)
        parent = {"name": "Emobble", "path": "Emobble.yyp"} if parent_path is None else {"name": Path(parent_path).stem, "path": parent_path}

        data = {
            "$GMFolder": "",
            # In IDE-authored projects, %Name is human-readable (and appears in the tree).
            "%Name": _folder_display_name(fp),
            "name": _folder_display_name(fp),
            "parent": parent,
            "resourceType": "GMFolder",
            "resourceVersion": "2.0",
        }

        target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def _gm_snippet_line(obj: dict, *, trailing_comma: bool = True) -> str:
    """Render a single JSON object for copy/paste into a JSON array.

    Important: the comma belongs AFTER the object ("},"), not before (",}").
    """

    s = json.dumps(obj, ensure_ascii=False, separators=(", ", ": "))
    return s + ("," if trailing_comma else "")


def _write_copy_into_yyp(output_root: Path, folders: list[str], resources: list[ResourceRef]) -> Path:
    out_path = output_root / "__copy_into_yyp.txt"

    indent = "    "

    # NOTE: .yyp "Folders" entries are GMFolder records and use `folderPath`.
    # They are distinct from `.resource_order` entries (which use name/order/path).
    folder_entries = [
        {
            "$GMFolder": "",
            "%Name": _folder_display_name(fp),
            "folderPath": fp,
            "name": _folder_display_name(fp),
            "resourceType": "GMFolder",
            "resourceVersion": "2.0",
        }
        for fp in folders
    ]

    resource_entries = [{"id": {"name": r.name, "path": r.path}} for r in resources]

    lines: list[str] = []
    lines.append("// Paste these into your .yyp")
    lines.append("// 1) Add to the project's \"Folders\": [ ... ] array")
    lines.append("// 2) Add to the project's \"resources\": [ ... ] array (optional but recommended for library imports)")
    lines.append("")

    lines.append("// --- Folders entries ---")
    for e in folder_entries:
        lines.append(indent + _gm_snippet_line(e, trailing_comma=True))

    lines.append("")
    lines.append("// --- resources entries ---")
    for e in resource_entries:
        lines.append(indent + _gm_snippet_line(e, trailing_comma=True))

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return out_path


def _write_copy_into_resource_order(output_root: Path, folders: list[str], resources: list[ResourceRef]) -> Path:
    out_path = output_root / "__copy_into_resource_order.txt"

    indent = "    "

    # Use a high base so it won't collide if pasted into an existing project.
    base = 10_000

    folder_entries = []
    for i, fp in enumerate(folders):
        folder_entries.append({"name": _folder_display_name(fp), "order": base + i, "path": fp})

    resource_entries = []
    for i, r in enumerate(resources):
        resource_entries.append({"name": r.name, "order": base + len(folder_entries) + i, "path": r.path})

    lines: list[str] = []
    lines.append("// Paste these into your .resource_order")
    lines.append("// Add the folder entries to \"FolderOrderSettings\": [ ... ]")
    lines.append("// Add the resource entries to \"ResourceOrderSettings\": [ ... ]")
    lines.append("// Note: orders are intentionally high to avoid collisions; GameMaker can re-order later.")
    lines.append("")

    lines.append("// --- FolderOrderSettings entries ---")
    for e in folder_entries:
        lines.append(indent + _gm_snippet_line(e, trailing_comma=True))

    lines.append("")
    lines.append("// --- ResourceOrderSettings entries ---")
    for e in resource_entries:
        lines.append(indent + _gm_snippet_line(e, trailing_comma=True))

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate GameMaker copy/paste snippets for .yyp and .resource_order")
    parser.add_argument("--output", default=str(Path(__file__).resolve().parent / "output"), help="Output directory root")
    parser.add_argument("--yyp", default=None, help="Optional target .yyp path (for de-dupe + order base only; not edited)")
    parser.add_argument(
        "--resource-order",
        default=None,
        help="Optional target .resource_order path (for de-dupe + order base only; not edited)",
    )
    args = parser.parse_args(argv)

    output_root = Path(args.output)
    resources = _discover_resources(output_root)
    folders = _discover_folder_paths(resources)

    existing = _read_existing_targets(
        Path(args.yyp) if args.yyp else None,
        Path(args.resource_order) if args.resource_order else None,
    )

    # If the user provided target files, filter out already-present entries to reduce copy/paste noise.
    if args.yyp:
        folders = [fp for fp in folders if fp not in existing.yyp_folder_paths]
        resources = [r for r in resources if r.path not in existing.yyp_resource_paths]
    if args.resource_order:
        folders_for_ro = [fp for fp in folders if fp not in existing.ro_folder_paths]
        resources_for_ro = [r for r in resources if r.path not in existing.ro_resource_paths]
    else:
        folders_for_ro = folders
        resources_for_ro = resources

    yyp_txt = _write_copy_into_yyp(output_root, folders, resources)
    ro_txt = _write_copy_into_resource_order(output_root, folders_for_ro, resources_for_ro)

    print(f"✅ Wrote {yyp_txt}")
    print(f"✅ Wrote {ro_txt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
