import os
import json
import re
from serpapi import GoogleSearch
from config import SERPAPI_KEY

print(" Starting scraping script...")

# SETTINGS
SEARCH_QUERY = "screen printing Vancouver"
NUM_RESULTS = 22

# Containers
places = []
reviews = {}
seen_brands = set()

# Clean unicode in hours
def clean_hours(hours_raw):
    if not hours_raw or hours_raw == "N/A":
        return "Hours not available"
    return hours_raw.replace('\u22c5', '|').replace('\u202f', ' ').strip()

# Extract normalized brand key (first 2 words lowercased, no punctuation)
def extract_brand_key(name):
    name_clean = re.sub(r'\W+', ' ', name).lower().strip()
    words = name_clean.split()
    return ''.join(words[:2])  

# Step 1: Query Google Maps
print(f"🔍 Querying Google Maps for: '{SEARCH_QUERY}'")

search = GoogleSearch({
    "engine": "google_maps",
    "q": SEARCH_QUERY,
    "type": "search",
    "hl": "en",
    "api_key": SERPAPI_KEY
})

results = search.get_dict()

# Step 2: Verify results
if "local_results" not in results:
    print("No local_results found.")
    print(json.dumps(results, indent=2))
    exit()

print(f" Found {len(results['local_results'])} local results. Processing up to {NUM_RESULTS}...")

# Step 3: Process each result
for idx, result in enumerate(results["local_results"][:NUM_RESULTS]):
    try:
        print(f"➡️ {idx+1}. {result['title']}")
        data_id = re.sub(r'\W+', '_', result["title"].lower().strip())

        # Use stronger brand key
        brand_key = extract_brand_key(result["title"])
        if brand_key in seen_brands:
            print(f"⚠️ Skipping duplicate brand: {result['title']}")
            continue
        seen_brands.add(brand_key)

        raw_hours = result.get("hours", "N/A")
        formatted_hours = clean_hours(raw_hours)

        places.append({
            "id": data_id,
            "name": result["title"],
            "address": result.get("address", "N/A"),
            "phone": result.get("phone", "N/A"),
            "hours": formatted_hours,
            "image": data_id,
            "website": result.get("website", "N/A")
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
        print(f" Error on result {idx+1}: {e}")

# Step 4: Output places.js
with open("places.js", "w") as f:
    f.write("export const places = [\n")
    for i, p in enumerate(places):
        f.write("  {\n")
        f.write(f'    id: "{p["id"]}",\n')
        f.write(f'    name: "{p["name"]}",\n')
        f.write(f'    address: "{p["address"]}",\n')
        f.write(f'    phone: "{p["phone"]}",\n')
        f.write(f'    hours: "{p["hours"]}",\n')
        f.write(f'    image: {p["image"]},\n')
        f.write(f'    website: "{p["website"]}"\n')
        f.write("  }" + (",\n" if i < len(places)-1 else "\n"))
    f.write("];\n")
print("✅ places.js written.")

# Step 5: Output reviews.js
with open("reviews.js", "w", encoding="utf-8") as f:
    f.write("export const reviews = {\n")
    for i, (place_id, review_list) in enumerate(reviews.items()):
        f.write(f"  {place_id}: [\n")
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
print(" reviews.js written.")

# Final log
print(f" Done! {len(places)} unique brands and {len(reviews)} review sets saved.")