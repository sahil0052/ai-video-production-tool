"""
Viral Sound Effects Harvester & Extractor from soundcn & open audio registry
"""
import base64
import json
import re
import urllib.request
from pathlib import Path

SFX_BASE = Path(r"c:\websites\ai video production tool\storage\assets\viral_sfx_library")
CATEGORIES = {
    "clicks": ["click", "tick"],
    "paper_and_cards": ["card", "book", "paper"],
    "pops_and_taps": ["pop", "tap", "snap"],
    "switches_and_toggles": ["switch", "toggle"],
    "bells_and_chimes": ["bell", "coin", "chime"]
}

for cat in CATEGORIES:
    (SFX_BASE / cat).mkdir(parents=True, exist_ok=True)

# Fetch all available sounds in soundcn
api_url = "https://api.github.com/repos/kapishdima/soundcn/contents/registry/soundcn/sounds"
req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req) as resp:
        all_sounds = [item["name"] for item in json.loads(resp.read().decode())]
except Exception as e:
    print(f"Error fetching sound list: {e}")
    all_sounds = []

extracted_count = 0

for sound_name in all_sounds:
    target_cat = None
    for cat, prefixes in CATEGORIES.items():
        if any(p in sound_name.lower() for p in prefixes):
            target_cat = cat
            break
    
    if not target_cat:
        continue

    ts_url = f"https://raw.githubusercontent.com/kapishdima/soundcn/main/registry/soundcn/sounds/{sound_name}/{sound_name}.ts"
    try:
        req_ts = urllib.request.Request(ts_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_ts) as resp:
            content = resp.read().decode()
            
        m = re.search(r'data:audio/(?:mpeg|mp3|wav);base64,([A-Za-z0-9+/=]+)', content)
        if m:
            b64_data = m.group(1)
            audio_bytes = base64.b64decode(b64_data)
            
            cat_dir = SFX_BASE / target_cat
            cat_dir.mkdir(parents=True, exist_ok=True)
            out_file = cat_dir / f"{sound_name}.mp3"
            out_file.write_bytes(audio_bytes)
            extracted_count += 1
            if extracted_count <= 20 or extracted_count % 10 == 0:
                print(f"[{extracted_count}] Saved: {target_cat}/{sound_name}.mp3 ({len(audio_bytes)} bytes)")
    except Exception:
        continue

print(f"\n🎉 Successfully extracted {extracted_count} high-quality viral SFX files into {SFX_BASE}!")
