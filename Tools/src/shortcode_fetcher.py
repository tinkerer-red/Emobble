import os
import json
import requests

# Define directories
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_DIR = os.path.join(PROJECT_ROOT, "db")
DB_DATA_DIR = os.path.join(DB_DIR, "Data")
SHORTCODES_DIR = os.path.join(DB_DIR, "Shortcodes")

# Ensure directories exist
os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(SHORTCODES_DIR, exist_ok=True)

# Mapping of locales to their multiple shortcodes dataset URLs
SHORTCODE_URLS = {
    "bn":[ "https://cdn.jsdelivr.net/npm/emojibase-data/bn/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/bn/shortcodes/cldr.json" ],

    "da":[ "https://cdn.jsdelivr.net/npm/emojibase-data/da/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/da/shortcodes/cldr.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/da/shortcodes/emojibase-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/da/shortcodes/emojibase.json" ],

    "de":[ "https://cdn.jsdelivr.net/npm/emojibase-data/de/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/de/shortcodes/cldr.json" ],

    "en-gb":[ "https://cdn.jsdelivr.net/npm/emojibase-data/en-gb/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/en-gb/shortcodes/cldr.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/en-gb/shortcodes/emojibase.json" ],

    "en":[ "https://cdn.jsdelivr.net/npm/emojibase-data/en/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/en/shortcodes/cldr.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/en/shortcodes/emojibase-legacy.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/en/shortcodes/emojibase.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/en/shortcodes/github.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/en/shortcodes/iamcal.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/en/shortcodes/joypixels.json" ],

    "es-mx":[ "https://cdn.jsdelivr.net/npm/emojibase-data/es-mx/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/es-mx/shortcodes/cldr.json" ],

    "es":[ "https://cdn.jsdelivr.net/npm/emojibase-data/es/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/es/shortcodes/cldr.json" ],

    "et":[ "https://cdn.jsdelivr.net/npm/emojibase-data/et/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/et/shortcodes/cldr.json" ],

    "fi":[ "https://cdn.jsdelivr.net/npm/emojibase-data/fi/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/fi/shortcodes/cldr.json" ],

    "fr":[ "https://cdn.jsdelivr.net/npm/emojibase-data/fr/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/fr/shortcodes/cldr.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/fr/shortcodes/emojibase.json" ],

    "hi":[ "https://cdn.jsdelivr.net/npm/emojibase-data/hi/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/hi/shortcodes/cldr.json" ],

    "hu":[ "https://cdn.jsdelivr.net/npm/emojibase-data/hu/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/hu/shortcodes/cldr.json" ],

    "it":[ "https://cdn.jsdelivr.net/npm/emojibase-data/it/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/it/shortcodes/cldr.json" ],

    "ja":[ "https://cdn.jsdelivr.net/npm/emojibase-data/ja/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/ja/shortcodes/cldr.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/ja/shortcodes/emojibase-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/ja/shortcodes/emojibase.json" ],

    "ko":[ "https://cdn.jsdelivr.net/npm/emojibase-data/ko/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/ko/shortcodes/cldr.json" ],

    "lt":[ "https://cdn.jsdelivr.net/npm/emojibase-data/lt/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/lt/shortcodes/cldr.json" ],

    "ms":[ "https://cdn.jsdelivr.net/npm/emojibase-data/ms/shortcodes/cldr.json" ],

    "nb":[ "https://cdn.jsdelivr.net/npm/emojibase-data/nb/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/nb/shortcodes/cldr.json" ],

    "nl":[ "https://cdn.jsdelivr.net/npm/emojibase-data/nl/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/nl/shortcodes/cldr.json" ],

    "pl":[ "https://cdn.jsdelivr.net/npm/emojibase-data/pl/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/pl/shortcodes/cldr.json" ],

    "pt":[ "https://cdn.jsdelivr.net/npm/emojibase-data/pt/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/pt/shortcodes/cldr.json" ],

    "ru":[ "https://cdn.jsdelivr.net/npm/emojibase-data/ru/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/ru/shortcodes/cldr.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/ru/shortcodes/emojibase-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/ru/shortcodes/emojibase.json" ],

    "sv":[ "https://cdn.jsdelivr.net/npm/emojibase-data/sv/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/sv/shortcodes/cldr.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/sv/shortcodes/emojibase-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/sv/shortcodes/emojibase.json" ],

    "th":[ "https://cdn.jsdelivr.net/npm/emojibase-data/th/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/th/shortcodes/cldr.json" ],

    "uk":[ "https://cdn.jsdelivr.net/npm/emojibase-data/uk/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/uk/shortcodes/cldr.json" ],

    "vi":[ "https://cdn.jsdelivr.net/npm/emojibase-data/vi/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/vi/shortcodes/cldr.json" ],

    "zh-hant":[ "https://cdn.jsdelivr.net/npm/emojibase-data/zh-hant/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/zh-hant/shortcodes/cldr.json" ],

    "zh":[ "https://cdn.jsdelivr.net/npm/emojibase-data/zh/shortcodes/cldr-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/zh/shortcodes/cldr.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/zh/shortcodes/emojibase-native.json",
        "https://cdn.jsdelivr.net/npm/emojibase-data/zh/shortcodes/emojibase.json" ],
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
    for locale, urls in SHORTCODE_URLS.items():
        merged_data = {}

        for url in urls:
            json_data = download_json(url)
            if json_data:
                merged_data = merge_json(merged_data, json_data)

        # Save merged JSON file
        if merged_data:
            file_path = os.path.join(SHORTCODES_DIR, f"{locale}.json")
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(merged_data, file, ensure_ascii=False, indent=2)
            print(f"Saved merged JSON: {file_path}")


if __name__ == "__main__":
    main()
