from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
import json
import os
from datetime import datetime
import re
import html
import unicodedata

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_DIR = os.path.join(PROJECT_ROOT, "db")

BASE_URL = "https://emojipedia.org"
CATEGORIES = [
	"emoji-1.0",
    "emoji-2.0",
    "emoji-3.0",
    "emoji-4.0",
    "emoji-5.0",
    "emoji-11.0",
    "emoji-12.0",
    "emoji-12.1",
    "emoji-13.0",
    "emoji-13.1",
    "emoji-14.0",
    "emoji-15.0",
    "emoji-15.1",
    "emoji-16.0",
    "emoji-17.0",
    "emoji-kitchen#list",
    "gestures#list",
	"halloween#list",
	"happy#list",
	"sad#list",
	"wedding-marriage#list",
	"independence-day#list",
	"easter#list",
	"valentines-day#list",
	"fantasy-magic#list",
	"queens-birthday#list",
	"christmas#list",
	"olympics#list",
	"cinco-de-mayo#list",
	"new-years-eve#list",
	"laughter#list",
	"summer#list",
	"canada-day#list",
	"winter-olympics#list",
	"australia-day#list",
	"love#list",
	"zodiac#list",
	"guy-fawkes#list",
	"bastille-day#list",
	"chinese-new-year#list",
	"spring#list",
	"diwali#list",
	"thanksgiving#list",
	"hearts#list",
	"kisses#list",
	"couples-with-hearts#list",
	"pets#list",
	"black-friday#list",
	"juneteenth#list",
	"japanese-culture#list",
	"winter#list",
	"mothers-day#list",
	"fathers-day#list",
	"birthday#list",
	"st-patricks-day#list",
	"international-womens-day#list",
	"music#list",
	"world-emoji-day#list",
	"graduation#list",
	"carnaval#list",
	"veterans-day#list",
	"super-bowl#list",
	"ramadan#list",
	"pride#list",
	"smileys#list",
	"people#list",
	"nature#list",
	"food-drink#list",
	"activity#list",
	"travel-places#list",
	"objects#list",
	"symbols#list",
	"flags#list",
	"black-lives-matter#list",
	"dragon-boat-festival#list",
	"earth-day#list",
	"emoji-movie#list",
	"fall-autumn#list",
	"families#list",
	"handshakes#list",
	"hanukkah#list",
	"holi#list",
	"jobs-roles#list",
	"mardi-gras#list",
	"mlb-world-series#list",
	"purim#list",
	"working-from-home#list",
	"world-book-day#list",
	"world-cup#list",
]

TIMEOUT = 3  # Global timeout in seconds
SAVE_INTERVAL = 100  # Save every 1000 emojis

# -- General purpose helper functions ----------------------------------------------------------------

def setup_driver():
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def save_to_json(data, filename="emoji_data.json"):
    os.makedirs(DB_DIR, exist_ok=True)
    with open(os.path.join(DB_DIR, filename), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def slugify_clean(text):
    text = text.lower().replace("-", "_").replace(" ", "_")
    return re.sub(r"[^\w_]", "", text)  # removes punctuation but keeps letters including Unicode

def slugify_ascii(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return slugify_clean(text)

def un_normalize_slug(slug):
    return slug.replace("_", " ").title()

def remove_trailing_parenthetical(text):
    return re.sub(r"\s*\([^)]*\)$", "", text).strip()

def is_emoticon(text):
    text = text.strip()
    if not text:
        return False

    # Define sets
    allowed_basic = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ")
    punctuation_marks = set("`~!@#$%^&*()_+-=[]\\{}|;':\",./<>?")

    total = len(text)
    if total == 0:
        return False

    non_basic = sum(1 for c in text if c not in allowed_basic)
    punct_count = sum(1 for c in text if c in punctuation_marks)

    # At least half of the characters must be non-basic
    if non_basic < total / 2:
        return False

    # At least a quarter must be punctuation
    if punct_count < total / 4:
        return False

    return True

def clean_text(text):
    text = html.unescape(text)
    text = text.replace("\u00a0", " ").replace("\xa0", " ")  # non-breaking space
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def add_unique_variants(text, collection):
    clean = slugify_clean(clean_text(text))
    ascii_ = slugify_ascii(clean_text(text))
    for variant in (clean, ascii_):
        if variant not in collection:
            collection.append(variant)

def get_first_sentence(text):
    match = re.match(r"(.+?[.!?])(?:\s|$)", text)
    return match.group(1).strip() if match else text.strip()

# -- scraping helper functions -----------------------------------------------------------------------

def extract_table_data(driver, emoji_data):
    try:
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.Table_table-wrapper-border-inside-body__QiLpE table tbody tr td"))
        )
        table_rows = driver.find_elements(By.CSS_SELECTOR, "div.Table_table-wrapper-border-inside-body__QiLpE table tbody tr")
        for row in table_rows:
            cells = row.find_elements(By.CLASS_NAME, "Table_table-td__DEXBu")
            if len(cells) == 2:
                key = cells[0].text.strip()
                value = cells[1].text.strip()
                if key == "Emoji" and value:
                    emoji_data["char"] = value
                elif key == "Codepoints" and value:
                    emoji_data["unicode"] = value
                elif key == "Unicode Name" and value:
                    emoji_data["name"] = value
                    emoji_data.setdefault("aliases", []).append(value)
                elif key in ["Apple Name", "Also Known As"]:
                    emoji_data.setdefault("aliases", [])
                    emoji_data.setdefault("shortcodes", [])
                    for v in cells[1].find_elements(By.TAG_NAME, "div"):
                        text = remove_trailing_parenthetical(v.text)
                        alias = un_normalize_slug(text)
                        if alias not in emoji_data["aliases"]:
                            emoji_data["aliases"].append(alias)
                        if not is_emoticon(text):
                            add_unique_variants(text, emoji_data["shortcodes"])
    except Exception as e:
        print(f"Error extracting table data: {e}")


def extract_variation_and_related_urls(driver, url_queue, visited_urls):
    added_urls = 0
    selectors = [
        "div.flex.flex-row.gap-2 a[class*='link-wrapper']",
        "div.flex.flex-row.gap-2 a[class*='Gender_gender__8oOsm']",
        "div.flex.flex-row.flex-wrap.gap-2 a[class*='link-wrapper']"
    ]

    for selector in selectors:
        try:
            links = driver.find_elements(By.CSS_SELECTOR, selector)
            for link in links:
                url = link.get_attribute("href")
                if url and url not in visited_urls and url not in url_queue:
                    url_queue.append(url)
                    added_urls += 1
        except StaleElementReferenceException:
            print("Encountered stale element while extracting URLs.")
            continue

    if added_urls:
        print(f"Added {added_urls} new related URLs.")


def extract_description(driver, emoji_data):
    try:
        desc_container = driver.find_element(By.CSS_SELECTOR, "div.flex.flex-col.gap-3.text-left")

        try:
            warning_elem = desc_container.find_element(By.CSS_SELECTOR, "div.EmojiContent_emoji-content-alerts__Qh_Yp p")
            emoji_data["warning"] = clean_text(warning_elem.text)
        except NoSuchElementException:
            emoji_data["warning"] = ""

        html_blocks = desc_container.find_elements(By.CSS_SELECTOR, "div.HtmlContent_html-content-container__Ow2Bk")
        collected_paragraphs = []
        for block in html_blocks:
            paragraphs = block.find_elements(By.TAG_NAME, "p")
            for p in paragraphs:
                collected_paragraphs.append(clean_text(p.text))

        if collected_paragraphs:
            emoji_data["description"] = get_first_sentence(collected_paragraphs[0])
            emoji_data["description_full"] = "\n\n".join(collected_paragraphs)
        else:
            emoji_data["description"] = emoji_data["description_full"] = ""

    except (NoSuchElementException, StaleElementReferenceException):
        emoji_data["description"] = emoji_data["description_full"] = emoji_data["warning"] = ""

# -- per emoji processers -----------------------------------------------------------------------------------------------------

def process_emoji_page(driver, emoji_url, url_queue, emoji_data, visited_urls):
    driver.get(emoji_url)
    emoji_data["url"] = emoji_url
    emoji_data["slug"] = emoji_url.strip("/").split("/")[-1]
    extract_variation_and_related_urls(driver, url_queue, visited_urls)
    extract_description(driver, emoji_data)


def extract_technical_metadata(driver, emoji_url, emoji_data):
    driver.get(f"{emoji_url}#technical")
    try:
        extract_table_data(driver, emoji_data)
    except TimeoutException:
        print(f"Timeout while fetching data for {emoji_url}")

# -- starting scrape ------------------------------------------------------------------------

def extract_list_page_emoji_urls(driver, url_queue, visited_urls):
    try:
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='emojis-list-wrapper'] a[class*='link-wrapper']"))
        )
        emoji_list_wrappers = driver.find_elements(By.CSS_SELECTOR, "div[class*='emojis-list-wrapper']")
        added_urls = 0
        for wrapper in emoji_list_wrappers:
            emoji_links = wrapper.find_elements(By.CSS_SELECTOR, "a[class*='link-wrapper']")
            for link in emoji_links:
                emoji_url = link.get_attribute("href")
                if emoji_url and emoji_url not in visited_urls and emoji_url not in url_queue:
                    url_queue.append(emoji_url)
                    added_urls += 1
        if added_urls:
            print(f"Collected {added_urls} new emoji URLs from list.")
    except TimeoutException:
        print("Skipping category due to timeout.")
    except Exception as e:
        print(f"Unexpected error: {e}")

# -- Main -----------------------------------------------------------------------------------------------

def scrape_emoji_data():
    driver = setup_driver()
    url_queue = []
    visited_urls = set()
    emoji_db = {}

    for category in CATEGORIES:
        url = f"{BASE_URL}/{category}"
        print(f"Scraping category: {url}")
        driver.get(url)
        extract_list_page_emoji_urls(driver, url_queue, visited_urls)

    url_queue = list(set(url_queue))
    
    while url_queue:
        emoji_url = url_queue.pop(0)
        if emoji_url in visited_urls:
            continue
        visited_urls.add(emoji_url)
        emoji_data = {}
        
        process_emoji_page(driver, emoji_url, url_queue, emoji_data, visited_urls)
        
        # removes flashing lights
        driver.get("about:blank")  
        driver.execute_script("""
            document.body.style.backgroundColor = '#121212';
            document.body.style.color = '#ffffff';
        """)
        
        extract_technical_metadata(driver, emoji_url, emoji_data)
        
        if "char" in emoji_data:
            emoji_db[emoji_data["char"]] = emoji_data

        if len(emoji_db) % SAVE_INTERVAL == 0:
            print(f"Saving snapshot at {len(emoji_db)} emojis...")
            save_to_json(emoji_db, filename="emoji_data_snapshot.json")
            save_to_json(list(visited_urls), filename="visited_urls.json")

    driver.quit()
    return emoji_db, visited_urls

if __name__ == "__main__":
    final_data, visited = scrape_emoji_data()
    save_to_json(final_data)
    save_to_json(list(visited), filename="visited_urls.json")
    print(f"Scraped {len(final_data)} emojis and saved to {os.path.join(DB_DIR, 'emoji_data.json')}")
