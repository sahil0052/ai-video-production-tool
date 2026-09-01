import requests, json
from pathlib import Path

save_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_verified")
headers = {"User-Agent": "NishaHomesBot/5.0 (contact@nishahomes.in)"}

def search_wiki_first_photo(query, out_name):
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}",
        "gsrnamespace": "6",
        "gsrlimit": "10",
        "prop": "imageinfo",
        "iiprop": "url|mime|size",
        "format": "json"
    }
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        pages = r.json().get("query", {}).get("pages", {})
        for pid, p in pages.items():
            title = p.get("title", "")
            info = p.get("imageinfo", [{}])[0]
            u = info.get("url")
            size = info.get("size", 0)
            mime = info.get("mime", "")
            if u and ("jpeg" in mime or "png" in mime or "jpg" in mime) and size > 50000 and not "pdf" in u.lower():
                print(f"Match for '{query}' -> {title}")
                data = requests.get(u, headers=headers, timeout=15).content
                with open(save_dir / out_name, "wb") as f:
                    f.write(data)
                print(f"  [OK] Saved {out_name} ({len(data)} bytes)")
                return True
    except Exception as e:
        print(f"Error {query}: {e}")
    return False

search_wiki_first_photo("Delhi Metro train", "real_metro_train_delhi.jpg")
search_wiki_first_photo("Key in door lock", "real_key_in_door_verified.jpg")
search_wiki_first_photo("Business meeting office team", "real_business_meeting_office.jpg")
search_wiki_first_photo("DLF Cyber City", "real_cyber_city_dlf.jpg")
search_wiki_first_photo("Noida skyline", "real_noida_skyline_verified.jpg")

print("Done searching and saving!")
