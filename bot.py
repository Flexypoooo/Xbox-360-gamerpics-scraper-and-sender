import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# -----------------------------
# SETTINGS
# -----------------------------
START_PAGE = 1
MAX_PAGE = 500
BASE_URL = "https://xboxgamer.pics/titles/all?page="
FOLDER = "gamerpics"
LOG_FILE = "download_log.txt"
LINKS_FILE = "downloaded_links.txt"
MAX_THREADS = 500  # Number of simultaneous downloads
DIRECT_LINK = "https://download.xboxgamer.pics/titles/584109a8/2000d.png"

os.makedirs(FOLDER, exist_ok=True)

# -----------------------------
# Selenium Setup
# -----------------------------
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# -----------------------------
# Session for requests
# -----------------------------
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

# -----------------------------
# Logging function
# -----------------------------
def log(msg):
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

# -----------------------------
# Save link function
# -----------------------------
def save_link(url):
    with open(LINKS_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

# -----------------------------
# Load already downloaded links
# -----------------------------
if os.path.exists(LINKS_FILE):
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        downloaded_links = set(line.strip() for line in f)
else:
    downloaded_links = set()

# -----------------------------
# Load page & extract real image URLs
# -----------------------------
def load_images(url):
    driver.get(url)
    time.sleep(2)

    # Scroll to load all images
    last_h = 0
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        new_h = driver.execute_script("return document.body.scrollHeight;")
        if new_h == last_h:
            break
        last_h = new_h

    soup = BeautifulSoup(driver.page_source, "html.parser")
    imgs = []

    # Extract real downloadable links
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a['href'])
        # Skip asset URLs
        if "assets.xboxgamer.pics" in href.lower():
            continue
        # Only titles PNG links
        if "/titles/" in href and href.lower().endswith(".png") and href not in downloaded_links:
            imgs.append(href)

    return imgs

# -----------------------------
# Download function
# -----------------------------
def download_image(url):
    filename = os.path.basename(urlparse(url).path)
    save_path = os.path.join(FOLDER, filename)

    try:
        r = session.get(url, timeout=15)
        r.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(r.content)

        log(f"[DOWNLOADED] {filename}")
        save_link(url)
        downloaded_links.add(url)
        return True
    except Exception as e:
        log(f"[FAILED] {filename} - {e}")
        return False

# -----------------------------
# MAIN LOOP
# -----------------------------
total_downloaded = 0

# Include the direct link first
if DIRECT_LINK not in downloaded_links:
    if download_image(DIRECT_LINK):
        total_downloaded += 1

# Loop through pages 1 → 126
for page_number in range(START_PAGE, MAX_PAGE + 1):
    current = f"{BASE_URL}{page_number}"
    log(f"\n=== PAGE {page_number}: {current} ===")

    image_urls = load_images(current)
    if not image_urls:
        log("[*] No new images on this page.")
        continue
    else:
        log(f"[*] Found {len(image_urls)} new images on this page.")

    # Multithreaded download
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = {executor.submit(download_image, url): url for url in image_urls}
        for future in as_completed(futures):
            if future.result():
                total_downloaded += 1

    time.sleep(1)  # polite delay

driver.quit()

log(f"\n[*] TOTAL DOWNLOADED: {total_downloaded}")
log(f"[*] All done! Links saved in {LINKS_FILE}")
