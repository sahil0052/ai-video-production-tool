import requests
from pathlib import Path

save_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_verified")
headers = {"User-Agent": "NishaHomesBot/4.0 (contact@nishahomes.in)"}

def download_wiki_file_by_title(title, out_name):
    url = f"https://commons.wikimedia.org/w/api.php?action=query&titles=File:{title}&prop=imageinfo&iiprop=url&format=json"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        pages = r.json().get("query", {}).get("pages", {})
        for pid, p in pages.items():
            if "imageinfo" in p:
                u = p["imageinfo"][0]["url"]
                print(f"Downloading {title} from {u[:60]}...")
                data = requests.get(u, headers=headers, timeout=15).content
                with open(save_dir / out_name, "wb") as f:
                    f.write(data)
                print(f"  [OK] Saved {out_name} ({len(data)} bytes)")
                return True
    except Exception as e:
        print(f"Error {title}: {e}")
    return False

# Download verified real photos from Wikimedia Commons
download_wiki_file_by_title("Schlüssel im Schloss.jpg", "real_keys_in_lock_verified.jpg")
download_wiki_file_by_title("Key in the lock (4392476722).jpg", "real_key_in_door_macro.jpg")
download_wiki_file_by_title("Delhi metro train at station.jpg", "real_delhi_metro_train_real.jpg")
download_wiki_file_by_title("Metro in Delhi.jpg", "real_delhi_metro_viaduct_real.jpg")
download_wiki_file_by_title("Business Meeting (5894178385).jpg", "real_business_meeting_real.jpg")
download_wiki_file_by_title("DLF Gateway Tower, Gurgaon.jpg", "real_dlf_gateway_tower.jpg")

print("Finished exact downloads!")
