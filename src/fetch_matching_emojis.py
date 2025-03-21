import json
import os
import math
from pathlib import Path

# Paths
ROOT_DIR = Path(r"C:\Users\Red\Documents\GameMakerStudio2\_tools\EmojiFontsProject")
EMOJI_DB_PATH = ROOT_DIR / "db" / "emoji.json"
METADATA_DIR = ROOT_DIR / "Assets" / "Sprites" / "Lite"
PRUNED_JSON_PATH = ROOT_DIR / "db" / "pruned_emoji.json"
PRUNED_TXT_PATH = ROOT_DIR / "db" / "pruned_emoji.txt"

SUBFOLDERS = [
    "emojidex",
    "Fluent Flat",
    "Fluent3D",
    "Font_NotoMonochrome",
    "Font_SegoeMonochrome",
    "Icons8",
    "Noto",
    "Openmoji",
    "Segoe",
    "Twemoji",
]

def load_json(file_path):
    """Load a JSON file and return its content as a dictionary."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return {}

def get_common_emojis():
    """Find emojis that are present in at least 70% of the specified metadata.json files."""
    
    # Load full emoji database
    emoji_data = load_json(EMOJI_DB_PATH)
    if not emoji_data:
        print("Error: Failed to load emoji database.")
        return {}

    # Track emoji occurrences
    emoji_occurrences = {}

    # Process only metadata.json files from the specified subfolders
    metadata_files = [
        METADATA_DIR / subfolder / "metadata.json"
        for subfolder in SUBFOLDERS
        if (METADATA_DIR / subfolder / "metadata.json").exists()
    ]

    if not metadata_files:
        print("Error: No valid metadata.json files found in the specified subfolders.")
        return {}

    num_metadata_files = len(metadata_files)
    threshold = math.ceil(num_metadata_files * 0.7)  # 70% threshold

    print(f"Processing {num_metadata_files} metadata.json files from: {SUBFOLDERS}")

    for metadata_file in metadata_files:
        metadata = load_json(metadata_file)
        if not metadata:
            print(f"Warning: Skipping {metadata_file} due to loading error.")
            continue

        for emoji_key in metadata.keys():
            emoji_occurrences[emoji_key] = emoji_occurrences.get(emoji_key, 0) + 1

    # Prune the emoji_data dictionary: Only keep emojis meeting the 70% threshold
    pruned_emoji_data = {
        key: emoji_data.get(key, {"char": key, "name": "Unknown", "unicode": f"U+{ord(key):04X}"})
        for key, count in emoji_occurrences.items() if count >= threshold
    }

    print(f"✅ Retained {len(pruned_emoji_data)} emojis that appear in at least {threshold}/{num_metadata_files} metadata files.")
    return pruned_emoji_data

def extract_unicode_value(emoji_data):
    """Extracts the integer Unicode value from the 'U+XXXXXX' format."""
    unicode_str = emoji_data.get("unicode", "")
    if unicode_str.startswith("U+"):
        try:
            return int(unicode_str[2:], 16)  # Convert hex string to int
        except ValueError:
            return float("inf")  # If conversion fails, push it to the end
    return float("inf")

def save_emoji_txt(pruned_emojis):
    """Save emoji data to a text file with format: "<char>" :: "<unicode>" :: "<name>", sorted by Unicode."""
    
    # Sort the emojis by their Unicode value
    sorted_emojis = sorted(pruned_emojis.items(), key=lambda item: extract_unicode_value(item[1]))

    with open(PRUNED_TXT_PATH, "w", encoding="utf-8") as f:
        for key, data in sorted_emojis:
            emoji_char = data.get("char", key)
            unicode_repr = data.get("unicode", f"U+{key.upper()}")
            emoji_name = data.get("name", "Unknown Name")
            f.write(f'"{emoji_char}" :: "{unicode_repr}" :: "{emoji_name}"\n')

# Run the script
if __name__ == "__main__":
    common_emojis = get_common_emojis()

    # Sort the dictionary by Unicode before saving
    sorted_common_emojis = dict(sorted(common_emojis.items(), key=lambda item: extract_unicode_value(item[1])))

    # Save the pruned data as JSON
    with open(PRUNED_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted_common_emojis, f, indent=4, ensure_ascii=False)

    print(f"Pruned emoji data saved to {PRUNED_JSON_PATH}")

    # Save the formatted text file
    save_emoji_txt(sorted_common_emojis)
    print(f"Formatted emoji list saved to {PRUNED_TXT_PATH}")
