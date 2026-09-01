import requests, json
from pathlib import Path

save_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_verified")
save_dir.mkdir(parents=True, exist_ok=True)

queries = [
    ("Cyber City", "real_cyber_city.jpg"),
    ("Delhi Metro viaduct", "real_delhi_metro.jpg"),
    ("Apartments in Noida", "real_noida_apartments.jpg"),
    ("House keys", "real_house_keys_door.jpg"),
    ("Blueprint architect", "real_blueprint_meeting.jpg"),
    ("Construction building concrete", "real_concrete_site.jpg"),
    ("Gurgaon skyline", "real_gurgaon_skyline.jpg")
]

headers = {"User-Agent": "NishaHomesBot/1.0 (contact@nishahomes.in)"}

for q, out_name in queries:
    api_url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {q}",
        "gsrlimit": "5",
        "prop": "imageinfo",
        "iiprop": "url|size|mime",
        "format": "json"
    }
    try:
        r = requests.get(api_url, params=params, headers=headers, timeout=10)
        pages = r.json().get("query", {}).get("pages", {})
        for page_id, p in pages.items():
            img_info = p.get("imageinfo", [{}])[0]
            u = img_info.get("url")
            size = img_info.get("size", 0)
            mime = img_info.get("mime", "")
            if u and "image" in mime and size > 40000:
                print(f"Downloading for '{q}': {u[:70]}...")
                img_data = requests.get(u, headers=headers, timeout=15).content
                with open(save_dir / out_name, "wb") as f:
                    f.write(img_data)
                print(f"  [OK] Saved {out_name} ({len(img_data)} bytes)")
                break
    except Exception as e:
        print(f"Error {q}: {e}")

print("Wikimedia search completed!")
