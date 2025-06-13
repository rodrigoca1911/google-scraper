import os
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests
from serpapi import GoogleSearch
from config import SERPAPI_KEY  # Add your SerpAPI key to config.py

# ─── SETTINGS ──────────────────────────────────────────────────────────────
SEARCH_QUERY = "screen printing Vancouver"
NUM_RESULTS = 20
LOGO_DIR = "scraped_logos"
os.makedirs(LOGO_DIR, exist_ok=True)

# ─── HELPERS ───────────────────────────────────────────────────────────────
def clean_hours(hours_raw):
    if not hours_raw or hours_raw == "N/A":
        return "Hours not available"
    return hours_raw.replace('\u22c5', '|').replace('\u202f', ' ').strip()

def extract_brand_key(name):
    name_clean = re.sub(r'\W+', ' ', name).lower().strip()
    words = name_clean.split()
    return ''.join(words[:2])

def generate_data_id(name):
    return re.sub(r'\W+', '-', name.lower().strip()).strip('-')

def is_likely_logo(img_tag):
    alt = (img_tag.get('alt') or '').lower()
    classes = ' '.join(img_tag.get('class', [])).lower()
    src = (img_tag.get('src') or '').lower()
    return 'logo' in alt or 'logo' in classes or 'logo' in src or 'brand' in classes

def scrape_logo(website_url, filename_base):
    try:
        print(f"🌐 Scraping logo from {website_url}")
        response = requests.get(website_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        img_tags = soup.find_all('img')

        selected_img_url = None
        fallback_img_url = None

        for img in img_tags:
            img_src = img.get('src')
            if not img_src:
                continue
            img_url = urljoin(website_url, img_src)

            ext = os.path.splitext(img_url.split("?")[0])[1].lower()
            if ext == '.gif':
                continue

            if is_likely_logo(img):
                selected_img_url = img_url
                break

            if not fallback_img_url:
                fallback_img_url = img_url

        final_img_url = selected_img_url or fallback_img_url
        if final_img_url:
            img_data = requests.get(final_img_url, timeout=20).content
            ext = os.path.splitext(final_img_url.split("?")[0])[1].lower()
            if not ext or len(ext) > 5 or ext == '.gif':
                ext = '.png'

            image_filename = f"{filename_base}{ext}"
            filepath = os.path.join(LOGO_DIR, image_filename)
            with open(filepath, 'wb') as f:
                f.write(img_data)

            print(f"🖼️ Logo saved: {filepath}")
            return filename_base  # return image name without extension
        else:
            print(f"⚠️ No suitable image found on {website_url}")
            return None

    except Exception as e:
        print(f"❌ Error scraping logo from {website_url}: {e}")
        return None

# ─── MAIN ──────────────────────────────────────────────────────────────────
print("🔍 Querying Google Maps for:", SEARCH_QUERY)

search = GoogleSearch({
    "engine": "google_maps",
    "q": SEARCH_QUERY,
    "type": "search",
    "hl": "en",
    "api_key": SERPAPI_KEY
})

results = search.get_dict()
if "local_results" not in results:
    print("No local_results found.")
    print(json.dumps(results, indent=2))
    exit()

places = []
reviews = {}
seen_brands = set()

local_results = results["local_results"]
print(f" Found {len(local_results)} local results. Processing up to {NUM_RESULTS}...")

for idx, result in enumerate(local_results[:NUM_RESULTS]):
    try:
        print(f"\n➡️ {idx+1}. {result['title']}")
        data_id = generate_data_id(result["title"])
        brand_key = extract_brand_key(result["title"])
        if brand_key in seen_brands:
            print(f"⚠️ Skipping duplicate brand: {result['title']}")
            continue
        seen_brands.add(brand_key)

        raw_hours = result.get("hours", "N/A")
        formatted_hours = clean_hours(raw_hours)
        website = result.get("website", "N/A")

        image_key = data_id
        if website.startswith("http"):
            scraped = scrape_logo(website, data_id)
            if scraped:
                image_key = scraped

        places.append({
            "id": data_id,
            "name": result["title"],
            "address": result.get("address", "N/A"),
            "phone": result.get("phone", "N/A"),
            "hours": formatted_hours,
            "image": image_key,
            "website": website
        })

        print(f"📝 Getting reviews for {result['title']}")
        detail_search = GoogleSearch({
            "engine": "google_maps_reviews",
            "data_id": result["data_id"],
            "hl": "en",
            "api_key": SERPAPI_KEY
        })

        detail_results = detail_search.get_dict()
        review_list = []
        for review in detail_results.get("reviews", [])[:3]:
            snippet = review.get("snippet", "").replace('"', '\\"')
            review_list.append({
                "snippet": snippet,
                "author": review.get("user", {}).get("name", "Anonymous"),
                "link": review.get("link", "https://google.com")
            })

        reviews[data_id] = review_list
        print(f" Got {len(review_list)} reviews")

    except Exception as e:
        print(f"❌ Error on result {idx+1}: {e}")

# ─── OUTPUT places.js ───────────────────────────────────────────────────────
with open("places.js", "w") as f:
    f.write("export const places = [\n")
    for i, p in enumerate(places):
        f.write("  {\n")
        f.write(f'    id: "{p["id"]}",\n')
        f.write(f'    name: "{p["name"]}",\n')
        f.write(f'    address: "{p["address"]}",\n')
        f.write(f'    phone: "{p["phone"]}",\n')
        f.write(f'    hours: "{p["hours"]}",\n')
        f.write(f'    image: {p["image"]},\n')  # Unquoted image value
        f.write(f'    website: "{p["website"]}"\n')
        f.write("  }" + (",\n" if i < len(places)-1 else "\n"))
    f.write("];\n")
print("✅ places.js written.")

# ─── OUTPUT reviews.js ──────────────────────────────────────────────────────
with open("reviews.js", "w", encoding="utf-8") as f:
    f.write("export const reviews = {\n")
    for i, (place_id, review_list) in enumerate(reviews.items()):
        f.write(f'  "{place_id}": [\n')
        for j, r in enumerate(review_list):
            snippet = r["snippet"].replace("`", "\\`").strip()
            author = r["author"].replace('"', '\\"')
            link = r["link"]
            f.write("    {\n")
            f.write(f"      snippet: `{snippet}`,\n")
            f.write(f'      author: "{author}",\n')
            f.write(f'      link: "{link}"\n')
            f.write("    }" + (",\n" if j < len(review_list)-1 else "\n"))
        f.write("  ]" + (",\n" if i < len(reviews)-1 else "\n"))
    f.write("};\n")
print("✅ reviews.js written.")

# ─── DONE ───────────────────────────────────────────────────────────────────
print(f"\n🎉 Done! {len(places)} businesses scraped with logos saved to: {LOGO_DIR}")