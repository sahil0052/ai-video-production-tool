import requests
from pathlib import Path

save_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_verified")
headers = {"User-Agent": "NishaHomesBot/9.0 (contact@nishahomes.in)"}

candidates = [
    "Meeting with an architect.jpg",
    "Architectural drawing review.jpg",
    "Business meeting in office.jpg",
    "Real estate agent with client.jpg",
    "Discussion of architectural plans.jpg",
    "Civil engineer and architect discussing.jpg",
    "Office meeting table discussion.jpg"
]

url = "https://commons.wikimedia.org/w/api.php"
for query in ["Architects blueprint discussion", "Architect floor plan table", "Property consultant meeting"]:
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": "10",
        "prop": "imageinfo",
        "iiprop": "url|mime|size",
        "format": "json"
    }
    r = requests.get(url, params=params, headers=headers, timeout=10)
    pages = r.json().get("query", {}).get("pages", {})
    for pid, p in pages.items():
        title = p.get("title", "")
        info = p.get("imageinfo", [{}])[0]
        u = info.get("url", "")
        mime = info.get("mime", "")
        if u and ("jpeg" in mime or "png" in mime or "jpg" in mime) and any(w in title.lower() for w in ["plan", "architect", "meeting", "discuss", "desk", "office"]):
            print(f"Candidate: {title} -> {u[:60]}")
            data = requests.get(u, headers=headers, timeout=15).content
            if len(data) > 50000:
                with open(save_dir / "real_advisory_table_perfect.jpg", "wb") as f:
                    f.write(data)
                print(f"  [OK] Saved {title}")
                break
    if (save_dir / "real_advisory_table_perfect.jpg").exists():
        break

print("Done!")
