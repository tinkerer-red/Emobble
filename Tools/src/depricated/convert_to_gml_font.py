import os
import json
import shutil
import logging
import re
import math

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# Project structure
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GML_DIR = os.path.join(PROJECT_ROOT, "GML")
TEXTURE_SHEETS_DIR = os.path.join(PROJECT_ROOT, "Assets", "Texture Sheets")

# Ensure GML folder exists
os.makedirs(GML_DIR, exist_ok=True)

PADDING = 1  # 1px padding on all sides

# Template for GameMaker `.yy` font file
GMFONT_TEMPLATE = {
  "$GMFont":"",
  "%Name":"Font1",
  "AntiAlias":1,
  "applyKerning":0,
  "ascender":0,
  "ascenderOffset":0,
  "bold":False,
  "canGenerateBitmap":True,
  "charset":0,
  "first":0,
  "fontName":"Arial",
  "glyphOperations":0,
  "glyphs":{},
  "hinting":0,
  "includeTTF":False,
  "interpreter":0,
  "italic":False,
  "kerningPairs":[],
  "last":0,
  "lineHeight":0,
  "maintainGms1Font":False,
  "name":"",
  "parent":{
    "name":"EmojiFonts",
    "path":"EmojiFonts.yyp",
  },
  "pointRounding":0,
  "ranges":[],
  "regenerateBitmap":False,
  "resourceType":"GMFont",
  "resourceVersion":"2.0",
  "sampleText":"",
  "sdfSpread":8,
  "size":12.0,
  "styleName":"Regular",
  "textureGroupId":{
    "name":"Default",
    "path":"texturegroups/Default",
  },
  "TTFName":"",
  "usesSDF":False,
}

def to_camel_case(name):
    """Converts a string to CamelCase, removing `_`, `-`, and spaces."""
    words = re.split(r"[_\-\s]+", name)
    return "".join(word.capitalize() for word in words)

# Store the order and resources
resource_order = []
resources = {}

def unicode_info(char):
    """ Returns a dictionary with various Unicode encodings for logging """
    try:
        return {
            "char": char,
            "UTF-8": char.encode("utf-8").hex(" "),
            "UTF-16": char.encode("utf-16be").hex(" "),
            "UTF-32": char.encode("utf-32be").hex(" "),
            "Ord Value": ord(char)
        }
    except Exception as e:
        return {"char": char, "error": str(e)}

def generate_gml_fonts():
    """Generate GML font folders, `.yy` font files, and GameMaker resource files."""
    order_counter = 1  # Track the order of resources
    resources_list = []  # Store all font resources

    for lite in [False, True]:  # Full and Lite versions
        lite_tag = "Lite" if lite else "Full"
        base_dir = os.path.join(TEXTURE_SHEETS_DIR, lite_tag)

        if not os.path.exists(base_dir):
            log.warning(f"Missing texture sheets directory: {base_dir}")
            continue

        for category in os.listdir(base_dir):
            category_path = os.path.join(base_dir, category)
            if not os.path.isdir(category_path):
                continue  # Skip non-directory entries

            for size in [16, 24, 32, 48, 64]:  # Texture sizes
                metadata_file = os.path.join(category_path, "metadata.json")
                if not os.path.exists(metadata_file):
                    log.warning(f"Metadata file missing: {metadata_file}")
                    continue
                
                with open(metadata_file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

                log.info(f"\n🔍 Checking Unicode Data for '{category}' ({lite_tag}, {size}px)")

                for char in metadata:
                    if len(char) > 1:
                        log.warning(f"Skipping unexpected multi-char key: {char}")
                        continue
                    
                    unicode_data = unicode_info(char)
                    
                    log.info(
                        f"📝 Char: {unicode_data['char']} | "
                        f"UTF-8: {unicode_data['UTF-8']} | "
                        f"UTF-16: {unicode_data['UTF-16']} | "
                        f"UTF-32: {unicode_data['UTF-32']} | "
                        f"Ord: {unicode_data['Ord Value']}"
                    )

if __name__ == "__main__":
    generate_gml_fonts()