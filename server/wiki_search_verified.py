import requests, json
from pathlib import Path

save_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_verified")
save_dir.mkdir(parents=True, exist_ok=True)

headers = {"User-Agent": "NishaHomesBot/2.0 (info@nishahomes.in)"}

def search_and_download_wiki(query, filename):
    print(f"Searching Wikimedia for '{query}'...")
    s_url = "https://commons.wikimedia.org/w/api.php"
    s_params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srnamespace": "6",
        "srlimit": "5",
        "format": "json"
    }
    r = requests.get(s_url, params=s_params, headers=headers, timeout=10)
    results = r.json().get("query", {}).get("search", [])
    for res in results:
        title = res["title"]
        print(f"  Checking title: {title}")
        i_params = {
            "action": "query",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|mime|size",
            "format": "json"
        }
        r2 = requests.get(s_url, params=i_params, headers=headers, timeout=10)
        pages = r2.json().get("query", {}).get("pages", {})
        for pid, page in pages.items():
            info = page.get("imageinfo", [{}])[0]
            u = info.get("url")
            mime = info.get("mime", "")
            size = info.get("size", 0)
            if u and ("jpeg" in mime or "png" in mime or "jpg" in mime) and size > 40000 and not "logo" in title.lower():
                print(f"  Downloading: {u[:70]}...")
                data = requests.get(u, headers=headers, timeout=15).content
                with open(save_dir / filename, "wb") as f:
                    f.write(data)
                print(f"  [OK] Saved {filename} ({len(data)} bytes)")
                return True
    return False

search_and_download_wiki("Cyber City Gurgaon", "real_cyber_city_gurgaon.jpg")
search_and_download_wiki("Delhi Metro train elevated", "real_delhi_metro_elevated.jpg")
search_and_download_wiki("Noida residential skyline apartments", "real_noida_skyline.jpg")
search_and_download_wiki("Building construction concrete frame scaffolding", "real_concrete_scaffolding.jpg")
search_and_download_wiki("House key in lock keyhole", "real_key_in_lock.jpg")
search_and_download_wiki("Architect floor plan table discussion", "real_floorplan_meeting.jpg")
search_and_download_wiki("Modern apartment living room", "real_modern_living_room.jpg")

print("Finished search & download!")
