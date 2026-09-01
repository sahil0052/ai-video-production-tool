import requests, re, json
from pathlib import Path
from urllib.parse import quote

save_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_verified")
save_dir.mkdir(parents=True, exist_ok=True)

def download_duckduckgo_image(query, filename):
    print(f"Searching DuckDuckGo for '{query}'...")
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # Try searching Wikimedia Commons directly first
    api_url = f"https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrsearch={quote(query)}&gsrlimit=5&prop=imageinfo&iiprop=url|size"
    try:
        r = requests.get(api_url, headers={"User-Agent": "NishaHomesBot/1.0 (contact@nishahomes.in)"}, timeout=10)
        pages = r.json().get("query", {}).get("pages", {})
        for k, v in pages.items():
            img_info = v.get("imageinfo", [{}])[0]
            u = img_info.get("url")
            if u and any(ext in u.lower() for ext in [".jpg", ".png", ".jpeg"]) and not "icon" in u.lower():
                print(f"  Downloading from Wikimedia: {u[:60]}...")
                img_data = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=15).content
                if len(img_data) > 30000:
                    with open(save_dir / filename, "wb") as f:
                        f.write(img_data)
                    print(f"  [OK] Saved {filename} ({len(img_data)} bytes)")
                    return True
    except Exception as e:
        print(f"  Wikimedia error: {e}")

    # Fallback to direct unsplash curated high-res real photo URLs
    return False

# Targeted search
download_duckduckgo_image("DLF Cyber City Gurgaon high resolution photograph", "real_dlf_cybercity.jpg")
download_duckduckgo_image("Delhi Metro train elevated viaduct bridge", "real_delhi_metro_elevated.jpg")
download_duckduckgo_image("Noida high rise residential apartment buildings towers", "real_noida_highrise.jpg")
download_duckduckgo_image("House keys inside keyhole door real photo", "real_key_in_door.jpg")
download_duckduckgo_image("Two business people discussing blueprint floorplan office", "real_floorplan_discussion.jpg")
download_duckduckgo_image("Building under construction concrete slab scaffolding India", "real_concrete_building_construction.jpg")

print("Done search and download!")
