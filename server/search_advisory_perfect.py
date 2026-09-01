import requests, json
from pathlib import Path

save_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_verified")
headers = {"User-Agent": "NishaHomesBot/8.0 (contact@nishahomes.in)"}

search_queries = [
    "Architects discussing plans office",
    "People looking at architectural drawings",
    "Real estate closing document signing",
    "Business meeting discussion desk laptop",
    "Architectural blueprint table meeting"
]

for sq in search_queries:
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": f"filetype:bitmap {sq}",
        "srnamespace": "6",
        "srlimit": "5",
        "format": "json"
    }
    r = requests.get(url, params=params, headers=headers, timeout=10)
    items = r.json().get("query", {}).get("search", [])
    for it in items:
        t = it["title"]
        r2 = requests.get(url, params={"action": "query", "titles": t, "prop": "imageinfo", "iiprop": "url|size|mime", "format": "json"}, headers=headers, timeout=10)
        pages = r2.json().get("query", {}).get("pages", {})
        for pid, p in pages.items():
            info = p.get("imageinfo", [{}])[0]
            u = info.get("url")
            size = info.get("size", 0)
            mime = info.get("mime", "")
            if u and ("jpeg" in mime or "png" in mime or "jpg" in mime) and size > 40000 and not "pdf" in u.lower():
                print(f"Match for '{sq}' -> {t}: {u[:70]}")
                data = requests.get(u, headers=headers, timeout=15).content
                with open(save_dir / "real_advisory_table_perfect.jpg", "wb") as f:
                    f.write(data)
                print(f"  [OK] Saved real_advisory_table_perfect.jpg ({len(data)} bytes)")
                break
        if (save_dir / "real_advisory_table_perfect.jpg").exists():
            break
    if (save_dir / "real_advisory_table_perfect.jpg").exists():
        break

print("Advisory search complete!")
