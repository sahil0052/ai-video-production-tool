import requests, json
from pathlib import Path

save_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_verified")
save_dir.mkdir(parents=True, exist_ok=True)
headers = {"User-Agent": "NishaHomesBot/3.0 (dev@nishahomes.in)"}

def get_wiki_image_by_search(query, filename):
    print(f"Searching: {query}...")
    s_url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srnamespace": "6",
        "srlimit": "8",
        "format": "json"
    }
    r = requests.get(s_url, params=params, headers=headers, timeout=10)
    items = r.json().get("query", {}).get("search", [])
    for it in items:
        t = it["title"]
        if any(t.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png"]):
            print(f"  Fetching info for: {t}")
            ip = {
                "action": "query",
                "titles": t,
                "prop": "imageinfo",
                "iiprop": "url|size",
                "format": "json"
            }
            r2 = requests.get(s_url, params=ip, headers=headers, timeout=10)
            pages = r2.json().get("query", {}).get("pages", {})
            for pid, p in pages.items():
                info = p.get("imageinfo", [{}])[0]
                u = info.get("url")
                size = info.get("size", 0)
                if u and size > 50000:
                    data = requests.get(u, headers=headers, timeout=15).content
                    with open(save_dir / filename, "wb") as f:
                        f.write(data)
                    print(f"  [OK] Saved {filename} from {t} ({len(data)} bytes)")
                    return True
    return False

get_wiki_image_by_search("Noida Sector residential apartments high rise", "real_noida_highrise_real.jpg")
get_wiki_image_by_search("Apartments Gurgaon DLF Phase", "real_gurgaon_apartments_real.jpg")
get_wiki_image_by_search("High-rise residential buildings in India", "real_indian_highrise_towers.jpg")
get_wiki_image_by_search("Holding keys door", "real_holding_keys.jpg")
get_wiki_image_by_search("Consultation meeting business", "real_consultation_meeting.jpg")
get_wiki_image_by_search("Under construction building concrete", "real_concrete_building_india.jpg")

print("Finished searching Wikimedia!")
