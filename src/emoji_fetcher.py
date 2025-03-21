import os
import re
import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

# Configuration
CONFIG = [
    { "output_folder": "Apple", "url": "https://emojipedia.org/apple" },
    { "output_folder": "au by KDDI", "url": "https://emojipedia.org/au-kddi" },
    { "output_folder": "Bluesky", "url": "https://emojipedia.org/bluesky" },
    { "output_folder": "Clubhouse", "url": "https://emojipedia.org/clubhouse" },
    { "output_folder": "Discord", "url": "https://emojipedia.org/discord" },
    { "output_folder": "Docomo", "url": "https://emojipedia.org/docomo" },
    { "output_folder": "Dropbox", "url": "https://emojipedia.org/dropbox" },
    { "output_folder": "emojidex", "url": "https://emojipedia.org/emojidex" },
    { "output_folder": "Emojipedia Sample Images", "url": "https://emojipedia.org/emojipedia" },
    { "output_folder": "Facebook", "url": "https://emojipedia.org/facebook" },
    { "output_folder": "GitHub", "url": "https://emojipedia.org/github" },
    { "output_folder": "Noto", "url": "https://emojipedia.org/google" },
    { "output_folder": "HTC", "url": "https://emojipedia.org/htc" },
    { "output_folder": "Huawei", "url": "https://emojipedia.org/huawei" },
    { "output_folder": "Icons8", "url": "https://emojipedia.org/icons8" },
    { "output_folder": "Instagram", "url": "https://emojipedia.org/instagram" },
    { "output_folder": "JoyPixels", "url": "https://emojipedia.org/joypixels" },
    { "output_folder": "JoyPixels Animations", "url": "https://emojipedia.org/joypixels-animations" },
    { "output_folder": "LG", "url": "https://emojipedia.org/lg" },
    { "output_folder": "LinkedIn", "url": "https://emojipedia.org/linkedin" },
    { "output_folder": "Mastodon", "url": "https://emojipedia.org/mastodon" },
    { "output_folder": "Messenger", "url": "https://emojipedia.org/messenger" },
    { "output_folder": "Segoe", "url": "https://emojipedia.org/microsoft/windows-11" }, #i know what it looks like but this was the only update on windows 11 which had these so its most up to date
    { "output_folder": "FluentFlat", "url": "https://emojipedia.org/microsoft" },
    { "output_folder": "Fluent3D", "url": "https://emojipedia.org/microsoft-3D-fluent" },
    { "output_folder": "Mozilla", "url": "https://emojipedia.org/mozilla" },
    { "output_folder": "MSN Messenger", "url": "https://emojipedia.org/msn-messenger" },
    { "output_folder": "NEC", "url": "https://emojipedia.org/nec" },
    { "output_folder": "Nintendo", "url": "https://emojipedia.org/nintendo" },
    { "output_folder": "OpenMoji", "url": "https://emojipedia.org/openmoji" },
    { "output_folder": "Panasonic", "url": "https://emojipedia.org/panasonic" },
    { "output_folder": "RedNote", "url": "https://emojipedia.org/rednote" },
    { "output_folder": "Roblox", "url": "https://emojipedia.org/roblox" },
    { "output_folder": "Samsung", "url": "https://emojipedia.org/samsung" },
    { "output_folder": "SerenityOS", "url": "https://emojipedia.org/serenityos" },
    { "output_folder": "Sharp", "url": "https://emojipedia.org/sharp" },
    { "output_folder": "Signal", "url": "https://emojipedia.org/signal" },
    { "output_folder": "SinaWeibo", "url": "https://emojipedia.org/sina-weibo" },
    { "output_folder": "Skype", "url": "https://emojipedia.org/skype" },
    { "output_folder": "Slack", "url": "https://emojipedia.org/slack" },
    { "output_folder": "Snapchat", "url": "https://emojipedia.org/snapchat" },
    { "output_folder": "SoftBank", "url": "https://emojipedia.org/softbank" },
    { "output_folder": "SonyPlaystation", "url": "https://emojipedia.org/sony" },
    { "output_folder": "Telegram", "url": "https://emojipedia.org/telegram" },
    { "output_folder": "TikTok", "url": "https://emojipedia.org/tiktok" },
    { "output_folder": "Tinder", "url": "https://emojipedia.org/tinder" },
    { "output_folder": "TossFace", "url": "https://emojipedia.org/toss-face" },
    { "output_folder": "Twitch", "url": "https://emojipedia.org/twitch" },
    { "output_folder": "TwitterEmojiStickers", "url": "https://emojipedia.org/twitter-emoji-stickers" },
    { "output_folder": "Twemoji", "url": "https://emojipedia.org/twitter" },
    { "output_folder": "Viber", "url": "https://emojipedia.org/viber" },
    { "output_folder": "VinSmart", "url": "https://emojipedia.org/vinsmart" },
    { "output_folder": "VK", "url": "https://emojipedia.org/vk" },
    { "output_folder": "WeChat", "url": "https://emojipedia.org/wechat" },
    { "output_folder": "WhatsApp", "url": "https://emojipedia.org/whatsapp" },
    { "output_folder": "Yahoo! Messenger", "url": "https://emojipedia.org/yahoo" },
    { "output_folder": "YoStatus", "url": "https://emojipedia.org/yo-status" },
    { "output_folder": "YouTube", "url": "https://emojipedia.org/youtube" },
    { "output_folder": "Zoom", "url": "https://emojipedia.org/zoom" }
]
# Define project paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "Assets")

# --- Scraper -------------------------------------------------------------------------------------

def setup_driver():
    """Sets up the Selenium WebDriver."""
    chrome_options = Options()
    
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")  # Suppress logs
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def extract_emoji_urls(driver, collected_urls):
    """Extracts all emoji URLs currently visible in the grid while handling stale elements."""
    new_urls = set()
    
    try:
        # Locate all emoji anchor elements (refreshing elements each time)
        elements = driver.find_elements(By.XPATH, "//a[contains(@class, 'Emoji_emoji__')]")
        
        for elem in elements:
            try:
                # Refresh element reference before getting attributes
                data_src = elem.get_attribute("data-src")  # Primary source
                background_url = elem.get_attribute("style")  # Background-image fallback
                
                # Extract URL from style attribute
                if background_url and "url(" in background_url:
                    background_url = background_url.split('url("')[1].split('")')[0]
                
                # Prioritize data-src if available
                url = data_src or background_url
                
                if url and url.endswith(".webp") and url not in collected_urls:
                    new_urls.add(url)

            except StaleElementReferenceException:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Warning: Stale element encountered, skipping...")
                continue  # Skip this element and continue with others
                
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Error in extract_emoji_urls: {e}")
    
    return new_urls

def scroll_and_collect(driver, page_url):
    """Closes popup if present, then scrolls through the page to trigger all emoji image loads."""
    driver.get(page_url)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sleeping for 1 seconds...")
    time.sleep(1)  # Initial wait for page load
    
    # Check for popup and close it
    try:
        close_button = driver.find_element(By.XPATH, "//span[@class='zw3zih' and text()='×']")
        driver.execute_script("arguments[0].click();", close_button)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Sleeping for 1 seconds...")
        time.sleep(0.5)  # Allow time for popup to close
    except:
        print("No popup found or already closed.")
    
    collected_urls = set()
    retries = 0

    last_scroll_position = driver.execute_script("return window.pageYOffset + window.innerHeight")  # ✅ Track actual scroll position

    while retries < 10:  # ✅ More flexible stopping condition
        new_urls = extract_emoji_urls(driver, collected_urls)
        
        if new_urls:
            collected_urls.update(new_urls)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Found {len(new_urls)} new emojis. Total: {len(collected_urls)}")
            retries = 0  # Reset retries since we got new data
        else:
            retries += 1  # If no new emojis, count it as a retry

        # Scroll down slightly
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(0.2)  # Small delay to allow new elements to appear

        # ✅ Check if we actually moved down
        new_scroll_position = driver.execute_script("return window.pageYOffset + window.innerHeight")
        if new_scroll_position == last_scroll_position:
            retries += 2  # ✅ If scrolling doesn't change, increase retries faster
        else:
            last_scroll_position = new_scroll_position  # ✅ Update the last known scroll position
        
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Finished. Total emojis collected: {len(collected_urls)}")
    return list(collected_urls)

def save_urls(urls, filepath):
    """Saves the list of URLs to a file."""
    with open(filepath, "w", encoding="utf-8") as f:
        for url in urls:
            f.write(url + "\n")
    print(f"Saved {len(urls)} emoji URLs to {filepath}")

# --- URL -> PNG -------------------------------------------------------------------------------------

def convert_url(webp_url):
    """
    Converts a .webp emoji URL into the correct .png format.
    Example:
    Input:  https://em-content.zobj.net/thumbs/60/serenityos/392/red-envelope_1f9e7.webp
    Output: https://em-content.zobj.net/source/serenityos/392/red-envelope_1f9e7.png
    """
    if "thumbs/60" in webp_url and webp_url.endswith(".webp"):
        png_url = webp_url.replace("thumbs/60", "source").replace(".webp", ".png")
        return png_url
    return None  # Return None if it can't be converted

def extract_filename(png_url):
    """
    Extracts the correct Unicode-based filename from a given PNG URL.
    - Ensures format is `<code>-<code>.png`
    - Uses start/stop indexes to remove trailing garbage Unicode
    - Filters out false matches (e.g., words like "face", "feed", "peace")
    - If only **one** valid Unicode match exists, return it directly.
    """
    filename = png_url.split("/")[-1]  # Get last part of URL (e.g., "face-with-rolling-eyes_1f644.png")
    filename_no_ext = filename.replace(".png", "")  # Temporarily remove .png

    # If the filename contains exactly one underscore `_`, return the last Unicode match  ex: `pig-face_1f437.png`
    if filename_no_ext.count("_") == 1:
        return filename_no_ext.split("_")[-1] + ".png"

    # Regex pattern to extract potential Unicode sequences (4-5 hex digits)
    possible_matches = re.findall(r'([0-9a-fA-F]{4,5})', filename_no_ext)

    if not possible_matches:
        raise ValueError(f"Could not extract Unicode from: {filename}")

    valid_unicode_matches = []

    for match in possible_matches:
        start_index = filename_no_ext.find(match)  # Find where it appears

        # Check if everything after this match is valid Unicode (`0-9a-fA-F-`)
        valid_after = all(c in "0123456789abcdefABCDEF-_" for c in filename_no_ext[start_index + len(match):])

        if valid_after:
            valid_unicode_matches.append(match)

    if not valid_unicode_matches:
        raise ValueError(f"Filtered out all Unicode matches from: {filename}")

    # Find where the first Unicode sequence starts
    first_match = valid_unicode_matches[0]
    start_index = filename.find(first_match)  # Position in original filename

    # Look ahead for `_` or `.png` to determine where to stop
    stop_index = len(filename)  # Default: Stop at the end
    if "_" in filename[start_index:]:
        stop_index = filename.index("_", start_index)  # Stop at first `_`
    elif ".png" in filename[start_index:]:
        stop_index = filename.index(".png", start_index)  # Stop at `.png`

    # Extract the correct part of the filename
    clean_filename = filename[start_index:stop_index] + ".png"

    return clean_filename

def download_image(url, save_path):
    """
    Downloads an image from the given URL and saves it to the specified path.
    """
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)
        
        with open(save_path, "wb") as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Downloaded: {save_path}")
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Failed to download {url}: {e}")

# --- Main -------------------------------------------------------------------------------------

def process_platform(driver, platform_config):
    """Handles scraping, saving, and downloading emojis for a single platform."""
    output_folder = platform_config["output_folder"]
    page_url = platform_config["url"]
    
    # Set paths for saving files
    png_folder = os.path.join(ASSETS_DIR, "PNGs", output_folder)
    url_list_file = os.path.join(png_folder, "emoji_urls.txt")
    
    os.makedirs(png_folder, exist_ok=True)  # Ensure output directory exists
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Processing: {output_folder} ({page_url})")
    
    emoji_urls = scroll_and_collect(driver, page_url)
    
    if not emoji_urls:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] No emoji URLs found for {output_folder}.")
        return
    
    # Save URL list for debugging
    with open(url_list_file, "w", encoding="utf-8") as f:
        for url in emoji_urls:
            f.write(url + "\n")
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Saved URL list for {output_folder}.")
    
    # Convert URLs & Download Images
    for webp_url in emoji_urls:
        png_url = convert_url(webp_url)
        if png_url:
            filename = extract_filename(png_url)
            save_path = os.path.join(png_folder, filename)
            
            if not os.path.exists(save_path):  # ✅ Skip if file already exists
                download_image(png_url, save_path)
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Skipped (already exists): {save_path}")
    
def main():
    """Runs the scraper for all platforms in the CONFIG list."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Launching Selenium...")

    driver = setup_driver()
    
    for platform in CONFIG:
        process_platform(driver, platform)

    driver.quit()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Scraping complete.")

if __name__ == "__main__":
    main()