import os
import requests
from bs4 import BeautifulSoup
import tldextract
from urllib.parse import urljoin

# ---------- SETUP FOLDER IN DOCUMENTS ----------
documents_path = os.path.expanduser("~/Documents")
OUTPUT_DIR = os.path.join(documents_path, "ScrapedLogos")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------- HEADERS ----------
HEADERS = {
    'User-Agent': 'Mozilla/5.0'
}

# ---------- FUNCTIONS ----------

def is_likely_logo(img_tag):
    alt = (img_tag.get('alt') or '').lower()
    classes = ' '.join(img_tag.get('class', [])).lower()
    src = (img_tag.get('src') or '').lower()
    return 'logo' in alt or 'logo' in classes or 'logo' in src or 'brand' in classes

def download_image(img_url, company_name):
    try:
        response = requests.get(img_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            ext = os.path.splitext(img_url.split("?")[0])[1]
            if not ext or len(ext) > 5:
                ext = '.png'
            filename = f"{company_name}{ext}"
            path = os.path.join(OUTPUT_DIR, filename)
            with open(path, 'wb') as f:
                f.write(response.content)
            print(f"[✓] Downloaded logo for {company_name}: {img_url}")
        else:
            print(f"[x] Failed to fetch image for {company_name}: {img_url}")
    except Exception as e:
        print(f"[!] Error downloading image for {company_name}: {e}")

def scrape_logo_from_url(url):
    try:
        company_name = tldextract.extract(url).domain
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        imgs = soup.find_all('img')

        for img in imgs:
            if is_likely_logo(img):
                logo_url = img.get('src')
                if logo_url:
                    full_url = urljoin(url, logo_url)
                    download_image(full_url, company_name)
                    return
        print(f"[x] No logo found for {company_name}")
    except Exception as e:
        print(f"[!] Error scraping {url}: {e}")

# ---------- USER INPUT LOOP ----------
print("Enter company URLs one by one. Type 'done' when finished:\n")
company_urls = []

while True:
    user_input = input("Enter URL: ").strip()
    if user_input.lower() == 'done':
        break
    elif user_input.startswith("http"):
        company_urls.append(user_input)
    else:
        print("Please enter a valid URL starting with http or https.")

# ---------- RUN SCRAPER ----------
print("\nStarting logo scraping...\n")
for url in company_urls:
    scrape_logo_from_url(url)

print(f"\nAll done! Logos saved to: {OUTPUT_DIR}")