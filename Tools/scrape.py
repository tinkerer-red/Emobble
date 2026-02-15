from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import time
from typing import Any

import requests

TOOLS_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_ROOT))


JSDELIVR_API_PKG = "https://data.jsdelivr.com/v1/package/npm/emojibase-data"
JSDELIVR_CDN_ROOT = "https://cdn.jsdelivr.net/npm/emojibase-data"

TWEMOJI_PNG_ROOT = "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72"

EMOJIPEDIA_ROOT = "https://emojipedia.org"

EM_CONTENT_SOURCE_ROOT = "https://em-content.zobj.net/source"
EM_CONTENT_THUMBS_HOST = "em-content.zobj.net"

DEFAULT_HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": f"{EMOJIPEDIA_ROOT}/",
}

_HTTP = requests.Session()
_HTTP.headers.update(DEFAULT_HTTP_HEADERS)

# Single source of truth for what image sets we scrape by default.
# (Fonts like Segoe Mono / Noto font are NOT scraped.)
DEFAULT_SETS: list[str] = [
    # Twemoji (Twitter) via CDN
    "twemoji",
    # Emojipedia vendor sets
    "google",  # Google - Noto (colored)
    "noto-emoji",  # Noto
    "microsoft-windows-10",  # Segoe UI (Win10)
    "microsoft-fluent-flat",  # Fluent Flat (Win11)
    "microsoft-3D-fluent",  # Fluent 3D (Win11)
    "openmoji",
    "emojidex",
    "icons8",
]

# Defaults for the legacy CLI (kept only for backwards compatibility).
DEFAULT_IMAGE_SOURCES: list[str] = ["twemoji", "emojipedia"]
DEFAULT_EMOJIPEDIA_VENDORS: list[str] = [s for s in DEFAULT_SETS if s not in ("twemoji", "none")]

# For our pipeline we keep vendor folder names stable and human-friendly.
# The values are Emojipedia vendor slugs.
KNOWN_VENDOR_ALIASES: dict[str, str] = {
    # Preferred sets (per user request)
    "openmoji": "openmoji",
    "google-noto": "google",
    "google": "google",
    "noto": "noto-emoji",
    "noto-emoji": "noto-emoji",
    "microsoft-segoe-ui": "microsoft",
    "segoe-ui": "microsoft",
    "microsoft": "microsoft",
    # Microsoft platform variants (Emojipedia pages under /microsoft/<release>/...)
    "microsoft-win10": "microsoft-windows-10",
    "microsoft-windows-10": "microsoft-windows-10",
    "windows-10": "microsoft-windows-10",
    "microsoft-fluent-flat": "microsoft-fluent-flat",
    "fluent-flat": "microsoft-fluent-flat",
    "microsoft-fluent-3d": "microsoft-3D-fluent",
    "fluent-3d": "microsoft-3D-fluent",
    "microsoft-3d-fluent": "microsoft-3D-fluent",
    "microsoft-teams": "microsoft-teams",
    "twemoji": "twitter",
    "twitter": "twitter",
    "emojidex": "emojidex",
    "icons8": "icons8",
}

# Folder names to match the project’s existing naming conventions.
VENDOR_OUTPUT_DIRNAME: dict[str, str] = {
    "openmoji": "OpenMoji",
    "google": "Google - Noto",
    "noto-emoji": "Noto",
    "microsoft": "Microsoft",
    "microsoft-windows-10": "Microsoft - Windows 10",
    "microsoft-fluent-flat": "Microsoft - Fluent Flat",
    "microsoft-3D-fluent": "Microsoft - Fluent 3D",
    "microsoft-teams": "Microsoft Teams",
    "twitter": "Twemoji",
    "emojidex": "emojidex",
    "icons8": "Icons8",
}

# Emojipedia also hosts historical/variant Microsoft sets under /microsoft/<release>/ pages.
# These are not separate vendor slugs on /vendors/, so we model them as pseudo-vendor set IDs.
EMOJIPEDIA_COLLECTION_PAGE_BY_SET_ID: dict[str, str] = {
    # Windows 10-era Segoe UI Emoji (last Win10 update noted by Emojipedia).
    "microsoft-windows-10": "microsoft/windows-10-may-2019-update",
    # Windows 11 launch-era Fluent (2D/flat) set.
    "microsoft-fluent-flat": "microsoft/windows-11-november-2021-update",
}


def _set_id_to_emojipedia_vendor_slug(set_id: str) -> str:
    set_id = str(set_id).strip().strip("/")
    # Platform variants still use the Microsoft vendor slug in em-content URLs.
    if set_id in EMOJIPEDIA_COLLECTION_PAGE_BY_SET_ID:
        return "microsoft"
    return set_id

# Revision fallback policy for missing images.
MAX_FALLBACK_REV_STEPS = 10
MAX_FALLBACK_REV_TRIES_PER_EMOJI = 10


def _download_json(url: str) -> Any:
    r = _HTTP.get(url, timeout=60)
    r.raise_for_status()
    return r.json()


def _download_bytes(url: str) -> bytes:
    r = _HTTP.get(url, timeout=60)
    r.raise_for_status()
    return r.content


def _download_text(url: str) -> str:
    r = _HTTP.get(url, timeout=60)
    r.raise_for_status()
    return r.text


def _format_seconds(seconds: float | int | None) -> str:
    if seconds is None:
        return "?"
    try:
        seconds_f = float(seconds)
    except Exception:
        return "?"
    if seconds_f < 0:
        seconds_f = 0
    s = int(round(seconds_f))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m"
    if m:
        return f"{m}m {sec:02d}s"
    return f"{sec}s"


def _slugify_emojipedia_label(label: str) -> str:
    """Best-effort conversion of an English label into an Emojipedia slug.

    This avoids an expensive /search/ request for most emoji.
    """
    s = str(label or "").strip().lower()
    if not s:
        return ""

    # Common substitutions
    s = s.replace("&", " and ")
    s = s.replace("’", "'")
    s = s.replace("'", "")

    # Drop punctuation
    s = re.sub(r"[\.:,;!\?\(\)\[\]{}]", " ", s)
    s = s.replace("#", " sharp ")
    s = s.replace("+", " plus ")

    # Collapse to slug
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def _ensure_playwright_ready() -> tuple[bool, str]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return (
            False,
            "Playwright is required for Emojipedia revision discovery. "
            "Install in this Python env: pip install playwright; python -m playwright install chromium",
        )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception as e:
        return (
            False,
            "Playwright is installed but Chromium couldn't launch. "
            "Run: python -m playwright install chromium. "
            f"Details: {e}",
        )

    return True, ""


def _merge_json(base: Any, new: Any) -> Any:
    if isinstance(base, dict) and isinstance(new, dict):
        out = dict(base)
        for k, v in new.items():
            out[k] = _merge_json(out[k], v) if k in out else v
        return out
    if isinstance(base, list) and isinstance(new, list):
        # Preserve uniqueness; order is not guaranteed.
        return list(set(base + new))
    if isinstance(base, str) and isinstance(new, str):
        return base if base == new else list(set([base, new]))
    if isinstance(base, str) and isinstance(new, list):
        return list(set([base] + new))
    if isinstance(base, list) and isinstance(new, str):
        return list(set(base + [new]))
    return new


def _sleep(delay_seconds: float | None) -> None:
    if not delay_seconds:
        return
    try:
        delay = float(delay_seconds)
    except Exception:
        return
    if delay > 0:
        time.sleep(delay)


def _jsdelivr_latest_version() -> str:
    meta = _download_json(JSDELIVR_API_PKG)
    latest = (meta.get("tags") or {}).get("latest")
    if not latest:
        raise RuntimeError("Unable to resolve emojibase-data latest version via jsDelivr")
    return str(latest)


def _list_locales_and_shortcodes(version: str) -> tuple[list[str], dict[str, list[str]]]:
    """Return (locales, shortcode_files_by_locale).

    Uses jsDelivr file tree so we only request files that actually exist.
    """
    tree = _download_json(f"{JSDELIVR_API_PKG}@{version}")
    files = tree.get("files") or []

    locales: list[str] = []
    shortcode_files: dict[str, list[str]] = {}

    for node in files:
        if node.get("type") != "directory":
            continue
        locale = node.get("name")
        if not locale:
            continue

        # Only accept directories that actually look like locale dirs.
        child_names = {str(ch.get("name")) for ch in (node.get("files") or []) if ch.get("type") == "file"}
        if "compact.json" not in child_names and "data.json" not in child_names:
            continue

        locales.append(locale)

        # Find shortcodes directory
        sc_list: list[str] = []
        for child in node.get("files") or []:
            if child.get("type") == "directory" and child.get("name") == "shortcodes":
                for sc_file in child.get("files") or []:
                    if sc_file.get("type") == "file" and str(sc_file.get("name", "")).endswith(".json"):
                        sc_list.append(str(sc_file["name"]))
        shortcode_files[locale] = sorted(set(sc_list))

    locales = sorted(set(locales))
    return locales, shortcode_files


def _write_json_if_missing(path: Path, data: Any, force: bool) -> bool:
    if path.exists() and not force:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    return True


def _safe_hex_filename_from_hexcode(hexcode: str) -> str:
    # Normalize for local filenames: underscores, uppercase.
    return str(hexcode).strip().upper().replace("-", "_")


def _is_single_codepoint_hex(hexcode: str) -> bool:
    parts = [p for p in str(hexcode).split("-") if p]
    return len(parts) == 1


def _single_codepoint_from_hex(hexcode: str) -> int | None:
    parts = [p for p in str(hexcode).split("-") if p]
    if len(parts) != 1:
        return None
    try:
        return int(parts[0], 16)
    except Exception:
        return None


def _should_try_old_revisions_for_hex(hexcode: str) -> bool:
    # Only for single codepoint <= 65563 (per project constraint) and never for sequences (ZWJ/VS16).
    cp = _single_codepoint_from_hex(hexcode)
    if cp is None:
        return False
    return cp <= 65563


def _normalize_twemoji_hexcode_components(hexcode: str) -> str:
    """Normalize an emojibase hexcode into Twemoji-style lowercase with no leading zeros.

    Example: "0030-FE0F-20E3" -> "30-fe0f-20e3".
    """
    parts = [p.strip().lower() for p in str(hexcode).split("-") if p.strip()]
    normalized: list[str] = []
    for p in parts:
        p = p.lstrip("0") or "0"
        normalized.append(p)
    return "-".join(normalized)


def _twemoji_url_candidates_from_hexcode(hexcode: str) -> list[str]:
    """Return a list of Twemoji CDN URL candidates for a given emojibase hexcode.

    Twemoji filenames often omit variation selector-16 (FE0F) for many emoji, but not all.
    We try both the full sequence and a version with FE0F removed.
    """
    norm = _normalize_twemoji_hexcode_components(hexcode)
    candidates = [norm]

    # Try stripping FE0F components (common for single-codepoint emoji like 2764-FE0F).
    parts = [p for p in norm.split("-") if p and p != "fe0f"]
    stripped = "-".join(parts)
    if stripped and stripped != norm:
        candidates.append(stripped)

    # De-dupe while preserving order.
    out: list[str] = []
    seen: set[str] = set()
    for c in candidates:
        if c not in seen:
            out.append(c)
            seen.add(c)
    return out


def _iter_hexcodes_from_data_json(data_json: list[dict[str, Any]]) -> set[str]:
    out: set[str] = set()
    for entry in data_json:
        if not isinstance(entry, dict):
            continue
        hx = entry.get("hexcode")
        if isinstance(hx, str) and hx:
            out.add(hx)
        skins = entry.get("skins")
        if isinstance(skins, list):
            for s in skins:
                if isinstance(s, dict) and isinstance(s.get("hexcode"), str) and s["hexcode"]:
                    out.add(s["hexcode"])
    return out


def _download_twemoji_pngs(
    hexcodes: set[str],
    out_dir: Path,
    force: bool,
    limit: int | None,
) -> tuple[int, int, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    skipped = 0
    failed = 0

    hexcodes_list = sorted(hexcodes)
    if limit is not None:
        hexcodes_list = hexcodes_list[: max(0, int(limit))]

    for hx in hexcodes_list:
        filename = _safe_hex_filename_from_hexcode(hx) + ".png"
        dest = out_dir / filename
        if dest.exists() and not force:
            skipped += 1
            continue

        success = False
        last_error: Exception | None = None
        for url_hex in _twemoji_url_candidates_from_hexcode(hx):
            url = f"{TWEMOJI_PNG_ROOT}/{url_hex}.png"
            try:
                content = _download_bytes(url)
            except Exception as e:
                last_error = e
                continue
            dest.write_bytes(content)
            downloaded += 1
            success = True
            break

        if not success:
            failed += 1

    return downloaded, skipped, failed


def _titleize_vendor_slug(slug: str) -> str:
    # "fluent-ui-emoji" -> "Fluent Ui Emoji" (kept simple; user can rename folders if desired)
    words = [w for w in str(slug).replace("_", "-").split("-") if w]
    return " ".join(w[:1].upper() + w[1:] for w in words) if words else str(slug)


def _normalize_vendor_slug(v: str) -> str:
    v = str(v).strip()
    if not v:
        return v
    key = v.lower().replace(" ", "-").replace("_", "-")
    key = re.sub(r"[^a-z0-9-]+", "-", key)
    key = re.sub(r"-+", "-", key).strip("-")
    return KNOWN_VENDOR_ALIASES.get(key, v)


def _normalize_set_token(token: str) -> str:
    t = str(token or "").strip()
    if not t:
        return ""
    # Strip parenthetical descriptors like "(Twitter)" or "(Colored)".
    t = re.sub(r"\([^)]*\)", "", t).strip()
    # Common punctuation normalization
    t = t.replace("—", "-").replace("–", "-")
    return _normalize_vendor_slug(t)


def _parse_sets_arg(value: str | None) -> list[str]:
    if value is None:
        return list(DEFAULT_SETS)
    parts = [p.strip() for p in str(value).split(",") if p.strip()]
    if not parts:
        return ["none"]
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        norm = _normalize_set_token(p)
        if not norm:
            continue
        if norm not in seen:
            out.append(norm)
            seen.add(norm)
    if not out:
        out = ["none"]
    if "none" in out and len(out) > 1:
        raise ValueError("--sets cannot include 'none' with other values")
    return out


def _vendor_output_dirname(vendor_slug: str) -> str:
    vendor_slug = str(vendor_slug).strip().strip("/")
    return VENDOR_OUTPUT_DIRNAME.get(vendor_slug, _titleize_vendor_slug(vendor_slug))


def _emojipedia_search_base_path(query: str, delay_seconds: float | None) -> str | None:
    """Resolve an Emojipedia base emoji path like "/grinning-face/" from a search query.

    Uses the public search page and picks the shortest plausible result path.
    """
    from urllib.parse import quote
    from html.parser import HTMLParser

    url = f"{EMOJIPEDIA_ROOT}/search/?q={quote(query)}"
    html = _download_text(url)
    _sleep(delay_seconds)

    class _LinkParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.hrefs_prefer: list[str] = []
            self.hrefs_all: list[str] = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag != "a":
                return
            href = None
            cls = ""
            for k, v in attrs:
                if k == "href":
                    href = v
                elif k == "class" and isinstance(v, str):
                    cls = v
            if not href:
                return

            self.hrefs_all.append(href)
            # Search results currently render emoji tiles with classes like "Emoji_emoji__..." and
            # "EmojisList_emojis-list-item__...".
            lowered = cls.lower()
            if "emoji_emoji" in lowered or "emojislist_" in lowered:
                self.hrefs_prefer.append(href)

    parser = _LinkParser()
    parser.feed(html)

    hrefs = parser.hrefs_prefer if parser.hrefs_prefer else parser.hrefs_all

    # Filter obvious non-emoji pages.
    blacklist = {
        "about",
        "activity",
        "contact",
        "faq",
        "glossary",
        "help",
        "licensing",
        "press",
        "privacy-policy",
        "requests",
        "search",
        "stats",
        "tips",
        "tos",
        "unicode-versions",
        "vendors",
        # common category pages
        "emoji",
        "emoji-versions",
        "flags",
        "food-drink",
        "nature",
        "objects",
        "people",
        "smileys",
        "symbols",
        "travel-places",
    }

    cleaned: list[str] = []
    for href in hrefs:
        if not isinstance(href, str) or not href.startswith("/"):
            continue
        if href.startswith("/search") or href.startswith("/vendors") or href.startswith("/about"):
            continue
        parts = [p for p in href.split("/") if p]
        if len(parts) == 1:
            slug = parts[0]
            if slug in blacklist:
                continue
            cleaned.append("/" + slug + "/")

    if not cleaned:
        return None
    # Preserve document order (first plausible result tends to be the best match).
    seen: set[str] = set()
    for path in cleaned:
        if path in seen:
            continue
        seen.add(path)
        return path
    return None


def _emojipedia_vendor_url(vendor_slug: str, base_path: str) -> str:
    vendor_slug = str(vendor_slug).strip().strip("/")
    base_path = "/" + "/".join([p for p in str(base_path).split("/") if p]) + "/"
    if not vendor_slug:
        return f"{EMOJIPEDIA_ROOT}{base_path}"
    return f"{EMOJIPEDIA_ROOT}/{vendor_slug}{base_path}"


def _emojipedia_extract_og_image_url(html: str) -> str | None:
    import re

    m = re.search(r'property="og:image"[^>]*content="([^"]+)"', html)
    return m.group(1) if m else None


def _emojipedia_base_path_to_slug(base_path: str) -> str:
    return str(base_path).strip().strip("/")


def _em_content_source_png_url(vendor_slug: str, revision: str | int, emoji_slug: str, hexcode: str) -> str:
    vendor_slug = str(vendor_slug).strip().strip("/")
    emoji_slug = str(emoji_slug).strip().strip("/")
    revision_str = str(revision).strip().strip("/")
    hx = str(hexcode).strip().lower()
    return f"{EM_CONTENT_SOURCE_ROOT}/{vendor_slug}/{revision_str}/{emoji_slug}_{hx}.png"


def _emojipedia_discover_vendor_revision(vendor_slug: str, delay_seconds: float | None) -> str | None:
    """Discover the em-content revision number for a vendor by observing thumbnail requests.

    Emojipedia currently loads vendor emoji images dynamically and requests thumbnail URLs like:
    https://em-content.zobj.net/thumbs/60/<vendor>/<rev>/<slug>_<hex>.webp

    We click the vendor name on a stable emoji page and capture the first matching thumbs URL.
    """

    import re

    vendor_slug = str(vendor_slug).strip().strip("/")
    if not vendor_slug:
        return None

    # Fast path: the vendor landing page often includes thumbnail URLs in its HTML payload.
    try:
        html = _download_text(f"{EMOJIPEDIA_ROOT}/{vendor_slug}/")
        _sleep(delay_seconds)
        m = re.search(
            rf"(?:https?:)?//{re.escape(EM_CONTENT_THUMBS_HOST)}/thumbs/\d+/{re.escape(vendor_slug)}/(\d+)/",
            html,
            flags=re.IGNORECASE,
        )
        if m:
            rev = str(m.group(1))
            return rev if rev.isdigit() else None
    except Exception:
        pass
    # We intentionally avoid doing browser automation here; Playwright navigation can be slow/flaky.
    # If the HTML doesn't contain the revision, callers should fall back to `_emojipedia_discover_revision_from_page`.
    return None


def _emojipedia_discover_revision_from_page(page_url: str, vendor_slug: str, delay_seconds: float | None) -> str | None:
    """Use Playwright to discover an em-content thumbs revision by observing network responses."""

    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None

    vendor_slug = str(vendor_slug).strip().strip("/")
    if not vendor_slug:
        return None

    vendor_slug_lc = vendor_slug.lower()
    captured: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def on_response(resp) -> None:
            try:
                u = resp.url
                u_lc = u.lower()
                if EM_CONTENT_THUMBS_HOST in u_lc and "/thumbs/" in u_lc and f"/{vendor_slug_lc}/" in u_lc:
                    captured.append(u)
            except Exception:
                return

        page.on("response", on_response)
        try:
            # Avoid "networkidle" (some pages keep connections open); we only need initial thumbs requests.
            page.goto(str(page_url), wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(5_000)
        except Exception:
            pass
        finally:
            try:
                browser.close()
            except Exception:
                pass

    for u in captured:
        parts = [p for p in u.split("/") if p]
        parts_lc = [p.lower() for p in parts]
        if vendor_slug_lc not in parts_lc:
            continue
        idx = parts_lc.index(vendor_slug_lc)
        if idx + 1 >= len(parts):
            continue
        rev = parts[idx + 1]
        if rev.isdigit():
            _sleep(delay_seconds)
            return rev

    _sleep(delay_seconds)
    return None


def _emojipedia_discover_set_revision(set_id: str, delay_seconds: float | None) -> str | None:
    """Discover revision for either a normal vendor slug or a pseudo-vendor set (collection page)."""

    set_id = str(set_id).strip().strip("/")
    if not set_id:
        return None

    if set_id in EMOJIPEDIA_COLLECTION_PAGE_BY_SET_ID:
        page_path = EMOJIPEDIA_COLLECTION_PAGE_BY_SET_ID[set_id]
        page_url = f"{EMOJIPEDIA_ROOT}/" + "/".join([p for p in str(page_path).split("/") if p]) + "/"
        vendor_slug = _set_id_to_emojipedia_vendor_slug(set_id)
        return _emojipedia_discover_revision_from_page(page_url, vendor_slug=vendor_slug, delay_seconds=delay_seconds)

    # Normal vendor slug
    vendor_slug = set_id
    # Prefer lightweight HTML parsing first; fall back to Playwright if needed.
    rev = _emojipedia_discover_vendor_revision(vendor_slug, delay_seconds=delay_seconds)
    if rev:
        return rev
    page_url = f"{EMOJIPEDIA_ROOT}/{vendor_slug}/"
    return _emojipedia_discover_revision_from_page(page_url, vendor_slug=vendor_slug, delay_seconds=delay_seconds)


def _emojipedia_validate_vendor_slugs(vendors: list[str], delay_seconds: float | None) -> list[str]:
    """Return only set IDs that appear to exist on emojipedia.org.

    This supports both real vendor slugs (e.g. "openmoji") and pseudo sets like
    "microsoft-fluent-flat" which map to a Microsoft collection page.
    """

    valid: list[str] = []
    for set_id in vendors:
        set_id = str(set_id).strip().strip("/")
        if not set_id:
            continue

        if set_id in EMOJIPEDIA_COLLECTION_PAGE_BY_SET_ID:
            page_path = EMOJIPEDIA_COLLECTION_PAGE_BY_SET_ID[set_id]
            url = f"{EMOJIPEDIA_ROOT}/" + "/".join([p for p in str(page_path).split("/") if p]) + "/"
        else:
            url = f"{EMOJIPEDIA_ROOT}/{set_id}/"

        try:
            html = _download_text(url)
            _sleep(delay_seconds)
            if "emojipedia" in html.lower():
                valid.append(set_id)
        except Exception:
            continue

    return valid


def _emojipedia_list_vendor_slugs(delay_seconds: float | None) -> list[str]:
    """Scrape https://emojipedia.org/vendors/ to list vendor slugs."""
    from html.parser import HTMLParser

    html = _download_text(f"{EMOJIPEDIA_ROOT}/vendors/")
    _sleep(delay_seconds)

    class _VendorParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.slugs: set[str] = set()

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag != "a":
                return
            href = None
            for k, v in attrs:
                if k == "href":
                    href = v
                    break
            if not href or not href.startswith("/"):
                return
            # Vendor links are typically "/apple/" etc.
            parts = [p for p in href.split("/") if p]
            if len(parts) != 1:
                return
            slug = parts[0]
            if all(ch.isalnum() or ch == "-" for ch in slug):
                self.slugs.add(slug)

    parser = _VendorParser()
    parser.feed(html)
    return sorted(parser.slugs)


def _download_emojipedia_vendor_pngs(
    hexcodes_to_emoji: list[tuple[str, str, str]],
    out_root: Path,
    vendors: list[str],
    vendor_revisions: dict[str, str],
    vendor_fallback_revisions: dict[str, dict[str, str]],
    force: bool,
    limit: int | None,
    delay_seconds: float | None,
    cache_paths: dict[str, str],
) -> dict[str, dict[str, int]]:
    """Download vendor images via Emojipedia vendor pages.

    Returns per-vendor stats: {vendor: {downloaded, skipped, failed, resolved}}.
    """

    stats: dict[str, dict[str, int]] = {}
    for set_id in vendors:
        stats[set_id] = {"downloaded": 0, "skipped": 0, "failed": 0, "resolved": 0}

    targets = hexcodes_to_emoji
    if limit is not None:
        targets = targets[: max(0, int(limit))]

    failures: list[dict[str, str]] = []

    total_emojis = len(targets)
    total_ops = max(1, total_emojis * max(1, len(vendors)))
    start_t = time.time()
    last_report_t = start_t
    processed_emojis = 0

    for hx, emoji, label in targets:
        base_path = cache_paths.get(hx)
        slug_guess = _slugify_emojipedia_label(label) or _slugify_emojipedia_label(emoji)

        if base_path:
            emoji_slug = _emojipedia_base_path_to_slug(base_path)
        else:
            emoji_slug = slug_guess
            # We will fall back to a real search only if downloads fail with the guessed slug.

        for vendor in vendors:
            set_id = vendor
            vendor_slug = _set_id_to_emojipedia_vendor_slug(set_id)
            rev = vendor_revisions.get(set_id)
            if not rev:
                stats[set_id]["failed"] += 1
                if len(failures) < 100:
                    failures.append({"hexcode": hx, "vendor": set_id, "step": "missing_revision", "base_path": base_path})
                continue

            vendor_dirname = _vendor_output_dirname(set_id)
            out_dir = out_root / vendor_dirname
            out_dir.mkdir(parents=True, exist_ok=True)

            filename = _safe_hex_filename_from_hexcode(hx) + ".png"
            dest = out_dir / filename
            if dest.exists() and not force:
                stats[vendor]["skipped"] += 1
                continue

            # If we previously found a fallback revision for this vendor+hexcode, prefer it.
            preferred_rev = (
                (vendor_fallback_revisions.get(set_id) or {}).get(str(hx).upper())
                or (vendor_fallback_revisions.get(set_id) or {}).get(str(hx).lower())
            )
            if preferred_rev and preferred_rev.isdigit():
                rev_to_try_first = preferred_rev
            else:
                rev_to_try_first = rev

            def _try_download_with_rev(rev_candidate: str) -> bool:
                img_url = _em_content_source_png_url(vendor_slug, rev_candidate, emoji_slug, hx)
                content = _download_bytes(img_url)
                dest.write_bytes(content)
                return True

            try:
                _try_download_with_rev(str(rev_to_try_first))
                stats[set_id]["downloaded"] += 1
                stats[set_id]["resolved"] += 1
            except Exception as first_err:
                # If we were using a guessed slug, do one expensive search to confirm the correct slug and retry once.
                if not base_path:
                    base_path = _emojipedia_search_base_path(hx, delay_seconds=delay_seconds) or _emojipedia_search_base_path(
                        emoji, delay_seconds=delay_seconds
                    )
                    if base_path:
                        cache_paths[hx] = base_path
                        emoji_slug = _emojipedia_base_path_to_slug(base_path)
                        try:
                            _try_download_with_rev(str(rev_to_try_first))
                            stats[set_id]["downloaded"] += 1
                            stats[set_id]["resolved"] += 1
                            continue
                        except Exception:
                            # fall through to fallback handling
                            pass

                # Try older revisions ONLY for single-codepoint <= 65563.
                if not _should_try_old_revisions_for_hex(hx):
                    stats[set_id]["failed"] += 1
                    if len(failures) < 100:
                        failures.append({"hexcode": hx, "vendor": set_id, "step": "vendor_or_image", "base_path": base_path or "", "error": type(first_err).__name__})
                    continue

                # Backtrack a small number of revisions; cache the first working one.
                found = False
                try:
                    rev_int = int(str(rev_to_try_first))
                except Exception:
                    rev_int = None

                if rev_int is not None:
                    tries = 0
                    for delta in range(1, MAX_FALLBACK_REV_STEPS + 1):
                        if tries >= MAX_FALLBACK_REV_TRIES_PER_EMOJI:
                            break
                        tries += 1

                        candidate_int = rev_int - delta
                        if candidate_int <= 0:
                            break
                        candidate = str(candidate_int)

                        try:
                            _try_download_with_rev(candidate)
                        except Exception:
                            continue

                        found = True
                        vendor_fallback_revisions.setdefault(set_id, {})[str(hx).upper()] = candidate
                        stats[set_id]["downloaded"] += 1
                        stats[set_id]["resolved"] += 1
                        break

                if not found:
                    stats[set_id]["failed"] += 1
                    if len(failures) < 100:
                        failures.append({"hexcode": hx, "vendor": set_id, "step": "fallback_failed", "base_path": base_path})

        processed_emojis += 1
        now = time.time()
        if processed_emojis == 1 or (now - last_report_t) >= 15:
            done_ops = processed_emojis * max(1, len(vendors))
            elapsed = now - start_t
            rate = (done_ops / elapsed) if elapsed > 0 else 0.0
            remaining_ops = max(0, total_ops - done_ops)
            eta = (remaining_ops / rate) if rate > 0 else None

            downloaded_total = sum((stats[s].get("downloaded", 0) for s in vendors if s in stats), 0)
            skipped_total = sum((stats[s].get("skipped", 0) for s in vendors if s in stats), 0)
            failed_total = sum((stats[s].get("failed", 0) for s in vendors if s in stats), 0)

            pct = (100.0 * processed_emojis / total_emojis) if total_emojis else 100.0
            print(
                f"🧭 Emojipedia progress: {processed_emojis}/{total_emojis} emojis ({pct:.1f}%), "
                f"{rate:.2f} ops/s, ETA {_format_seconds(eta)} | "
                f"downloaded={downloaded_total}, skipped={skipped_total}, failed={failed_total}"
            )
            last_report_t = now

    # Attach failures for caller if they want to persist.
    stats["__failures__"] = {"count": len(failures)}
    # Keep the detailed list separate to avoid ballooning stats in memory.
    stats["__failures_list__"] = {"items": failures}
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape/download emoji datasets (emoji data, shortcodes, locale names) and optionally images. "
            "All outputs are cached under Tools/db and skipped if already present unless --force is used."
        )
    )
    parser.add_argument("--output", default=str(TOOLS_ROOT / "output"), help="Output root (unused; scraper writes under Tools/db)")
    parser.add_argument("--force", action="store_true", help="Re-download and overwrite existing DB files")
    parser.add_argument("--all-locales", action="store_true", help="Download all locales available in emojibase-data")
    parser.add_argument("--locales", default="en", help="Comma-separated locales to download (ignored with --all-locales)")
    parser.add_argument("--with-data", action="store_true", default=True, help="Download data.json per locale")
    parser.add_argument("--with-compact", action="store_true", default=True, help="Download compact.json per locale")
    parser.add_argument("--with-shortcodes", action="store_true", default=True, help="Download all shortcodes/*.json per locale")
    parser.add_argument(
        "--sets",
        default=None,
        help=(
            "Comma-separated sets to download. If omitted, downloads the default sets. "
            "If provided, ONLY those sets are downloaded. Use 'none' to skip images. "
            f"Default: {','.join(DEFAULT_SETS)}. "
            "Examples: --sets twemoji,openmoji | --sets twemoji | --sets none"
        ),
    )

    # Legacy flags (hidden): keep older scripts/commands working.
    parser.add_argument("--with-image", "--with-images", dest="with_images", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--image-limit", type=int, default=0, help="Limit image downloads for testing (0 = no limit)")
    parser.add_argument(
        "--request-delay",
        type=float,
        default=0.2,
        help="Polite delay (seconds) between HTTP requests for scraping (default: 0.2)",
    )
    parser.add_argument(
        "--emojipedia-vendors",
        default=",".join(DEFAULT_EMOJIPEDIA_VENDORS),
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--list-emojipedia-vendors",
        action="store_true",
        help="List vendor slugs available on emojipedia.org and exit",
    )
    args = parser.parse_args(argv)

    force = bool(args.force)
    limit = int(args.image_limit) if int(args.image_limit) > 0 else None
    delay_seconds = float(args.request_delay) if args.request_delay is not None else None

    if bool(args.list_emojipedia_vendors):
        slugs = _emojipedia_list_vendor_slugs(delay_seconds=delay_seconds)
        print("\n".join(slugs))
        return 0

    # Unify image selection.
    try:
        sets = _parse_sets_arg(args.sets)
    except ValueError as e:
        print(f"❌ {e}")
        return 2

    # If user didn't specify --sets but did specify legacy flags, translate them.
    if args.sets is None and args.with_images is not None:
        legacy_sources = [s.strip().lower() for s in str(args.with_images).split(",") if s.strip()]
        if not legacy_sources:
            legacy_sources = ["none"]
        if "none" in legacy_sources:
            sets = ["none"]
        else:
            translated: list[str] = []
            if "twemoji" in legacy_sources:
                translated.append("twemoji")
            if "emojipedia" in legacy_sources:
                translated.extend([s.strip() for s in str(args.emojipedia_vendors).split(",") if s.strip()])
            try:
                sets = _parse_sets_arg(",".join(translated) if translated else "none")
            except ValueError as e:
                print(f"❌ {e}")
                return 2

    do_images = sets != ["none"]
    do_twemoji = False
    emojipedia_sets: list[str] = []
    for s in sets:
        norm = _normalize_set_token(s)
        if norm in ("twitter", "twemoji"):
            do_twemoji = True
        elif norm != "none":
            emojipedia_sets.append(norm)

    # Back-compat manifest fields
    image_sources: list[str] = []
    if do_images:
        if do_twemoji:
            image_sources.append("twemoji")
        if emojipedia_sets:
            image_sources.append("emojipedia")

    version = _jsdelivr_latest_version()
    all_locales, shortcode_files = _list_locales_and_shortcodes(version)

    if args.all_locales:
        locales = all_locales
    else:
        locales = [l.strip() for l in str(args.locales).split(",") if l.strip()]
        if not locales:
            locales = ["en"]

    db_dir = TOOLS_ROOT / "db"
    emojibase_root = db_dir / "Emojibase" / version
    data_dir = db_dir / "Data"  # convenience compact outputs
    shortcodes_dir = db_dir / "Shortcodes"  # convenience merged outputs
    db_png_dir = db_dir / "PNGs"
    emojipedia_dir = db_dir / "Emojipedia"

    db_dir.mkdir(parents=True, exist_ok=True)
    emojibase_root.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    shortcodes_dir.mkdir(parents=True, exist_ok=True)
    emojipedia_dir.mkdir(parents=True, exist_ok=True)

    wrote_any = 0
    skipped_any = 0
    wrote_shortcodes = 0
    skipped_shortcodes = 0

    # 1) Download emojibase per-locale datasets
    for locale in locales:
        locale_root = emojibase_root / locale
        locale_root.mkdir(parents=True, exist_ok=True)

        if args.with_data:
            url = f"{JSDELIVR_CDN_ROOT}@{version}/{locale}/data.json"
            dest = locale_root / "data.json"
            if dest.exists() and not force:
                skipped_any += 1
            else:
                print(f"📥 {locale}: data.json")
                try:
                    data_json = _download_json(url)
                except Exception as e:
                    print(f"⚠️ {locale}: failed data.json ({e})")
                else:
                    wrote_any += 1 if _write_json_if_missing(dest, data_json, force=True) else 0

        if args.with_compact:
            url = f"{JSDELIVR_CDN_ROOT}@{version}/{locale}/compact.json"
            dest = locale_root / "compact.json"
            if dest.exists() and not force:
                skipped_any += 1
            else:
                print(f"📥 {locale}: compact.json")
                try:
                    compact_json = _download_json(url)
                except Exception as e:
                    print(f"⚠️ {locale}: failed compact.json ({e})")
                else:
                    wrote_any += 1 if _write_json_if_missing(dest, compact_json, force=True) else 0
                    # convenience file (legacy path): db/Data/<locale>.json
                    if _write_json_if_missing(data_dir / f"{locale}.json", compact_json, force=force):
                        wrote_any += 1
                    else:
                        skipped_any += 1

        if args.with_shortcodes:
            sc_root = locale_root / "shortcodes"
            sc_root.mkdir(parents=True, exist_ok=True)
            merged: Any = {}
            files = shortcode_files.get(locale) or []
            if files:
                print(f"📥 {locale}: shortcodes ({len(files)} files)")
            for name in files:
                url = f"{JSDELIVR_CDN_ROOT}@{version}/{locale}/shortcodes/{name}"
                dest = sc_root / name
                if dest.exists() and not force:
                    skipped_shortcodes += 1
                    continue
                try:
                    sc_json = _download_json(url)
                except Exception:
                    continue
                if _write_json_if_missing(dest, sc_json, force=True):
                    wrote_shortcodes += 1
                merged = _merge_json(merged, sc_json)
            # convenience merged file: db/Shortcodes/<locale>.json
            if merged:
                if _write_json_if_missing(shortcodes_dir / f"{locale}.json", merged, force=force):
                    wrote_shortcodes += 1
                else:
                    skipped_shortcodes += 1

    # 2) Images (optional)
    if do_images and do_twemoji:
        # Read from en data.json if present, else en compact.json.
        en_data_path = emojibase_root / "en" / "data.json"
        if not en_data_path.exists():
            print("❌ Twemoji download requires en/data.json; run with --with-data")
            return 1
        en_data = json.loads(en_data_path.read_text(encoding="utf-8"))
        hexcodes = _iter_hexcodes_from_data_json(en_data)

        # Keep Twemoji CDN outputs in the same vendor folder naming scheme as Emojipedia.
        # (The twitter vendor set maps to "Twemoji"; using a separate lowercase "twemoji" folder
        # causes downstream atlas/font stages to miss the images.)
        out_dir = db_png_dir / _vendor_output_dirname("twitter")

        # Back-compat: older runs wrote into db/PNGs/twemoji.
        old_dir = db_png_dir / "twemoji"
        if old_dir.exists() and old_dir.is_dir() and out_dir.name != old_dir.name:
            # On case-insensitive filesystems (Windows default), these may refer to the same directory.
            same_dir = False
            try:
                same_dir = old_dir.resolve().samefile(out_dir.resolve())
            except Exception:
                try:
                    same_dir = str(old_dir.resolve()).lower() == str(out_dir.resolve()).lower()
                except Exception:
                    same_dir = False

            if not same_dir:
                if not out_dir.exists():
                    try:
                        old_dir.replace(out_dir)
                    except Exception:
                        # If we can't rename (e.g. cross-device), just proceed with the new folder.
                        pass
                else:
                    # If both exist (case-sensitive FS), merge files so downstream stages see one set.
                    try:
                        out_dir.mkdir(parents=True, exist_ok=True)
                        for p in old_dir.rglob("*.png"):
                            rel = p.relative_to(old_dir)
                            dest = out_dir / rel
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            if not dest.exists():
                                try:
                                    p.replace(dest)
                                except Exception:
                                    # Best-effort merge; ignore locked/colliding files.
                                    pass
                        # Remove legacy folder if now empty.
                        try:
                            if not any(old_dir.rglob("*")):
                                old_dir.rmdir()
                        except Exception:
                            pass
                    except Exception:
                        pass
        print(f"🖼️ Downloading Twemoji PNGs: {len(hexcodes)} targets")
        dl, sk, fail = _download_twemoji_pngs(hexcodes, out_dir=out_dir, force=force, limit=limit)
        print(f"✅ Twemoji PNGs: downloaded={dl}, skipped={sk}, failed={fail}")

        # Persist a small report for quick inspection when failures happen.
        # (We don't currently store per-emoji error reasons to keep the scrape log clean.)
        if fail:
            _write_json_if_missing(
                db_dir / "twemoji_download_report.json",
                {
                    "emojibase_version": version,
                    "attempted": len(hexcodes) if limit is None else int(limit),
                    "downloaded": dl,
                    "skipped": sk,
                    "failed": fail,
                    "note": "Twemoji filenames may omit FE0F; scraper tries both with/without FE0F.",
                },
                force=True,
            )

    if do_images and emojipedia_sets:
        en_data_path = emojibase_root / "en" / "data.json"
        if not en_data_path.exists():
            print("❌ Emojipedia download requires en/data.json; run with --with-data")
            return 1

        vendors = [_normalize_vendor_slug(v) for v in emojipedia_sets]
        if not vendors:
            print("❌ No emojipedia vendors specified; pass --emojipedia-vendors")
            return 1

        valid_vendors = _emojipedia_validate_vendor_slugs(vendors, delay_seconds=delay_seconds)
        invalid = [v for v in vendors if v not in valid_vendors]
        if invalid:
            print(f"⚠️ Emojipedia: skipping invalid vendors: {', '.join(invalid)}")
        vendors = valid_vendors
        if not vendors:
            print("❌ Emojipedia: no valid vendors remain after validation")
            return 1

        en_data = json.loads(en_data_path.read_text(encoding="utf-8"))
        hx_to_emoji: list[tuple[str, str, str]] = []
        for entry in en_data:
            if not isinstance(entry, dict):
                continue
            hx = entry.get("hexcode")
            em = entry.get("emoji")
            label = entry.get("label")
            label_str = str(label) if isinstance(label, str) else ""
            if isinstance(label, str) and label.lower().startswith("regional indicator"):
                # Skip components; flags are represented by separate multi-codepoint entries.
                continue
            if isinstance(hx, str) and hx and isinstance(em, str) and em:
                hx_to_emoji.append((hx, em, label_str))
            skins = entry.get("skins")
            if isinstance(skins, list):
                for s in skins:
                    if not isinstance(s, dict):
                        continue
                    shx = s.get("hexcode")
                    sem = s.get("emoji") or em
                    if isinstance(shx, str) and shx and isinstance(sem, str) and sem:
                        hx_to_emoji.append((shx, sem, label_str))

        # De-dupe by hexcode while preserving order.
        seen_hx: set[str] = set()
        hx_to_emoji_deduped: list[tuple[str, str, str]] = []
        for hx, em, label_str in hx_to_emoji:
            if hx in seen_hx:
                continue
            seen_hx.add(hx)
            hx_to_emoji_deduped.append((hx, em, label_str))

        cache_path_file = emojipedia_dir / "emoji_paths.json"
        if cache_path_file.exists():
            try:
                cache_paths = json.loads(cache_path_file.read_text(encoding="utf-8"))
                if not isinstance(cache_paths, dict):
                    cache_paths = {}
            except Exception:
                cache_paths = {}
        else:
            cache_paths = {}

        vendor_rev_file = emojipedia_dir / "vendor_revisions.json"
        if vendor_rev_file.exists():
            try:
                vendor_revisions = json.loads(vendor_rev_file.read_text(encoding="utf-8"))
                if not isinstance(vendor_revisions, dict):
                    vendor_revisions = {}
            except Exception:
                vendor_revisions = {}
        else:
            vendor_revisions = {}

        fallback_rev_file = emojipedia_dir / "fallback_revisions.json"
        if fallback_rev_file.exists():
            try:
                vendor_fallback_revisions = json.loads(fallback_rev_file.read_text(encoding="utf-8"))
                if not isinstance(vendor_fallback_revisions, dict):
                    vendor_fallback_revisions = {}
            except Exception:
                vendor_fallback_revisions = {}
        else:
            vendor_fallback_revisions = {}

        # Discover missing set revisions (requires Playwright on a fresh DB).
        missing_revs = [v for v in vendors if not vendor_revisions.get(v)]
        if missing_revs:
            ok, reason = _ensure_playwright_ready()
            if not ok:
                print("❌ Emojipedia image scraping can't start yet.")
                print(f"   {reason}")
                print("   Tip: run the pipeline using Tools/.venv Python to avoid env mismatches.")
                return 1

            print(f"🔎 Emojipedia: discovering vendor revisions ({len(missing_revs)} sets)")
            for i, v in enumerate(missing_revs, start=1):
                print(f"   - [{i}/{len(missing_revs)}] discovering revision for {v}...")
                rev = _emojipedia_discover_set_revision(v, delay_seconds=delay_seconds)
                if rev:
                    vendor_revisions[v] = rev
                    print(f"     ↳ {v}: rev={rev}")
                else:
                    print(f"     ↳ {v}: failed (try again later or increase --request-delay)")

        # Drop any sets without a discovered revision.
        missing_after = [v for v in vendors if not vendor_revisions.get(v)]
        if missing_after:
            print(f"⚠️ Emojipedia: skipping {len(missing_after)} sets with unknown revision: {', '.join(missing_after)}")
        vendors = [v for v in vendors if vendor_revisions.get(v)]
        if not vendors:
            print("❌ Emojipedia: no sets have a known revision; aborting image download")
            return 1

        _write_json_if_missing(vendor_rev_file, vendor_revisions, force=True)

        out_root = db_png_dir
        effective_targets = len(hx_to_emoji_deduped) if limit is None else min(len(hx_to_emoji_deduped), int(limit))
        print(f"🖼️ Downloading Emojipedia vendor PNGs: vendors={len(vendors)}, emojis={effective_targets}")
        try:
            vendor_stats = _download_emojipedia_vendor_pngs(
                hexcodes_to_emoji=hx_to_emoji_deduped,
                out_root=out_root,
                vendors=vendors,
                vendor_revisions=vendor_revisions,
                vendor_fallback_revisions=vendor_fallback_revisions,
                force=force,
                limit=limit,
                delay_seconds=delay_seconds,
                cache_paths=cache_paths,
            )
        except KeyboardInterrupt:
            print("⏹ Interrupted by user (keeping partial downloads)")
            _write_json_if_missing(fallback_rev_file, vendor_fallback_revisions, force=True)
            _write_json_if_missing(cache_path_file, cache_paths, force=True)
            _write_json_if_missing(vendor_rev_file, vendor_revisions, force=True)
            return 130

        _write_json_if_missing(fallback_rev_file, vendor_fallback_revisions, force=True)

        # Persist resolved base paths for next run.
        _write_json_if_missing(cache_path_file, cache_paths, force=True)

        # Persist a small failure sample for debugging.
        failures = (vendor_stats.get("__failures_list__") or {}).get("items") or []
        if failures:
            _write_json_if_missing(
                emojipedia_dir / "emojipedia_failures.json",
                {
                    "note": "Sample of up to 100 failures (hexcode/vendor/step) to help tune vendor slugs and parsing.",
                    "items": failures,
                },
                force=True,
            )

        # Summary
        for v in vendors:
            st = vendor_stats.get(v, {})
            print(
                f"✅ Emojipedia {v}: downloaded={st.get('downloaded', 0)}, "
                f"skipped={st.get('skipped', 0)}, resolved={st.get('resolved', 0)}, failed={st.get('failed', 0)}"
            )

    # Record what we fetched
    _write_json_if_missing(
        db_dir / "scrape_manifest.json",
        {
            "emojibase_version": version,
            "locales": locales,
            "with_data": bool(args.with_data),
            "with_compact": bool(args.with_compact),
            "with_shortcodes": bool(args.with_shortcodes),
            "sets": sets,
            "with_images": image_sources,
            "emojipedia_vendors": vendors if (do_images and emojipedia_sets) else [],
        },
        force=True,
    )

    print(
        "✅ Scrape complete "
        f"(wrote={wrote_any + wrote_shortcodes}, skipped={skipped_any + skipped_shortcodes}; "
        f"datasets={wrote_any}, shortcodes={wrote_shortcodes})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
