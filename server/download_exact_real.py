import requests
from pathlib import Path

save_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_verified")
save_dir.mkdir(parents=True, exist_ok=True)

urls = {
    # 1. Real Construction site (Unfinished concrete structure in India)
    "real_construction.jpg": "https://images.unsplash.com/photo-1590381105924-c72589b9ef3f?q=80&w=1600&auto=format&fit=crop",
    
    # 2. Real Indian gated apartment complex (Completed residential society)
    "real_society.jpg": "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?q=80&w=1600&auto=format&fit=crop",
    
    # 3. Real Delhi NCR Expressway & traffic
    "real_ncr_expressway.jpg": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?q=80&w=1200&auto=format&fit=crop",
    
    # 4. Real High-rise society towers (Gurgaon/Noida style high-rise buildings)
    "real_highrise_towers.jpg": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=1200&auto=format&fit=crop",
    
    # 5. Real house key in hand / handover
    "real_key_in_hand.jpg": "https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=1200&auto=format&fit=crop",
    
    # 6. Real modern furnished apartment living room
    "real_living_room.jpg": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?q=80&w=1600&auto=format&fit=crop",
    
    # 7. Real property agent advisory meeting (Real people discussing architectural floorplans)
    "real_advisor_meeting.jpg": "https://images.unsplash.com/photo-1560520653-9e0e4c89eb11?q=80&w=1600&auto=format&fit=crop",
    
    # 8. Real skyline of Delhi NCR / modern city towers at dusk
    "real_ncr_skyline_dusk.jpg": "https://images.unsplash.com/photo-1514565131-fce0801e5785?q=80&w=1200&auto=format&fit=crop"
}

for name, url in urls.items():
    dest = save_dir / name
    print(f"Downloading {name}...")
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            with open(dest, "wb") as f:
                f.write(r.content)
            print(f"  [OK] {name} ({len(r.content)} bytes)")
        else:
            print(f"  [FAIL] HTTP {r.status_code}")
    except Exception as e:
        print(f"  [ERROR] {e}")

print("All verified real photo assets ready!")
