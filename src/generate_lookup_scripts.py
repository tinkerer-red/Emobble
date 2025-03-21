import os
import json

# Define project directory structure
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "Assets")
SPRITE_SHEETS_DIR = os.path.join(ASSETS_DIR, "Sprites")
FULL_SPRITE_DIR = os.path.join(SPRITE_SHEETS_DIR, "Full")
LITE_SPRITE_DIR = os.path.join(SPRITE_SHEETS_DIR, "Lite")

# Function to properly escape JSON for GML
def escape_json_for_gml(json_string):
    return json_string.replace("\\", "\\\\").replace("\"", "\\\"")

# Function to process metadata files and generate GML code
def generate_gml_lookup():
    for sprite_dir, label in [(FULL_SPRITE_DIR, "full"), (LITE_SPRITE_DIR, "lite")]:
        for category in os.listdir(sprite_dir):
            category_path = os.path.join(sprite_dir, category)
            metadata_path = os.path.join(category_path, "metadata.json")
            output_gml_path = os.path.join(category_path, "lookup.gml")

            if not os.path.isdir(category_path) or not os.path.exists(metadata_path):
                continue

            # Read and minify the JSON metadata
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            minified_json = json.dumps(metadata, separators=(",", ":"))

            # Properly escape JSON for GML string
            escaped_json = escape_json_for_gml(minified_json)

            # Format the function name
            function_name = f"__emoji_lookup_{category.lower()}_{label}"

            # Generate GML function
            gml_code = f'function {function_name}() {{\n\t//This is a generated file from `generate_lookup_scripts.py` please dont modify.\n\treturn json_parse("{escaped_json}");\n}}'

            # Save to lookup.gml
            with open(output_gml_path, "w", encoding="utf-8") as f:
                f.write(gml_code)

            print(f"Generated: {output_gml_path}")

# Run the function to generate GML lookup files
generate_gml_lookup()
