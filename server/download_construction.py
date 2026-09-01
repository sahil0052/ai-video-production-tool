import requests
from pathlib import Path

dest = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_raw\real_construction_site.jpg")
urls = [
    "https://images.unsplash.com/photo-1504307651254-35680f356dfd?q=80&w=1920&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1590381105924-c72589b9ef3f?q=80&w=1920&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1541888946425-d0fbb18086f6?q=80&w=1920&auto=format&fit=crop"
]

for u in urls:
    try:
        r = requests.get(u, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            with open(dest, "wb") as f:
                f.write(r.content)
            print("Successfully downloaded real_construction_site.jpg!")
            break
    except:
        pass
