import requests, json
from pathlib import Path

save_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_verified")
save_dir.mkdir(parents=True, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def search_unsplash(query, out_name):
    url = f"https://unsplash.com/napi/search/photos?query={query}&per_page=5"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        results = data.get("results", [])
        if results:
            img_url = results[0]["urls"]["raw"] + "&w=1920&q=85&auto=format&fit=crop"
            desc = results[0].get("alt_description", "")
            print(f"Found for '{query}' ({desc}): {img_url[:60]}...")
            img_data = requests.get(img_url, headers=headers, timeout=15).content
            with open(save_dir / out_name, "wb") as f:
                f.write(img_data)
            print(f"  [OK] Saved {out_name} ({len(img_data)} bytes)")
            return True
    except Exception as e:
        print(f"Error {query}: {e}")
    return False

# Search queries for authentic real photos
search_unsplash("building construction concrete scaffolding", "real_concrete_construction.jpg")
search_unsplash("modern apartment buildings residential exterior", "real_modern_society.jpg")
search_unsplash("highway traffic city lights night aerial", "real_expressway_traffic.jpg")
search_unsplash("metro train station modern city", "real_metro_train.jpg")
search_unsplash("modern residential towers skyline", "real_residential_highrise.jpg")
search_unsplash("holding keys house real estate", "real_keys_in_hand.jpg")
search_unsplash("luxury modern apartment living room interior", "real_apartment_living_room.jpg")
search_unsplash("architectural meeting blueprint consultation office", "real_floorplan_consultation.jpg")
search_unsplash("city skyline sunset towers aerial view", "real_city_skyline_dusk.jpg")

print("Unsplash search and download complete!")
