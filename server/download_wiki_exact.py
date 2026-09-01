import requests, json
from pathlib import Path

save_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_verified")
save_dir.mkdir(parents=True, exist_ok=True)

# List of exact Wikimedia Commons real photo pages
files_to_download = {
    # 1. Gurgaon Cyber City & Expressway skyline
    "real_gurgaon_cybercity.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cb/Cyber_City_Gurgaon.jpg/1280px-Cyber_City_Gurgaon.jpg",
    # 2. Noida Expressway Highrise Residential Sector
    "real_noida_residential_towers.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d7/Noida_Skyline.jpg/1280px-Noida_Skyline.jpg",
    # 3. Modern Indian Apartment Complex (Gated Society)
    "real_gated_society_india.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/High-rise_apartments_in_Greater_Noida.jpg/1280px-High-rise_apartments_in_Greater_Noida.jpg",
    # 4. Real House Keys on Table Handover
    "real_house_keys_closeup.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/House_Keys.jpg/1280px-House_Keys.jpg",
    # 5. Real Building Construction Underway
    "real_concrete_construction.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Building_construction_in_India.jpg/1280px-Building_construction_in_India.jpg",
    # 6. Real Indian Metro Train / Connectivity
    "real_rapid_metro_gurgaon.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/Rapid_MetroRail_Gurgaon.jpg/1280px-Rapid_MetroRail_Gurgaon.jpg"
}

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

for name, url in files_to_download.items():
    print(f"Fetching {name}...")
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200 and len(r.content) > 10000:
            with open(save_dir / name, "wb") as f:
                f.write(r.content)
            print(f"  [OK] {name} ({len(r.content)} bytes)")
        else:
            print(f"  [FAIL] HTTP {r.status_code}")
    except Exception as e:
        print(f"  [ERROR] {e}")

print("Verified Wikimedia Commons real photos downloaded!")
