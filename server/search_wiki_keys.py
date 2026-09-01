import requests, json
from pathlib import Path

save_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_verified")
headers = {"User-Agent": "NishaHomesBot/6.0 (dev@nishahomes.in)"}

def download_wiki_file_search(query, out_name):
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": f"filetype:bitmap {query}",
        "srnamespace": "6",
        "srlimit": "10",
        "format": "json"
    }
    r = requests.get(url, params=params, headers=headers, timeout=10)
    items = r.json().get("query", {}).get("search", [])
    for it in items:
        t = it["title"]
        print(f"Checking {t} for '{query}'...")
        r2 = requests.get(url, params={"action": "query", "titles": t, "prop": "imageinfo", "iiprop": "url|mime|size", "format": "json"}, headers=headers, timeout=10)
        pages = r2.json().get("query", {}).get("pages", {})
        for pid, p in pages.items():
            info = p.get("imageinfo", [{}])[0]
            u = info.get("url")
            size = info.get("size", 0)
            mime = info.get("mime", "")
            if u and ("jpeg" in mime or "png" in mime or "jpg" in mime) and size > 40000 and not "pdf" in u.lower() and not "icon" in u.lower():
                print(f"  Downloading: {u[:70]}...")
                data = requests.get(u, headers=headers, timeout=15).content
                with open(save_dir / out_name, "wb") as f:
                    f.write(data)
                print(f"  [OK] Saved {out_name} ({len(data)} bytes)")
                return True
    return False

download_wiki_file_search("Keys in door", "real_key_in_door_macro.jpg")
download_wiki_file_search("Hand holding key", "real_hand_with_key.jpg")
download_wiki_file_search("Architect blueprint review table", "real_blueprint_meeting.jpg")
download_wiki_file_search("Real estate consultation", "real_consultation_scene.jpg")

print("Done searching & saving!")
