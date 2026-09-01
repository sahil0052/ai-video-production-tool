import requests
from pathlib import Path

save_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_verified")
save_dir.mkdir(parents=True, exist_ok=True)

files_to_download = {
    "real_gurgaon_cybercity.jpg": "https://upload.wikimedia.org/wikipedia/commons/c/cb/Cyber_City_Gurgaon.jpg",
    "real_noida_residential_towers.jpg": "https://upload.wikimedia.org/wikipedia/commons/d/d7/Noida_Skyline.jpg",
    "real_gated_society_india.jpg": "https://upload.wikimedia.org/wikipedia/commons/6/67/High-rise_apartments_in_Greater_Noida.jpg",
    "real_house_keys_closeup.jpg": "https://upload.wikimedia.org/wikipedia/commons/d/d4/House_Keys.jpg",
    "real_concrete_construction.jpg": "https://upload.wikimedia.org/wikipedia/commons/8/8c/Building_construction_in_India.jpg",
    "real_rapid_metro_gurgaon.jpg": "https://upload.wikimedia.org/wikipedia/commons/b/b8/Rapid_MetroRail_Gurgaon.jpg"
}

headers = {"User-Agent": "NishaHomesProductionBot/1.0 (support@nishahomes.in)"}

for name, url in files_to_download.items():
    print(f"Fetching {name}...")
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200 and len(r.content) > 10000:
            with open(save_dir / name, "wb") as f:
                f.write(r.content)
            print(f"  [OK] {name} ({len(r.content)} bytes)")
        else:
            print(f"  [FAIL] HTTP {r.status_code}")
    except Exception as e:
        print(f"  [ERROR] {e}")

print("Done!")
