import os
import json
import requests

# Define directories
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_DIR = os.path.join(PROJECT_ROOT, "db")
DB_DATA_DIR = os.path.join(DB_DIR, "Data")

# Ensure directories exist
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(DB_DATA_DIR, exist_ok=True)

# Mapping of locales to their multiple shortcodes dataset URLs
COMPACT_JSON_URLS = {
    "bn": ["https://cdn.jsdelivr.net/npm/emojibase-data/bn/compact.json"],
    "da": ["https://cdn.jsdelivr.net/npm/emojibase-data/da/compact.json"],
    "de": ["https://cdn.jsdelivr.net/npm/emojibase-data/de/compact.json"],
    "en-gb": ["https://cdn.jsdelivr.net/npm/emojibase-data/en-gb/compact.json"],
    "en": ["https://cdn.jsdelivr.net/npm/emojibase-data/en/compact.json"],
    "es-mx": ["https://cdn.jsdelivr.net/npm/emojibase-data/es-mx/compact.json"],
    "es": ["https://cdn.jsdelivr.net/npm/emojibase-data/es/compact.json"],
    "et": ["https://cdn.jsdelivr.net/npm/emojibase-data/et/compact.json"],
    "fi": ["https://cdn.jsdelivr.net/npm/emojibase-data/fi/compact.json"],
    "fr": ["https://cdn.jsdelivr.net/npm/emojibase-data/fr/compact.json"],
    "hi": ["https://cdn.jsdelivr.net/npm/emojibase-data/hi/compact.json"],
    "hu": ["https://cdn.jsdelivr.net/npm/emojibase-data/hu/compact.json"],
    "it": ["https://cdn.jsdelivr.net/npm/emojibase-data/it/compact.json"],
    "ja": ["https://cdn.jsdelivr.net/npm/emojibase-data/ja/compact.json"],
    "ko": ["https://cdn.jsdelivr.net/npm/emojibase-data/ko/compact.json"],
    "lt": ["https://cdn.jsdelivr.net/npm/emojibase-data/lt/compact.json"],
    "ms": ["https://cdn.jsdelivr.net/npm/emojibase-data/ms/compact.json"],
    "nb": ["https://cdn.jsdelivr.net/npm/emojibase-data/nb/compact.json"],
    "nl": ["https://cdn.jsdelivr.net/npm/emojibase-data/nl/compact.json"],
    "pl": ["https://cdn.jsdelivr.net/npm/emojibase-data/pl/compact.json"],
    "pt": ["https://cdn.jsdelivr.net/npm/emojibase-data/pt/compact.json"],
    "ru": ["https://cdn.jsdelivr.net/npm/emojibase-data/ru/compact.json"],
    "sv": ["https://cdn.jsdelivr.net/npm/emojibase-data/sv/compact.json"],
    "th": ["https://cdn.jsdelivr.net/npm/emojibase-data/th/compact.json"],
    "uk": ["https://cdn.jsdelivr.net/npm/emojibase-data/uk/compact.json"],
    "vi": ["https://cdn.jsdelivr.net/npm/emojibase-data/vi/compact.json"],
    "zh-hant": ["https://cdn.jsdelivr.net/npm/emojibase-data/zh-hant/compact.json"],
    "zh": ["https://cdn.jsdelivr.net/npm/emojibase-data/zh/compact.json"],
}

def merge_json(base, new_data):
    """Recursively merges JSON objects, merging arrays and avoiding duplicates."""
    if isinstance(base, dict) and isinstance(new_data, dict):
        for key, value in new_data.items():
            if key in base:
                base[key] = merge_json(base[key], value)
            else:
                base[key] = value
        return base

    elif isinstance(base, list) and isinstance(new_data, list):
        return list(set(base + new_data))  # Merge lists and remove duplicates

    elif isinstance(base, str) and isinstance(new_data, str):
        return list(set([base, new_data])) if base != new_data else base

    elif isinstance(base, str) and isinstance(new_data, list):
        return list(set([base] + new_data))

    elif isinstance(base, list) and isinstance(new_data, str):
        return list(set(base + [new_data]))

    return new_data  # Default case, replace with new data


def download_json(url):
    """Downloads a JSON file from a URL and returns the parsed JSON object."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Failed to download {url}: {e}")
        return None


def main():
    """Main function to download and merge JSON datasets."""
    for locale, urls in COMPACT_JSON_URLS.items():
        merged_data = {}

        for url in urls:
            json_data = download_json(url)
            if json_data:
                merged_data = merge_json(merged_data, json_data)

        # Save merged JSON file
        if merged_data:
            file_path = os.path.join(DB_DATA_DIR, f"{locale}.json")
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(merged_data, file, ensure_ascii=False, indent=2)
            print(f"Saved merged JSON: {file_path}")


if __name__ == "__main__":
    main()
