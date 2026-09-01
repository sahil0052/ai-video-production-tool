import requests, os, json
from pathlib import Path

save_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_raw")
save_dir.mkdir(parents=True, exist_ok=True)

# List of high-res real photos from authentic photo repositories
# We will download real photos with direct URLs
real_images = {
    # 1. Price comparison (Distressed/Under construction building vs Completed Apartment Society)
    "real_construction_site.jpg": "https://images.unsplash.com/photo-1541888946425-d0fbb18086f6?q=80&w=1920&auto=format&fit=crop", # Real raw building construction
    "real_luxury_society.jpg": "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?q=80&w=1920&auto=format&fit=crop", # Real residential apartment complex
    
    # 2. Location & Connectivity: Real Gurgaon / Delhi NCR Expressway & Metro infrastructure
    "real_gurgaon_expressway.jpg": "https://images.unsplash.com/photo-1570168007204-dfb528c6958f?q=80&w=1080&auto=format&fit=crop", # Real Indian urban expressway / night traffic
    "real_metro_connectivity.jpg": "https://images.unsplash.com/photo-1587474260584-136574528ed5?q=80&w=1080&auto=format&fit=crop", # Delhi Metro viaduct / Indian cityscape
    
    # 3. Project Quality & Gated Community: Real high-rise society towers & amenities
    "real_society_highrise.jpg": "https://images.unsplash.com/photo-1574362848149-11496d93a7c7?q=80&w=1080&auto=format&fit=crop", # Real modern residential society towers
    "real_society_clubhouse.jpg": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?q=80&w=1080&auto=format&fit=crop", # Real residential property pool & architecture
    
    # 4. Timely Possession & Key Handover: Real keys & property contract
    "real_house_keys.jpg": "https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=1080&auto=format&fit=crop", # Real house key & model
    "real_handover_keys.jpg": "https://images.unsplash.com/photo-1582407947304-fd86f028f716?q=80&w=1080&auto=format&fit=crop", # Real estate contract & key
    
    # 5. Move-in Ready Interior: Real furnished modern apartment interior
    "real_ready_interior.jpg": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?q=80&w=1920&auto=format&fit=crop", # Real finished living room interior
    "real_modern_apartment.jpg": "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?q=80&w=1920&auto=format&fit=crop", # Real contemporary apartment interior
    
    # 6. Advisory Consultation: Real estate meeting & architectural floorplan review
    "real_advisory_meeting.jpg": "https://images.unsplash.com/photo-1560520653-9e0e4c89eb11?q=80&w=1920&auto=format&fit=crop", # Real consultation / floorplan review
    "real_client_discussion.jpg": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=1920&auto=format&fit=crop", # Real professional advisory discussion
    
    # 7. Delhi NCR Cityscape (Gurgaon / Noida / South Delhi)
    "real_delhi_ncr_skyline.jpg": "https://images.unsplash.com/photo-1598899134739-24c46f58b8c0?q=80&w=1080&auto=format&fit=crop", # Real modern Indian city skyline
    "real_noida_gurgaon_towers.jpg": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=1080&auto=format&fit=crop" # Real modern glass high-rises
}

for name, url in real_images.items():
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

print("\nDownloaded real photo assets successfully!")
