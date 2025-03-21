import os
import json
from itertools import combinations
import shutil

# Define directories
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_DIR = os.path.join(PROJECT_ROOT, "db")
DB_DATA_DIR = os.path.join(DB_DIR, "Data")
SHORTCODES_DIR = os.path.join(DB_DIR, "Shortcodes")
IMAGE_DIR = os.path.join(PROJECT_ROOT, "Assets", "PNGs")  # Adjust as needed

# Define database file paths
DATA_FILE = os.path.join(DB_DATA_DIR, "en.json")
SHORTCODES_FILE = os.path.join(SHORTCODES_DIR, "en.json")

# Load JSON data
def load_json(file_path):
    """Loads a JSON file and returns its content."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {file_path}")
        return None

# Load database files
data_entries = load_json(DATA_FILE) or []
shortcode_entries = load_json(SHORTCODES_FILE) or {}

# Convert data JSON list to a set of valid hexcodes (including skin tones)
data_hex_set = set()

for entry in data_entries:
    data_hex_set.add(entry["hexcode"])  # Add base emoji
    if "skins" in entry:
        for skin in entry["skins"]:
            data_hex_set.add(skin["hexcode"])  # Add skin tone variants


# Convert shortcode dictionary keys to a set
shortcode_hex_set = set(shortcode_entries.keys())


def generate_fe0f_variants(hexcode):
    """Generates all possible combinations of removing or keeping `-FE0F` in a hexcode."""
    parts = hexcode.split("-")
    fe0f_indices = [i for i, part in enumerate(parts) if part == "FE0F"]

    if not fe0f_indices:
        return []  # No FE0F to modify

    variants = set()
    
    # ✅ Generate every possible combination of removing `FE0F`
    for i in range(1, len(fe0f_indices) + 1):
        for combo in combinations(fe0f_indices, i):
            modified_parts = [part for j, part in enumerate(parts) if j not in combo]
            variants.add("-".join(modified_parts))

    return sorted(variants)  # Sorting ensures consistency

def normalize_hexcode(hexcode):
    """Ensures all segments in a hexcode are at least 4 characters long by padding with leading zeros."""
    parts = hexcode.split("-")
    normalized_parts = [part.zfill(4) for part in parts]  # ✅ Pad segments to 4 characters
    return "-".join(normalized_parts)

def verify_images():
    """Checks all images in the image directory against the database JSONs and renames/moves files as needed."""
    for platform in os.listdir(IMAGE_DIR):  # Iterate through platform folders (e.g., Apple, Twitter)
        platform_path = os.path.join(IMAGE_DIR, platform)
        if not os.path.isdir(platform_path):
            continue  # Skip non-folder files

        missing_in_data = []
        missing_in_shortcodes = []

        for filename in os.listdir(platform_path):
            if filename.endswith(".png"):
                hexcode = filename.replace(".png", "").upper()  # ✅ Convert to uppercase
                hexcode = normalize_hexcode(hexcode)  # ✅ Normalize short segments
                image_path = os.path.join(platform_path, filename)  # Full file path

                # ✅ Ensure uppercase normalization in lookup
                in_data = hexcode in data_hex_set
                in_shortcodes = hexcode in shortcode_hex_set

                # ✅ Try removing `-FE0F` variations if the emoji is missing
                if not in_data and not in_shortcodes and "-FE0F" in hexcode:
                    for variant in generate_fe0f_variants(hexcode):
                        variant = normalize_hexcode(variant)  # ✅ Normalize variant
                        if variant in data_hex_set or variant in shortcode_hex_set:
                            new_filename = variant + ".png"
                            new_path = os.path.join(platform_path, new_filename)

                            # ✅ If the destination file already exists, delete it
                            if os.path.exists(new_path):
                                os.rename(new_path, f"{new_path}_copy")
                                
                            # ✅ Rename file
                            os.rename(image_path, new_path)
                            print(f"🔄 Renamed {filename} → {new_filename}")

                            # ✅ Update path reference and break loop
                            image_path = new_path
                            hexcode = variant
                            break  # Stop after first successful rename

                # ✅ If the emoji is STILL missing, move it to `_MissingData/`
                if not in_data and not in_shortcodes:
                    missing_data_path = os.path.join(platform_path, "_MissingData")
                    os.makedirs(missing_data_path, exist_ok=True)  # Ensure `_MissingData` exists
                    new_missing_path = os.path.join(missing_data_path, filename)
                    shutil.move(image_path, new_missing_path)
                    print(f"🚨 Moved {filename} to {new_missing_path}")
                    continue  # Skip further checks for this file

                # ✅ If the emoji is valid but filename isn't uppercase, rename it
                expected_filename = hexcode + ".png"
                expected_path = os.path.join(platform_path, expected_filename)

                if image_path != expected_path:
                    # ✅ If the destination file already exists, delete it
                    if os.path.exists(image_path):
                        os.rename(image_path, expected_path)
                        print(f"🔄 Renamed {filename} → {expected_filename}")
                    else:
                        print(f"🚨 File already Renamed {filename} → {expected_filename}")

                if not in_data:
                    missing_in_data.append(f"{hexcode} | {expected_path}")
                if not in_shortcodes:
                    missing_in_shortcodes.append(f"{hexcode} | {expected_path}")

        # Write logs per platform
        write_platform_log(platform, missing_in_data, missing_in_shortcodes)


# Write platform-specific error logs
def write_platform_log(platform, missing_in_data, missing_in_shortcodes):
    """Writes missing hex codes to a log file per platform, only if there are missing entries."""
    if not missing_in_data and not missing_in_shortcodes:
        print(f"✅ No missing entries for {platform}. Skipping log file.")
        return  # ✅ Don't create an empty log file

    log_file_path = os.path.join(PROJECT_ROOT, f"{platform}_errors.txt")

    with open(log_file_path, "w", encoding="utf-8") as log:
        if missing_in_data:
            log.write("❌ Missing from Data/en.json:\n")
            log.write("\n".join(missing_in_data) + "\n\n")
        if missing_in_shortcodes:
            log.write("❌ Missing from Shortcodes/en.json:\n")
            log.write("\n".join(missing_in_shortcodes) + "\n\n")

    print(f"⚠️ Log saved for {platform}: {log_file_path}")


# Run verification
if __name__ == "__main__":
    verify_images()
