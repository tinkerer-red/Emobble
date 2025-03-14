import json
import os
from pathlib import Path

# Paths
ROOT_DIR = Path(r"C:\Users\Red\Documents\GameMakerStudio2\_tools\EmojiFontsProject")
EMOJI_DB_PATH = ROOT_DIR / "db" / "emoji.json"
METADATA_DIR = ROOT_DIR / "Assets" / "Texture Sheets" / "Lite"
PRUNED_JSON_PATH = ROOT_DIR / "db" / "pruned_emoji.json"
PRUNED_TXT_PATH = ROOT_DIR / "db" / "pruned_emoji.txt"

def load_json(file_path):
    """Load a JSON file and return its content as a dictionary."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return {}

def get_common_emojis():
    """Find emojis that are present in all metadata.json files."""
    
    # Load full emoji database
    emoji_data = load_json(EMOJI_DB_PATH)
    if not emoji_data:
        print("Error: Failed to load emoji database.")
        return {}

    emoji_keys = set(emoji_data.keys())  # Original emoji set

    # Process metadata.json files
    metadata_files = list(METADATA_DIR.glob("*/metadata.json"))
    if not metadata_files:
        print("Error: No metadata.json files found.")
        return {}

    print(f"Processing {len(metadata_files)} metadata.json files...")

    for metadata_file in metadata_files:
        metadata = load_json(metadata_file)
        if not metadata:
            print(f"Warning: Skipping {metadata_file} due to loading error.")
            continue

        metadata_keys = set(metadata.keys())

        # Retain only emojis that appear in all metadata.json files
        emoji_keys.intersection_update(metadata_keys)

    # Prune the emoji_data dictionary
    pruned_emoji_data = {key: emoji_data[key] for key in emoji_keys}

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
