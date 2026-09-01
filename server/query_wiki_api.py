import requests
from pathlib import Path

save_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_verified")
save_dir.mkdir(parents=True, exist_ok=True)

titles_map = {
    "Cyber City Gurugram.jpg": "real_gurgaon_cybercity.jpg",
    "Rapid Metro Gurgaon.jpg": "real_metro_connectivity.jpg",
    "Noida Expressway skyline.jpg": "real_noida_skyline.jpg",
    "Apartment buildings in India.jpg": "real_apartment_towers.jpg",
    "Construction of high rise building.jpg": "real_construction_site.jpg",
    "Keys to the house.jpg": "real_keys_real.jpg"
}

headers = {"User-Agent": "NishaHomesBot/1.0 (contact@nishahomes.in)"}

for title, out_name in titles_map.items():
    api_url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": f"File:{title}",
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json"
    }
    try:
        r = requests.get(api_url, params=params, headers=headers, timeout=10)
        pages = r.json().get("query", {}).get("pages", {})
        for k, v in pages.items():
            if "imageinfo" in v:
                u = v["imageinfo"][0]["url"]
                print(f"Found URL for {title}: {u[:60]}...")
                img_data = requests.get(u, headers=headers, timeout=15).content
                with open(save_dir / out_name, "wb") as f:
                    f.write(img_data)
                print(f"  [OK] Saved {out_name} ({len(img_data)} bytes)")
    except Exception as e:
        print(f"Error {title}: {e}")

# Also search by category
categories = [
    ("Gurgaon skyline", "real_gurgaon_skyline.jpg"),
    ("Noida high-rise", "real_noida_highrise.jpg"),
    ("Indian residential architecture", "real_indian_society.jpg")
]

for cat, out_name in categories:
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": cat,
        "gsrlimit": "3",
        "prop": "imageinfo",
        "iiprop": "url|size",
        "format": "json"
    }
    try:
        r = requests.get(api_url, params=params, headers=headers, timeout=10)
        pages = r.json().get("query", {}).get("pages", {})
        for k, v in pages.items():
            if "imageinfo" in v:
                u = v["imageinfo"][0]["url"]
                if u.endswith((".jpg", ".png", ".jpeg")):
                    img_data = requests.get(u, headers=headers, timeout=15).content
                    if len(img_data) > 50000:
                        with open(save_dir / out_name, "wb") as f:
                            f.write(img_data)
                        print(f"  [OK] Saved category {cat} -> {out_name} ({len(img_data)} bytes)")
                        break
    except Exception as e:
        print(f"Error category {cat}: {e}")

print("Done querying Wikimedia API!")
