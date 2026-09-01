import requests, json
from pathlib import Path

save_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_verified")
save_dir.mkdir(parents=True, exist_ok=True)

# Wikimedia Commons API search & fetch highest resolution original file
def fetch_wikimedia_image(query, filename):
    try:
        search_url = "https://commons.wikimedia.org/w/api.php"
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": "6",
            "gsrlimit": "5",
            "prop": "imageinfo",
            "iiprop": "url|mime|size",
            "format": "json"
        }
        r = requests.get(search_url, params=params, headers={"User-Agent": "NishaHomesProduction/1.0"}, timeout=10)
        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            img_info = page.get("imageinfo", [{}])[0]
            img_url = img_info.get("url")
            mime = img_info.get("mime", "")
            if img_url and ("jpeg" in mime or "png" in mime or "jpg" in mime):
                print(f"Downloading {filename} from: {img_url[:80]}...")
                img_data = requests.get(img_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15).content
                if len(img_data) > 50000:
                    with open(save_dir / filename, "wb") as f:
                        f.write(img_data)
                    print(f"  [OK] Saved {filename} ({len(img_data)} bytes)")
                    return True
    except Exception as e:
        print(f"  [ERROR] {query}: {e}")
    return False

# Targeted search for genuine real photos
fetch_wikimedia_image("Cyber City Gurgaon skyline expressway", "real_cyber_city_gurgaon.jpg")
fetch_wikimedia_image("Delhi Metro elevated viaduct Gurgaon", "real_delhi_metro_elevated.jpg")
fetch_wikimedia_image("Noida residential high rise apartment buildings", "real_noida_highrise_society.jpg")
fetch_wikimedia_image("House key in door handover", "real_key_handover_verified.jpg")
fetch_wikimedia_image("Real estate agent client meeting consultation", "real_advisory_consultation_verified.jpg")
fetch_wikimedia_image("Apartment living room interior modern", "real_apartment_interior_verified.jpg")
fetch_wikimedia_image("Building under construction concrete Delhi", "real_construction_underway.jpg")
fetch_wikimedia_image("Gurgaon Golf Course Road skyline", "real_golf_course_road.jpg")

print("Finished fetching verified real photos!")
