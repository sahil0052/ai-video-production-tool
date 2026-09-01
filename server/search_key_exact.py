import requests
from pathlib import Path

save_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_verified")
headers = {"User-Agent": "NishaHomesBot/7.0 (contact@nishahomes.in)"}

key_files = [
    "Mortise lock with key.jpg",
    "Yale lock and key.jpg",
    "House keys on a ring.jpg",
    "Key in a keyhole.jpg",
    "Door key in keyhole.jpg"
]

for kf in key_files:
    url = f"https://commons.wikimedia.org/w/api.php?action=query&titles=File:{kf}&prop=imageinfo&iiprop=url|size&format=json"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        pages = r.json().get("query", {}).get("pages", {})
        for pid, p in pages.items():
            if "imageinfo" in p:
                u = p["imageinfo"][0]["url"]
                size = p["imageinfo"][0]["size"]
                print(f"Found {kf}: {u[:60]}... ({size} bytes)")
                data = requests.get(u, headers=headers, timeout=15).content
                with open(save_dir / "real_house_key_handover.jpg", "wb") as f:
                    f.write(data)
                print("  [OK] Saved real_house_key_handover.jpg")
                break
        if (save_dir / "real_house_key_handover.jpg").exists():
            break
    except Exception as e:
        print(f"Error {kf}: {e}")

print("Done searching key files!")
