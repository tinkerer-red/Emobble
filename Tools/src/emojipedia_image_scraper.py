import random
import json
import os
import re
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_DIR = os.path.join(PROJECT_ROOT, "db")
ASSET_DIR = os.path.join(PROJECT_ROOT, "Assets")
PNG_DIR = os.path.join(ASSET_DIR, "PNGs")

BASE_URL = "https://emojipedia.org"
TIMEOUT = 3  # Global timeout in seconds

def sanitize_folder_name(name):
    """
    Sanitizes a folder name by replacing invalid characters with an underscore.
    """
    invalid_chars = r'<>:"/\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    return name.strip()

def load_json_data(json_path):
    """
    Loads the emoji data from a JSON file.
    
    Args:
        json_path (str): Path to the JSON file.
        
    Returns:
        dict: The loaded emoji data.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def download_image(img_url, manufacturer, unicode_value):
    """
    Downloads the image from the given URL if it hasn't already been downloaded.
    
    Args:
        img_url (str): URL of the image to download.
        manufacturer (str): Manufacturer name (used for the directory structure).
        unicode_value (str): Unicode identifier (used for the file_path).
        
    Returns:
        str: The path to the downloaded image file.
    """
    # Convert "U+1F1F2 U+1F1EB" to "1F1F2_1F1EB"
    clean_unicode = "_".join(part.replace("U+", "") for part in unicode_value.split())
    
    safe_manufacturer = sanitize_folder_name(manufacturer)
    dest_dir = os.path.join(PNG_DIR, safe_manufacturer)
    os.makedirs(dest_dir, exist_ok=True)
    file_path = os.path.join(dest_dir, f"{clean_unicode}.png")

    if os.path.exists(file_path):
        #print(f"Image already exists: {file_path}")
        return file_path

     # Try optimized thumbnail version first
    optimized_url = img_url.replace("em-content.zobj.net/source/", "em-content.zobj.net/thumbs/60/").replace(".webp", ".png")

    try:
        response = requests.get(optimized_url)
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(response.content)
            return file_path # Success
        else:
            print(f"Optimized image not available at {optimized_url}, falling back to original...")
    except Exception as e:
        print(f"Error downloading optimized image: {e}, falling back...")

    # If original image is not PNG, skip
    if not img_url.lower().endswith(".png"):
        print(f"❌ Skipping non-PNG image: {img_url}")
        return

    # Fallback to original full-size image
    try:
        response = requests.get(img_url)
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                f.write(response.content)
        else:
            print(f"Failed to download fallback image: {img_url}")
    except Exception as e:
        print(f"Failed to download fallback image: {e}")
    
    return file_path

def extract_manufacturer(section):
    """Returns the manufacturer name from a section <h3><a> tag, removing any parentheses."""
    try:
        h3 = section.find_element(By.TAG_NAME, "h3")
    except Exception:
        raise Exception("No <h3> found in section: " + section.get_attribute("outerHTML"))

    try:
        manufacturer_element = h3.find_element(By.TAG_NAME, "a")
        manufacturer = manufacturer_element.text.strip()

        # Fallback to innerText if .text is empty
        if not manufacturer:
            manufacturer = manufacturer_element.get_attribute("innerText").strip()

        # Still fallback to innerHTML if needed (very rare)
        if not manufacturer:
            manufacturer = re.sub(r"<[^>]+>", "", manufacturer_element.get_attribute("innerHTML")).strip()
    except Exception:
        raise Exception("No <a> tag found in <h3>: " + h3.get_attribute("outerHTML"))

    # Remove parentheses, like "Apple (2012–2024)" → "Apple"
    if "(" in manufacturer:
        manufacturer = re.split(r"\s*\(", manufacturer)[0].strip()

    if not manufacturer:
        raise Exception("Manufacturer name is empty. Section HTML: " + section.get_attribute("outerHTML"))

    return manufacturer

def process_manufacturer_section(section, unicode_value):
    """Extracts manufacturer and downloads appropriate image(s), with special handling for Microsoft."""
    try:
        manufacturer = extract_manufacturer(section)
    except Exception as e:
        print("Failed to extract manufacturer:", e)
        return

    try:
        inner_list = section.find_element(By.XPATH, ".//*[contains(@class, 'EmojiTimeline_emoji-timeline-pins-list')]")
    except Exception as e:
        print(f"Timeline list not found for {manufacturer}:", e)
        return

    # Special handling for Microsoft
    if manufacturer == "Microsoft":
        pins = inner_list.find_elements(By.XPATH, ".//*[contains(@class, 'EmojiTimeline_emoji-timeline-pin__')]")

        cutoff_date = datetime.strptime("2021/10", "%Y/%m")
        segoe_pins = []
        fluent_pins = []

        # Divide into two buckets
        for pin in pins:
            try:
                date_text = pin.find_element(By.XPATH, ".//p[contains(@class, 'emoji-timeline-pin-date')]").get_attribute("textContent").strip()
                date_obj = datetime.strptime(date_text, "%Y/%m")
                if date_obj <= cutoff_date:
                    segoe_pins.append((date_obj, pin))
                else:
                    fluent_pins.append((date_obj, pin))
            except Exception:
                print(f"[DEBUG] Pin date found: {date_text}")
                continue

        segoe_success = False
        fluent_success = False
        debug_urls = []

        # Sort and take the latest from each list
        if segoe_pins:
            segoe_pins.sort(key=lambda x: x[0], reverse=True)
            try:
                segoe_img = segoe_pins[0][1].find_element(By.TAG_NAME, "img").get_attribute("src")
                debug_urls.append(f"Segoe candidate: {segoe_img}")
                download_image(segoe_img, "Microsoft - Segoe UI", unicode_value)
                segoe_success = True
            except Exception as e:
                print("Failed to download Microsoft - Segoe UI image:", e)
        #else:
            #print("No Segoe UI pin found for Microsoft.")

        if fluent_pins:
            fluent_pins.sort(key=lambda x: x[0], reverse=True)
            try:
                fluent_img = fluent_pins[0][1].find_element(By.TAG_NAME, "img").get_attribute("src")
                debug_urls.append(f"Fluent candidate: {fluent_img}")
                download_image(fluent_img, "Microsoft - Fluent Flat", unicode_value)
                fluent_success = True
            except Exception as e:
                print("Failed to download Microsoft - Fluent Flat image:", e)
        #else:
            #print("No Fluent Flat pin found for Microsoft.")
    
        if not segoe_success and not fluent_success:
            print("\n\n‼️ Debug info for Microsoft emoji failure:")

            for url in debug_urls:
                print(url)

            print("\n📦 Raw HTML of emoji timeline list:")
            try:
                print(inner_list.get_attribute("outerHTML"))
            except Exception as e:
                print(f"Could not get inner_list HTML: {e}")
        
            print("\n")

            raise Exception("Microsoft emoji download failed for both Fluent and Segoe candidates.")
        
        return

    # Default case for all other manufacturers
    try:
        active_pin = inner_list.find_element(By.XPATH, ".//*[contains(@class, 'emoji-timeline-pin-active')]")
        img_element = active_pin.find_element(By.TAG_NAME, "img")
        img_url = img_element.get_attribute("src")
        download_image(img_url, manufacturer, unicode_value)
    except Exception as e:
        print(f"Image not found for {manufacturer}:", e)

def process_emoji(driver, wait, emoji_data):
    """
    Processes a single emoji by navigating to its design page,
    waiting for the designs to load, and processing each manufacturer section.
    
    Only sections that contain a timeline (as identified by a child element 
    with a class containing "EmojiTimeline_emoji-timeline-pins-list") are processed.
    
    Args:
        driver (WebDriver): Selenium WebDriver instance.
        wait (WebDriverWait): Selenium WebDriverWait instance.
        emoji_data (dict): Data for a single emoji containing at least 'slug' and 'unicode'.
    """
    slug = emoji_data["slug"]
    unicode_value = emoji_data["unicode"]
    url = f"{BASE_URL}/{slug}#designs"
    driver.get(url)

    try:
        panel = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//*[contains(@class, 'Tabs_tab-panel')]")
        ))
    except Exception as e:
        #print(f"Design panel not loaded for {slug}:", e)
        return

    manufacturer_sections = panel.find_elements(By.CLASS_NAME, "mb-6")
    for section in manufacturer_sections:
        # Only process sections that contain a timeline pins list
        timeline_elements = section.find_elements(By.XPATH, ".//*[contains(@class, 'EmojiTimeline_emoji-timeline-pins-list')]")
        if not timeline_elements:
            #print("Skipping section without a valid timeline:", section.get_attribute("outerHTML")[:200])
            continue
        process_manufacturer_section(section, unicode_value)

def main():
    json_path = os.path.join(DB_DIR, 'emoji_data.json')
    all_emojis = load_json_data(json_path)

    driver = webdriver.Chrome()  # Ensure chromedriver is in PATH or provide its path.
    wait = WebDriverWait(driver, TIMEOUT)
    
    # Get the keys and shuffle them
    keys = list(all_emojis.keys())
    random.shuffle(keys)

    for key in keys:
        emoji_data = all_emojis[key]
        process_emoji(driver, wait, emoji_data)

    driver.quit()

if __name__ == '__main__':
    main()
